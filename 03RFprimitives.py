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
    lc_class = str(ee.Image(img).get('Class').getInfo())
    df.to_csv(f"{metrics_path}/varImportanceClass{lc_class}.csv")
    # OOB error to txt file
    with open(os.path.join(metrics_path,f'oobErrorClass{lc_class}.txt'),mode='w') as f:
        f.write(ee.String(ee.Number(oob).format()).getInfo())
        f.close()

def export_img(img,imgcoll_p,aoi): # dry_run:False would go here
    """Export image to Primitives imageCollection"""
    # aoi = ee.FeatureCollection(f"projects/wwf-sig/assets/kaza-lc/aoi/{aoi_s}")
    desc = f"Class{ee.Image(img).getString('Class').getInfo()}"
    task = ee.batch.Export.image.toAsset(
        image=ee.Image(img),
        description=desc,
        assetId=f'{imgcoll_p}/{desc}', 
        region=aoi, #.geometry().bounds(), 
        scale=10, 
        crs='EPSG:32734', 
        maxPixels=1e13)
    
    task.start()
    print(f"Export Started: {imgcoll_p}/{desc}")

def RFprim(training_pts,input_stack,aoi):
    """Construct train and apply RF Probability classifier on LC Primitives"""
    inputs = ee.Image(input_stack)
    samples = ee.FeatureCollection(training_pts)
    
    class_value = ee.String(ee.Number.format(ee.Feature(samples.sort('PRIM',False).first()).get('LANDCOVER'))) #get LC numeric value for the given primitive (i.e. 'PRIM':1, 'LANDCOVER':6) then map to its class label (i.e. 6: 'Water')
    
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
    output = ee.Image(inputs).clip(aoi).classify(model,'Probability').set('oobError',oob, 'Class',class_value) # 'Class',class_value
    return importance,oob,output

def primitives_to_collection(input_stack_path,reference_data_path,output_ic):
    """ export each RF primitive image into a collection"""

    # make the empty IC, assuming it'll never already exist because error handling at main() will have prohibited that
    print(f"Creating empty Primitives ImageCollection: {output_ic}.")
    os.popen(f"earthengine create collection {output_ic}").read()
    
    # list of distinct LANDCOVER values
    labels = ee.FeatureCollection(reference_data_path).aggregate_array('LANDCOVER').distinct().getInfo()
    # labels = ee.FeatureCollection(training_pts).aggregate_array('LANDCOVER').distinct().getInfo()
    
    # converting to index of the list of distinct LANDCOVER primtive FC's (prim_pts below)
    indices = list(range(len(labels))) # handles dynamic land cover strata
    
    # print('LANDCOVER class values: ',labels)
    # print('prim pt list indices: ',indices)
    
    # Landtrendr change img
    lt_change = ee.Image("projects/wwf-sig/assets/kaza-lc/input_stacks/lt_change_v2")
    # Sentinel2 SR image stack
    input_stack = ee.Image(input_stack_path)#.addBands(lt_change)
    
    aoi = input_stack.geometry()
        
    # user-provided FeatureCollection reference dataset, contains LANDCOVER property with integer values
    ref_data = ee.FeatureCollection(reference_data_path).filterBounds(aoi)
    
    # generate sample pts of input stack raster info inside reference data
    # tries to retrieve literally all pixel centers of input_stack that overlap ref_data polygons, 
    # may be able to adjust this with tileScale, otherwise may need a diff functionality to avoid OOM errors
    # sample_pts_w_inputs = (input_stack.sampleRegions(collection=ref_data, scale=10, tileScale=4, geometries=True)
    #                         .filter(ee.Filter.notNull(input_stack.bandNames())))
    
    # Instead we rasterize the ref polygons on their LANDCOVER values, 
    img_paint = ee.Image(0).paint(ref_data,'LANDCOVER').clip(aoi).selfMask().rename('LANDCOVER')

    # then we can stack the LANDCOVER raster w/ the input_stack and do .stratifiedSample() to control # pts per class
    # stratifiedSample(numPoints, classBand, region, scale, projection, seed, classValues, classPoints, dropNulls, tileScale, geometries)
    sample_pts_w_inputs = (img_paint.addBands(input_stack).stratifiedSample(
        numPoints=10000, # pts per class
        classBand='LANDCOVER', 
        region = aoi, 
        scale = 10, 
        projection = 'EPSG:32734',
        seed = seed,
        dropNulls = True,
        geometries = True) 
        )
  

    training_pts, testing_pts = stratify_pts(sample_pts_w_inputs)
    
    # exports train/test FCs if don't exist
    export_pts(training_pts,reference_data_path+"_trainingPts")
    export_pts(testing_pts,reference_data_path+"_testingPts")    
    
    for i in indices: # running one LC class at a time
        prim_pts = ee.FeatureCollection(ee.List(format_pts(training_pts)).get(i)) # format training pts to 1/0 prim format
        # print(f'Index {i}, PRIM is LANDCOVER:', prim_pts.filter(ee.Filter.eq('PRIM',1)).aggregate_histogram('LANDCOVER').getInfo())
        importance,oob,output = RFprim(prim_pts,input_stack,aoi) # run RF primitive model, get output image and metrics
        export_img(ee.Image(output), img_coll_path, aoi)
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

    parser.add_argument(
        "-d",
        "--dry_run",
        dest="dry_run",
        action="store_true",
        help="goes through checks and prints paths to outputs but does not export them.",
        )

    args = parser.parse_args()

    input_stack_path = args.input_stack
    reference_data_path = args.reference_data
    output = args.output
    dry_run = args.dry_run

    # Run Checks

    # Check Input Stack exists
    assert helper.check_exists(input_stack_path) == 0, f"Check input_stack asset exists: {input_stack_path}"
    
    # Check Reference data exists
    assert helper.check_exists(reference_data_path) == 0, f"Check reference_data asset exists: {reference_data_path}"
    
    # Check -o output value will work if provided 
    # you have to either provide full asset path to output asset or not provide -o value at all to use default output location 
    if output:
        if '/' not in output:
            raise ValueError("Incorrect -o argument: Provide full asset path to -o or leave argument blank to use default output location")
             
        img_coll_path = output
        outputbase = os.path.dirname(output)
        # if / in path but the parent folder for your provided Primitives IC path doesn't exist, catches it
        assert helper.check_exists(outputbase) == 0, f"Check parent folder exists: {outputbase}"
        
    else:
        outputbase = "projects/wwf-sig/assets/kaza-lc/output_landcover"
        img_coll_path = f"{outputbase}/Primitives_{os.path.basename(input_stack_path)}" #default path
    
    # don't want to let user try to export new Images into pre-existing ImageCollection, would be messy to handle
    if helper.check_exists(img_coll_path) == 0:
        raise AssertionError(f"Primitives ImageCollection already exists: {img_coll_path}")

    # Construct local 'metrics' folder path from -o output or a default name if not provided
    cwd = os.getcwd()
    metrics_path = os.path.join(cwd,"metrics",os.path.basename(img_coll_path))
    # Check that LC strata in strata.py matches LANDCOVER values of input reference_data 
    ref_data_values = ee.FeatureCollection(reference_data_path).aggregate_array('LANDCOVER').distinct().getInfo()
    
    # not providing strata anymore, model will just model the unique values passed by reference data's LANDCOVER property
    # strata_values = list(lc_dct.keys())
    # assert ref_data_values == strata_values, f"'LANDCOVER' values provided in reference data does not match strata\n Reference Data 'LANDCOVER':{ref_data_values}, Strata:{strata_values}"

    # print output locations and exit
    if dry_run: 
        print(f"Would Export Primitives ImageCollection to: {img_coll_path}")
        print(f"Would Export Model Metrics to: {metrics_path}")
        exit()
    
    else:
        # make local metrics folder
        if not os.path.exists(metrics_path):
            Path(metrics_path).mkdir(parents=True)
        print(f"Metrics will be exported to: {metrics_path}")
        
        primitives_to_collection(input_stack_path,reference_data_path,img_coll_path)


