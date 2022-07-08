#%%
import ee
import os
from pathlib import Path
import pandas as pd
ee.Initialize()


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
    aoi = ee.FeatureCollection(f"projects/sig-ee/WWF_KAZA_LC/aoi/{aoi_s}")
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
    seed=51515).setOutputMode('PROBABILITY').train(features=samples, 
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
    img_coll_path = f"projects/sig-ee/WWF_KAZA_LC/output_landcover/{sensor}{aoi_s}{year}Primitives"
    os.popen(f"earthengine create collection {img_coll_path}").read()
    
    #setup training points and input stack
    aoi = ee.FeatureCollection(f"projects/sig-ee/WWF_KAZA_LC/aoi/{aoi_s}")
    input_stack = ee.Image(f"projects/sig-ee/WWF_KAZA_LC/input_stacks/{sensor}_{year}monthlyCompositeStack_{aoi_s}").clip(aoi)
    
    # initizalize training pts featColl
    training_pts_all = ee.FeatureCollection(f"projects/sig-ee/WWF_KAZA_LC/trainingPts/EOSS2020_derived{year}")
    training_pts = training_pts_all.filterBounds(aoi)  # only grab pts within your aoi
    training_pts_sampled = (input_stack.sampleRegions(collection=training_pts, scale=10, tileScale=4, geometries=True)
                            .filter(ee.Filter.notNull(input_stack.bandNames()))) # sample the input stack band values needed for classifier
    
  
    # create RF Primitive images one Land cover class at a time, exporting to a Primitive collection
    labels = ee.FeatureCollection(training_pts).aggregate_array('LANDCOVER').distinct().getInfo()
    for l in labels: # running one LC class at a time
        prim_pts = ee.FeatureCollection(ee.List(format_pts(training_pts_sampled)).get(l)) # format training pts to 1/0 prim format
        importance,oob,output = RFprim(prim_pts,input_stack,aoi) # run RF primitive model, get output image and metrics
        
        export_img(ee.Image(output), img_coll_path, aoi_s)
        export_metrics(importance,oob,output) 
        
    return


#%%
sensor = 'planet' # S2 or planet or combined?
year = '2021'
aoi_s = 'SNMC'

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


