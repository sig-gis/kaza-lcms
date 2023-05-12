import ee
import os
import pandas as pd

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

def export_metrics(imp,oob,img,metrics_path):
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


def gettop20(dict):
   dict = ee.Dictionary(dict)
   values = dict.values().sort()
   cutoff = values.get(-20)
   def kv_return(key,passedObj):
       passedObj = ee.List(passedObj)
       val = ee.Number(dict.get(key))
       retObj = ee.Algorithms.If(val.gte(cutoff),passedObj.add(key),passedObj)
       return retObj
   newl = dict.keys().iterate(kv_return,ee.List([]))
   return newl

def RFprim(training_pts,input_stack):
    """Train and apply RF Probability classifier on a Primitive"""
    inputs = ee.Image(input_stack)
    samples = ee.FeatureCollection(training_pts)
    
    class_value = ee.String(ee.Number.format(ee.Feature(samples.sort('PRIM',False).first()).get('LANDCOVER'))) #get LC numeric value for the given primitive (i.e. 'PRIM':1, 'LANDCOVER':6) then map to its class label (i.e. 6: 'Water')
    
    # can experiment with classifier params for model performance
    classifier = ee.Classifier.smileRandomForest(
    numberOfTrees=100, 
    minLeafPopulation=1, 
    bagFraction=0.7, 
    seed=51515).setOutputMode('PROBABILITY')
    
    # train model with all features
    model = classifier.train(features=samples, 
                            classProperty='PRIM', 
                            inputProperties=inputs.bandNames() 
                            )
    
    # store for model performance exploration
    oob_all = ee.Dictionary(model.explain()).get('outOfBagErrorEstimate')
    importance_all = ee.Dictionary(model.explain()).get('importance')
    
    # retrieve top 20 most important features
    top20 = gettop20(importance_all)
    
    # re-train model with top20 important features
    model = classifier.train(features=samples, 
                            classProperty='PRIM', 
                            inputProperties=top20
                            )
    
    oob_top20 = ee.Dictionary(model.explain()).get('outOfBagErrorEstimate')
    importance_top20 = ee.Dictionary(model.explain()).get('importance')

    output = ee.Image(inputs).classify(model,'Probability').set('oobError',oob_top20, 'Class',class_value) # 'Class',class_value
    return importance_all,oob_all,importance_top20,oob_top20,output

def primitives_to_collection(input_stack,training_pts,output_ic,metrics_path):
    """
    Create LC Primitive image for each LC class in training points

    args:
        input_stack (ee.Image): of all covariates and predictor
        training_pts (ee.FeatureCollection): training pts containing full LC typology
        output_ic (str): output ImageCollection path
        metrics_path (str): local file path to the metrics/this_model_run folder in repo
    
    returns:
        ImageCollection containing Primitive Images
    """

    input_stack = ee.Image(input_stack)
    training_pts = ee.FeatureCollection(training_pts)
    # make the empty IC, assuming it'll never already exist because error handling at main() will have prohibited that
    print(f"Creating empty Primitives ImageCollection: {output_ic}.\n")
    os.popen(f"earthengine create collection {output_ic}").read()
    
    # list of distinct LANDCOVER values
    labels = training_pts.aggregate_array('LANDCOVER').distinct().getInfo()
    # labels = ee.FeatureCollection(train_path).aggregate_array('LANDCOVER').distinct().getInfo()
    # labels = ee.FeatureCollection(training_pts).aggregate_array('LANDCOVER').distinct().getInfo()
    
    # converting to index of the list of distinct LANDCOVER primtive FC's (prim_pts below)
    indices = list(range(len(labels))) # handles dynamic land cover strata
    
    # print('LANDCOVER class values: ',labels)
    # print('prim pt list indices: ',indices)
    
    # Sentinel2 SR composite to apply model inference on
    input_stack = ee.Image(input_stack)
    
    aoi = input_stack.geometry()
        
    # user-provided FeatureCollection reference dataset, contains LANDCOVER property with integer values
    # training_pts = ee.FeatureCollection(train_path)#.filterBounds(aoi) 
    
    for i in indices: # running one LC class at a time
        prim_pts = ee.FeatureCollection(ee.List(format_pts(training_pts)).get(i)) # format training pts to 1/0 prim format
        # print(f'Index {i}, PRIM is LANDCOVER:', prim_pts.filter(ee.Filter.eq('PRIM',1)).aggregate_histogram('LANDCOVER').getInfo())
        importance_all,oob_all,importance_top20,oob_top20,output = RFprim(prim_pts,input_stack) # aoi was a kwarg, but it was only being used to filter training pts to aoi before training model, don't wanna do that anymore# run RF primitive model, get output image and metrics
        export_img(ee.Image(output), output_ic, aoi)
        
        # TODO: we would need greater file path control in export_metrics() so we don't overwrite the pre-top20 outputs
        # export metrics before top20 feature selection
        # export_metrics(importance_all,oob_all,output,metrics_path) 
        
        # export metrics after top20 feature selection
        export_metrics(importance_top20,oob_top20,output,metrics_path) 

    return