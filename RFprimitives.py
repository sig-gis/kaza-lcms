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
    
    class_value = lc_dct[ee.Feature(samples.sort('PRIM',False).first()).get('LANDCOVER').getInfo()] #get its LC numeric value, map it to LC Class
    
    model = ee.Classifier.smileRandomForest(
    numberOfTrees=100, 
    #variablesPerSplit=, #default sqrt of M total covariates 
    minLeafPopulation=1, 
    bagFraction=0.7, 
    #maxNodes=, #defaults to no limit
    seed=51515).setOutputMode('PROBABILITY').train(features=samples, 
                                                    classProperty='PRIM', 
                                                    inputProperties=inputs.bandNames(), 
                                                    #subsampling, 
                                                    #subsamplingSeed
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
    training_pts_all = ee.FeatureCollection(f"projects/sig-ee/WWF_KAZA_LC/trainingPts/ceoTestPts{year}")
    training_pts = training_pts_all.filterBounds(aoi)  # only grab pts within your aoi
    training_pts_sampled = (input_stack.sampleRegions(collection=training_pts, scale=10, tileScale=4, geometries=True)
                            .filter(ee.Filter.notNull(input_stack.bandNames()))) # sample the input stack band values needed for classifier
    
  
    # create RF Primitive images one Land cover class at a time, exporting to a Primitive collection
    labels = ee.FeatureCollection(training_pts).aggregate_array('LANDCOVER').distinct().getInfo()
    
    for l in labels:
        prim_pts = ee.FeatureCollection(ee.List(format_pts(training_pts_sampled)).get(l-1)) # format training pts to 1/0 prim format
        importance,oob,output = RFprim(prim_pts,input_stack,aoi) # create output RF Primitive probability image
        #print(rf_output.bandNames().getInfo())
        #print('OOB Error',output.get('oobError').getInfo())
        
        export_img(ee.Image(output), img_coll_path, aoi_s) # export the Class Primitive image to Primitive img collection
        export_metrics(importance,oob,output) 
        #break
    
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
    1:'Grassland',
    2:'Crop',
    3:'Built',
    4:'Bare',
    5:'Water',
    6:'Wetland',
    7:'Forest',
    8:'Shrubland'
    }

primitives_to_collection(sensor,year,aoi_s)


