#%%
import ee
import os
from pathlib import Path
import pandas as pd
import argparse
from utils.check_exists import check_exists

def format_pts(pts):
    """Turn a FC of training points containing full LC typology into a list of primitive point FCs, 
            one point FC for each LC primitive"""
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

# TODO: should use export function defined in exports.py to reduce redundant code
def export_img(img,imgcoll_p,aoi): 
    """Export image to Primitives imageCollection"""
    desc = f"Class{ee.Image(img).getString('Class').getInfo()}" # this would need to be defined in the Prims img for-loop
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

def RFprim(training_pts,input_stack):
    """Construct train and apply RF Probability classifier on LC Primitives"""
    inputs = ee.Image(input_stack)
    samples = ee.FeatureCollection(training_pts)
    
    class_value = ee.String(ee.Number.format(ee.Feature(samples.sort('PRIM',False).first()).get('LANDCOVER'))) #get LC numeric value for the given primitive (i.e. 'PRIM':1, 'LANDCOVER':6) then map to its class label (i.e. 6: 'Water')
    
    model = ee.Classifier.smileRandomForest(
    # can experiment with following three params for model performance
    numberOfTrees=100, 
    minLeafPopulation=1, 
    bagFraction=0.7, 
    seed=51515).setOutputMode('PROBABILITY').train(features=samples, 
                                                    classProperty='PRIM', 
                                                    inputProperties=inputs.bandNames(), 
                                                    )
    
    
    importance = ee.Dictionary(model.explain()).get('importance')
    oob = ee.Dictionary(model.explain()).get('outOfBagErrorEstimate')
    output = ee.Image(inputs).classify(model,'Probability').set('oobError',oob, 'Class',class_value) # 'Class',class_value
    return importance,oob,output

def primitives_to_collection(input_stack_path,train_path,output_ic):
    """ export each RF primitive image into a collection"""

    # make the empty IC, assuming it'll never already exist because error handling at main() will have prohibited that
    print(f"Creating empty Primitives ImageCollection: {output_ic}.")
    os.popen(f"earthengine create collection {output_ic}").read()
    
    # list of distinct LANDCOVER values
    labels = ee.FeatureCollection(train_path).aggregate_array('LANDCOVER').distinct().getInfo()
    # labels = ee.FeatureCollection(training_pts).aggregate_array('LANDCOVER').distinct().getInfo()
    
    # converting to index of the list of distinct LANDCOVER primtive FC's (prim_pts below)
    indices = list(range(len(labels))) # handles dynamic land cover strata
    
    # print('LANDCOVER class values: ',labels)
    # print('prim pt list indices: ',indices)
    
    # Sentinel2 SR composite to apply model inference on
    input_stack = ee.Image(input_stack_path)
    
    aoi = input_stack.geometry()
        
    # user-provided FeatureCollection reference dataset, contains LANDCOVER property with integer values
    training_pts = ee.FeatureCollection(train_path)#.filterBounds(aoi) 
    
    for i in indices: # running one LC class at a time
        prim_pts = ee.FeatureCollection(ee.List(format_pts(training_pts)).get(i)) # format training pts to 1/0 prim format
        # print(f'Index {i}, PRIM is LANDCOVER:', prim_pts.filter(ee.Filter.eq('PRIM',1)).aggregate_histogram('LANDCOVER').getInfo())
        importance,oob,output = RFprim(prim_pts,input_stack) # aoi was a kwarg, but it was only being used to filter training pts to aoi before training model, don't wanna do that anymore# run RF primitive model, get output image and metrics
        export_img(ee.Image(output), img_coll_path, aoi)
        export_metrics(importance,oob,output) 
        
    return


#%%
if __name__=="__main__":
    ee.Initialize(project='wwf-sig')

    parser = argparse.ArgumentParser(
    description="Create land cover primitives for all classes in provided training data",
    usage = "python 03RFprimitives.py -i path/to/input_stack -t path/to/training_data -o path/to/output"
    )
    
    parser.add_argument(
        "-i",
        "--input_stack",
        type=str,
        required=True,
        help="full asset path to input stack"
    )
    
    parser.add_argument(
        "-t",
        "--training_data",
        type=str,
        required=True,
        help = "full asset path to training data"
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
    train_path = args.training_data
    output = args.output
    dry_run = args.dry_run

    # Run Checks

    # Check Input Stack exists
    assert check_exists(input_stack_path) == 0, f"Check input_stack asset exists: {input_stack_path}"
    
    # Check Reference data exists
    assert check_exists(train_path) == 0, f"Check training_data asset exists: {train_path}"
    
    # Check -o output value will work if provided 
    # you have to either provide full asset path to output asset or not provide -o value at all to use default output location 
    if output:
        if '/' not in output:
            raise ValueError("Incorrect -o argument: Provide full asset path to -o or leave argument blank to use default output location")
             
        img_coll_path = output
        outputbase = os.path.dirname(output)
        # if / in path but the parent folder for your provided Primitives IC path doesn't exist, catches it
        assert check_exists(outputbase) == 0, f"Check parent folder exists: {outputbase}"
        
    else:
        outputbase = "projects/wwf-sig/assets/kaza-lc/output_landcover"
        img_coll_path = f"{outputbase}/Primitives_{os.path.basename(input_stack_path)}" #default path
    
    # don't want to let user try to export new Images into pre-existing ImageCollection, would be messy to handle
    if check_exists(img_coll_path) == 0:
        raise AssertionError(f"Primitives ImageCollection already exists: {img_coll_path}")

    # Construct local 'metrics' folder path from -o output or a default name if not provided
    cwd = os.getcwd()
    metrics_path = os.path.join(cwd,"metrics",os.path.basename(img_coll_path))
    # Check that LC strata in strata.py matches LANDCOVER values of input reference_data 
    ref_data_values = ee.FeatureCollection(train_path).aggregate_array('LANDCOVER').distinct().getInfo()

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
        
        # run analysis
        primitives_to_collection(input_stack_path,train_path,img_coll_path)