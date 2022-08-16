#%%
import ee
import os
from pathlib import Path
import pandas as pd
import argparse

seed = 51515

def export_train_test_pts(pts,aoi_s,year):
    """stratify 70/30 train and test points, export them, return training points in func for immediate use"""
    featColl = ee.FeatureCollection(pts)
    featColl = featColl.randomColumn(columnName='random', seed=seed)
    filt = ee.Filter.lt('random',0.7)
    train = featColl.filter(filt)
    test = featColl.filter(filt.Not())
    print('train size', train.size().getInfo())
    print('train breakdown',train.aggregate_histogram('LANDCOVER').getInfo())
    print('test size', test.size().getInfo())
    print('test breakdown',test.aggregate_histogram('LANDCOVER').getInfo())
    
    # export if they don't already exist
    train_pts_assets = os.popen(f"earthengine ls projects/{project}/assets/kaza-lc/sample_pts").read().split('\n')[0:-1]
    # print(train_pts_assets)
    # train
    train_asset = f"projects/{project}/assets/kaza-lc/sample_pts/training{aoi_s}{year}"
    train_e = ee.batch.Export.table.toAsset(train,f'exportTrainingPoints_{aoi_s}{year}',train_asset)
    train_asset_exists = train_asset in train_pts_assets
    # print(train_asset_exists)
    if not train_asset_exists:
        train_e.start()
        print(f'Training Points exported for {aoi_s} {year}')
    else:
        print(f"{train_asset} already exists, will not export")
    # test
    test_asset = f"projects/{project}/assets/kaza-lc/sample_pts/testing{aoi_s}{year}"
    test_e = ee.batch.Export.table.toAsset(test,f'exportTestPoints_{aoi_s}{year}',test_asset)
    test_asset_exists = test_asset in train_pts_assets
    # print(test_asset_exists)
    if not test_asset_exists:
        test_e.start()
        print(f'Test Points exported for {aoi_s} {year}')
    else:
        print(f"{test_asset} already exists, will not export")
    return train # return training points since we'll use it in the script to train the RFs

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

def export_img(img,imgcoll_p,aoi_s):
    """Export image to Primitives imageCollection"""
    aoi = ee.FeatureCollection(f"projects/{project}/assets/kaza-lc/aoi/{aoi_s}")
    desc = ee.Image(img).getString('Class').getInfo()
    task = ee.batch.Export.image.toAsset(
        image=ee.Image(img),
        description=desc,
        assetId=f'{imgcoll_p}/{desc}', 
        region=aoi.geometry().bounds(), 
        scale=10, 
        crs='EPSG:32734', 
        maxPixels=1e13)

    task.start()
    print(f"Export Started for {imgcoll_p}/{desc}")

def format_pts(training_pts):
    """Turn a FC of training points containing full LC typology into a list of FCs, one FC for each LC primitive"""
    # create sets of binary training pts for each class represented in the full training pts collection
    labels = ee.FeatureCollection(training_pts).aggregate_array('LANDCOVER').distinct()
    def binaryPts(l):
        # create prim and non prim sets with filters, reset prim to 1, non-prim to 0
        prim = training_pts.filter(ee.Filter.eq('LANDCOVER',l)).map(lambda f: f.set('PRIM',1))
        non_prim = training_pts.filter(ee.Filter.neq('LANDCOVER',l)).map(lambda f: f.set('PRIM',0))
        return ee.FeatureCollection(prim).merge(non_prim)
    list_of_prim_pts = ee.List(labels).map(binaryPts)
    return list_of_prim_pts

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


def primitives_to_collection(sensor,year,aoi_s):
    """ export each RF primitive image into a collection"""
    # create new collection 
    img_coll_path = f"projects/{project}/assets/kaza-lc/output_landcover/{sensor}_{year}_Primitives_{aoi_s}"
    os.popen(f"earthengine create collection {img_coll_path}").read()
    
    #setup training points and input stack
    aoi = ee.FeatureCollection(f"projects/{project}/assets/kaza-lc/aoi/{aoi_s}")
    input_stack = ee.Image(f"projects/{project}/assets/kaza-lc/input_stacks/{sensor}_{year}_stack_{aoi_s}").clip(aoi)
    
    # initizalize training pts featColl
    sample_pts_all = ee.FeatureCollection(f"projects/{project}/assets/kaza-lc/sample_pts/EOSS2020_derived{year}")
    sample_pts = sample_pts_all.filterBounds(aoi)  # only grab pts within your aoi, only can use SNMC, Mufunta and Zambezi as demos how its setup now, other AOIs don't have all 8 classes represented in their sample points
    sample_pts_w_inputs = (input_stack.sampleRegions(collection=sample_pts, scale=10, tileScale=4, geometries=True)
                            .filter(ee.Filter.notNull(input_stack.bandNames()))) # sample the input stack band values needed for classifier
    
    training_pts = export_train_test_pts(sample_pts_w_inputs,aoi_s,year)

  
    # create RF Primitive images one Land cover class at a time, exporting to a Primitive collection
    # total list of LANDCOVER classes is [0,1,2,3,4,5,6,7] 
    labels = ee.FeatureCollection(training_pts).aggregate_array('LANDCOVER').distinct().getInfo()
    indices = list(range(len(labels))) # handles cases where one or more LANDCOVER classes is not present in the training pts, converting to index of the list of distinct LANDCOVER primtive FC's (prim_pts below)
    
    #print('LANDCOVER classes: ',labels)
    #print('prim pt list indices: ',indices)
    for i in indices: # running one LC class at a time
        prim_pts = ee.FeatureCollection(ee.List(format_pts(training_pts)).get(i)) # format training pts to 1/0 prim format
        # print(f'Index {i}, PRIM is LANDCOVER:', prim_pts.filter(ee.Filter.eq('PRIM',1)).aggregate_histogram('LANDCOVER').getInfo())
        importance,oob,output = RFprim(prim_pts,input_stack,aoi) # run RF primitive model, get output image and metrics
        
        export_img(ee.Image(output), img_coll_path, aoi_s)
        export_metrics(importance,oob,output) 
        
    return


#%%

if __name__=="__main__":
    ee.Initialize()

    parser = argparse.ArgumentParser(
    description="Create land cover binary primitives for all classes in typology",
    usage = "python 03RFprimitives.py -p kaza-lc -a Zambezi -y 2021 -s S2"
    )
    
    parser.add_argument(
    "-p",
    "--project",
    type=str,
    required=True
    )
    
    parser.add_argument(
    "-a",
    "--aoi_string",
    type=str,
    required=True
    )
    
    parser.add_argument(
    "-y",
    "--year",
    type=int,
    required=True
    )
    
    parser.add_argument(
    "-s",
    "--sensor",
    type=str,
    required=True
    )
    
    args = parser.parse_args()

    sensor=args.sensor #S2 or planet
    year = args.year #2021
    aoi_s = args.aoi_string #SNMC
    project=args.project #kaza-lc

    # intiialize local folder upon run-time to store any model output metrics
    cwd = os.getcwd()
    p = os.path.join(cwd,f"metrics_{sensor}_{year}_{aoi_s}")
    if not os.path.exists(p):
        Path(p).mkdir(parents=True)


    # Typology
    lc_dct = {
        0:'Bare',
        1:'Built',
        2:'Crop',
        3:'Forest',
        4:'Grass',
        5:'Shrub',
        6:'Water',
        7:'Wetland'
        }

    primitives_to_collection(sensor,year,aoi_s)


