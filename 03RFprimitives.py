#%%
import ee
import os
import datetime
from pathlib import Path
import pandas as pd
import argparse
from utils import helper

seed = 51515

def stratify_pts(pts):
    """stratify 70/30 train and test points, export them, return training points in func for immediate use"""
    # featColl_sys_id = ee.FeatureCollection(pts)
    featColl = ee.FeatureCollection(pts)
    featColl = featColl.randomColumn(columnName='random', seed=seed)
    filt = ee.Filter.lt('random',0.7)
    train = featColl.filter(filt)
    test = featColl.filter(filt.Not())
    # print('train size', train.size().getInfo())
    # print('train breakdown',train.aggregate_histogram('LANDCOVER').getInfo())
    # print('test size', test.size().getInfo())
    # print('test breakdown',test.aggregate_histogram('LANDCOVER').getInfo())
    
    return train, test

def export_pts(pts:ee.FeatureCollection,asset_id):
    """export train or test points to asset"""
    
    if helper.check_exists(asset_id) == 1:
        task = ee.batch.Export.table.toAsset(pts,asset_id.replace('/','_'),asset_id)
        task.start()
        print(f'Export started: {asset_id}')
    else:
        print(f"{asset_id} already exists")
    
    return

def format_pts(pts):
    """Turn a FC of training points containing full LC typology into a list of FCs, one FC for each LC primitive"""
    # create sets of binary training pts for each class represented in the full training pts collection
    labels = ee.FeatureCollection(pts).aggregate_array('LANDCOVER').distinct()
    def binaryPts(l):
        # create prim and non prim sets with filters, reset prim to 1, non-prim to 0
        prim = pts.filter(ee.Filter.eq('LANDCOVER',l)).map(lambda f: f.set('PRIM',1))
        non_prim = pts.filter(ee.Filter.neq('LANDCOVER',l)).map(lambda f: f.set('PRIM',0))
        return ee.FeatureCollection(prim).merge(non_prim)
    list_of_prim_pts = ee.List(labels).map(binaryPts)
    return list_of_prim_pts

def export_metrics(imp,oob,img):
    """Parse variable importance and OOB Error estimate from trained model, output to local files respectively"""
    # Var Importance to csv file
    dct = imp.getInfo()
    list = dct.values()
    idx = dct.keys()
    df = pd.DataFrame(list, index = idx)
    LC = ee.Image(img).get('Class').getInfo()
    df.to_csv(f"{p}/varImportance{LC}.csv")
    # OOB error to txt file
    with open(os.path.join(p,f'oobError{LC}.txt'),mode='w') as f:
        f.write(ee.String(ee.Number(oob).format()).getInfo())
        f.close()

def export_img(img,imgcoll_p,aoi): # dry_run:False would go here
    """Export image to Primitives imageCollection"""
    # aoi = ee.FeatureCollection(f"projects/wwf-sig/assets/kaza-lc/aoi/{aoi_s}")
    desc = ee.Image(img).getString('Class').getInfo()
    task = ee.batch.Export.image.toAsset(
        image=ee.Image(img),
        description=desc,
        assetId=f'{imgcoll_p}/{desc}', 
        region=aoi, #.geometry().bounds(), 
        scale=10, 
        crs='EPSG:32734', 
        maxPixels=1e13)
    # if dry_run:
    #     print(f"Would Export: {imgcoll_p}/{desc}")
    # else:
    task.start()
    print(f"Export Started: {imgcoll_p}/{desc}")

def RFprim(training_pts,input_stack,aoi):
    """Construct train and apply RF Probability classifier on LC Primitives"""
    inputs = ee.Image(input_stack)
    samples = ee.FeatureCollection(training_pts)
    
    class_value = lc_dct[ee.Feature(samples.sort('PRIM',False).first()).get('LANDCOVER').getInfo()] #get LC numeric value for the given primitive (i.e. 'PRIM':1, 'LANDCOVER':6) then map to its class label (i.e. 6: 'Water')
    
    model = ee.Classifier.smileRandomForest(
    numberOfTrees=100, 
    minLeafPopulation=1, 
    bagFraction=0.7, 
    seed=seed).setOutputMode('PROBABILITY').train(features=samples, 
                                                    classProperty='PRIM', 
                                                    inputProperties=inputs.bandNames(), 
                                                    )
    
    
    importance = ee.Dictionary(model.explain()).get('importance')
    oob = ee.Dictionary(model.explain()).get('outOfBagErrorEstimate')
    output = ee.Image(inputs).clip(aoi).classify(model,'Probability').set('oobError',oob,'Class',class_value)
    return importance,oob,output

def primitives_to_collection(input_stack_path,reference_data_path,output):
    """ export each RF primitive image into a collection"""
    # create empty ImageCollection 
    if output: # user-entered ImageCollection path
        img_coll_path = output
        outputbase = os.path.dirname(output)
    else:
        outputbase = "projects/wwf-sig/assets/kaza-lc/output_landcover"
        img_coll_path = f"{outputbase}/Primitives_{os.path.basename(input_stack_path)}" #default path

    # print('output', output)        
    # print('outputbase',outputbase)
    # print('img_coll_path',img_coll_path)

    if helper.check_exists(img_coll_path) == 0:
        pass # if ImgCollection exists then outputbase (its parent) also exists
    
    else: #img_coll_path doesn't exist
        if helper.check_exists(outputbase) == 1: # create outputbase (ImgCollection's parent) if it doesn't exist
            f"{outputbase} does not exist, creating it."
            os.popen(f"earthengine create folder {outputbase}").read()

        f"{img_coll_path} does not exist, creating it."
        os.popen(f"earthengine create collection {img_coll_path}").read()
    
    # list of distinct LANDCOVER values
    labels = ee.FeatureCollection(reference_data_path).aggregate_array('LANDCOVER').distinct().getInfo()
    # labels = ee.FeatureCollection(training_pts).aggregate_array('LANDCOVER').distinct().getInfo()
    
    # converting to index of the list of distinct LANDCOVER primtive FC's (prim_pts below)
    indices = list(range(len(labels))) # handles dynamic land cover strata
    
    # print('LANDCOVER class values: ',labels)
    # print('prim pt list indices: ',indices)
    
    # if that RF prim img already exists, skip
    # lc_classes = [lc_dct[labels[i]] for i in indices]
    # print('LandCover Classes in Reference Data: ',lc_classes)
    
    # TODO: do we want to skip the whole analysis if the images already exsit? or keep it as it is to allow
    #  exporting of metrics.

    # to_export = [helper.check_exists(f"{img_coll_path}/{c}") == 1 for c in lc_classes]
    # print(to_export)
    # for i in indices:
    #     if to_export[i]:
    #         print(f'will export {lc_classes[i]}')
    
    # Landtrendr change img
    lt_change = ee.Image("projects/wwf-sig/assets/kaza-lc/input_stacks/lt_change_v2")
    # Sentinel2 SR image stack
    input_stack = ee.Image(input_stack_path)#.addBands(lt_change)
    
    aoi = input_stack.geometry()
        
    # initizalize  featColl
    # user-provided FeatureCollection reference dataset, contains LANDCOVER property with integer values
    ref_data = ee.FeatureCollection(reference_data_path).filterBounds(aoi)
    
    # generate sample pts of input stack raster info inside reference data
    # tries to retrieve literally all pixel centers of input_stack that overlap ref_data polygons, 
    # may be able to adjust this with tileScale, otherwise may need a diff functionality to avoid OOM errors
    sample_pts_w_inputs = (input_stack.sampleRegions(collection=ref_data, scale=10, tileScale=4, geometries=True)
                            .filter(ee.Filter.notNull(input_stack.bandNames()))) # sample the input stack band values needed for classifier
                            #.limit(100000) # could just limit it to a capped number of pts? wouldn't fix code erroring out on .sampleRegions()
    
    training_pts, testing_pts = stratify_pts(sample_pts_w_inputs)
    
    # exports train/test FCs if don't exist
    export_pts(training_pts,reference_data_path+"_training")
    export_pts(testing_pts,reference_data_path+"_testing")    
    
    for i in indices: # running one LC class at a time
        prim_pts = ee.FeatureCollection(ee.List(format_pts(training_pts)).get(i)) # format training pts to 1/0 prim format
        # print(f'Index {i}, PRIM is LANDCOVER:', prim_pts.filter(ee.Filter.eq('PRIM',1)).aggregate_histogram('LANDCOVER').getInfo())
        importance,oob,output = RFprim(prim_pts,input_stack,aoi) # run RF primitive model, get output image and metrics
        export_img(ee.Image(output), img_coll_path, aoi) # a dry_run arg would go here
        export_metrics(importance,oob,output) 
        
    return


#%%

if __name__=="__main__":
    ee.Initialize(project='wwf-sig')

    parser = argparse.ArgumentParser(
    description="Create land cover primitives for all classes in provided reference data",
    usage = "python 03RFprimitives.py -i path/to/input_stack -r path/to/reference_data -o path/to/output"
    )
    
    parser.add_argument(
        "-i",
        "--input_stack",
        type=str,
        required=True,
        help="full asset path to input stack"
    )
    
    parser.add_argument(
        "-r",
        "--reference_data",
        type=str,
        required=True,
        help = "full asset path to reference data"
    )
    
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=False,
        help="The full asset path for export. Defaults to: 'projects/wwf-sig/assets/kaza-lc/output_landcover/S2_[year]_Primitives_[aoi]' "
    )

    # TODO: to incorporate this would want to maybe pull out the folder/ImageCollection/Image path constructions
    #  out of primitives_to_collection() and into main() level function after parsing arguments
    # parser.add_argument(
    #     "-d",
    #     "--dry_run",
    #     dest="dry_run",
    #     action="store_true",
    #     help="goes through checks but does not export.",
    #     )

    args = parser.parse_args()

    input_stack_path = args.input_stack
    reference_data_path = args.reference_data
    output = args.output
    # dry_run = args.dry_run
    
    # intiialize local folder upon run-time to store any model output metrics
    cwd = os.getcwd()
    if output:
        p = os.path.join(cwd,f"metrics_{os.path.basename(output)}")
    else:
        date_id = datetime.datetime.utcnow().strftime("%Y-%m-%d").replace('-','')
        p = os.path.join(cwd,f"metrics_output_{os.path.basename(input_stack_path)}_{date_id}")

    if not os.path.exists(p):
        Path(p).mkdir(parents=True)

    # Typology
    # TODO: how to handle output primitives so they are labeled with class name appropriately?
    # have them pass path to a csv that delineates typology so they don't have to modify code?
    # have them provide a LABEL porperty in reference data with LANDCOVER so we can identify it programmatically..?
    
    # lc_dct = {
    #     0:'Bare',
    #     1:'Built',
    #     2:'Crop',
    #     3:'Forest',
    #     4:'Grass',
    #     5:'Shrub',
    #     6:'Water',
    #     7:'Wetland'
    #     }
    
    lc_dct = {
        0:'Crop',
        1:'Forest',
    }

    primitives_to_collection(input_stack_path,reference_data_path,output)


