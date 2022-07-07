#%%
import ee
import os
ee.Initialize()


sensor = 'S2' # S2 or planet or combined?
year = '2021'
aoi_s = 'SNMC'


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
    """Construct train and apply RF Probability classifier on LC Primitives (binary)"""
    inputs = ee.Image(input_stack)
    #print(inputs.bandNames().getInfo())
    samples = ee.FeatureCollection(training_pts)
    # class_value = samples.first().filter(ee.Filter.eq('PRIM',1)).limit(1).get('LANDCOVER').getInfo()
    # print(samples.propertyNames().getInfo())
    
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
    
    output = ee.Image(inputs).clip(aoi).classify(model,'Probability')#.set('Class',class_value)         
    return output #, importance, oob_estimate ## gonna want to export var importance and oob estimates per RF model

def export(img,imgcoll_p,aoi_s,year):
    aoi = ee.FeatureCollection(f"projects/sig-ee/WWF_KAZA_LC/aoi/{aoi_s}")
    #primitive = str(ee.Image(img).get('Class').getInfo())
    desc = f"{aoi_s}{year}Class"
    print(desc)
    config = {
        'image':ee.Image(img),
        'description':desc,
        'assetId':f'{imgcoll_p}/{aoi_s}{year}Class', 
        'pyramidingPolicy':'mean', 
        'region':aoi.geometry(),
        'scale':10, 
        'crs':'EPSG:32734', 
        'maxPixels':1e13, 
        }
    print(config)
    task = ee.batch.Export.image.toAsset(config)
    
    # task = ee.batch.Export.image.toAsset(image=ee.Image(img),
    #     description=desc,
    #     assetId=f'{imgcoll_p}/{aoi}{year}Class', 
    #     pyramidingPolicy='mean', 
    #     region=aoi.geometry().getInfo()['coordinates'], 
    #     scale=10, 
    #     crs='EPSG:32734', 
    #     maxPixels=1e13)

    task.start()
    print(f"Export Started for {desc}")


def primitives_to_collection(sensor,year,aoi_s):
    """ export each RF primitive image into a collection"""
    # create new collection 
    img_coll_path = f"projects/sig-ee/WWF_KAZA_LC/output_landcover/{aoi_s}{year}Primitives"
    os.popen(f"earthengine create collection {img_coll_path}").read()
    
    #setup training points and input stack
    aoi = ee.FeatureCollection(f"projects/sig-ee/WWF_KAZA_LC/aoi/{aoi_s}")
    input_stack = ee.Image(f"projects/sig-ee/WWF_KAZA_LC/input_stacks/{sensor}_{year}monthlyCompositeStack_{aoi_s}").clip(aoi)
    # initizalize training pts featColl
    training_pts_all = ee.FeatureCollection(f"projects/sig-ee/WWF_KAZA_LC/trainingPts/ceoTestPts{year}")
    training_pts = training_pts_all.filterBounds(aoi)  # only grab pts within desired aoi
    training_pts_sampled = (input_stack.sampleRegions(collection=training_pts, scale=10, tileScale=4, geometries=True)
                            .filter(ee.Filter.notNull(input_stack.bandNames()))) # sample the input stack band values needed for classifier
    
  
    # create RF Primitive images one Land cover class at a time, exporting to a Primitive collection
    labels = ee.FeatureCollection(training_pts).aggregate_array('LANDCOVER').distinct().getInfo()
    print(labels)
    for l in labels:
        print(l)
        prim_pts = ee.FeatureCollection(ee.List(format_pts(training_pts_sampled)).get(l)) # format training pts to 1/0 prim format
        print(prim_pts.size().getInfo())
        rf_output = RFprim(prim_pts,input_stack,aoi) # create output RF Primitive probability image
        print(rf_output.bandNames().getInfo())

        export(ee.Image(rf_output), img_coll_path, aoi_s, year) # export the Class Primitive image to Primitive img collection
        break

    
    



    return


#%%
primitives_to_collection('S2','2021','SNMC')


# %%
