#%%
import ee

ee.Initialize()


# ######################### #
# Random Stratified Sample for Collect Earth Online  #
# ######################### #
# This script will preform a random stratified sample
# on a categorical input image for the intent of
# using the sampling schema in Collect Earth Online.

# Stratified random sampling can be preformed equally
# across classes, or by defining a list of labels and
# values.

# The output is a csv sample design where each plot
# has 1 sample in the proper format for use in CEO
# ######################### #
# Paramters
aoi = ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/Hwange")
aoi2 = ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/Mufunta")
aoi3 = ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/Mulobesi")
aoi4 = ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/SNMC")
aoi5 = ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/Sichifulo")
aoi6 = ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/Zambezi")
aoi7 = ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/Binga")

aoi_list = [aoi,aoi2,aoi3,aoi4,aoi5,aoi6,aoi7]

#%%
## GLOBAL VARS

# landCover is the named field which will hold each
# class label
landCover = 'LANDCOVER'

# scale in m^2 for sampling
scale = 30

def export(e,mode):
    # ######################### #
    #             Export Options            
    # ######################### #
    year = '2021' # year the training pts are to be interpreted for

    description = 'ceoTestPts' + year

    # Drive Options,
    folder = "KAZA-LC-trainingpts"

    # Cloud Options,
    bucket = "testBucket"

    # Asset Option
    partialPath = "projects/sig-ee/WWF_KAZA_LC/trainingPts/"
    assetId = partialPath + description
    
    drive_task = ee.batch.Export.table.toDrive(collection=e, description=description+'-Drive', fileNamePrefix=description,
    folder=folder, selectors='LON,LAT,PLOTID,SAMPLEID,'+landCover)

    cloud_task = ee.batch.Export.table.toCloudStorage(collection=e, description=description+'-Bucket', fileNamePrefix=description,
    bucket=bucket, selectors='LON,LAT,PLOTID,SAMPLEID,'+landCover),

    asset_task = ee.batch.Export.table.toAsset(collection=e, description=description+'-Asset', assetId=assetId)

    if mode=='drive':
        drive_task.start()
        print(f'Export to Drive: {description}')
    elif mode=='cloud':
        cloud_task.start()
        print(f'Export to Cloud: {description}')
    elif mode=='asset':
        asset_task.start()
        print(f'Export to Asset: {description}')
    else:
        drive_task.start()
        cloud_task.start()
        asset_task.start()
        print(f'All 3 Export modes started: {description}')
    return

def sample(aoi,diff_per_class):
    
    # When using simple stratified sampling numPoints is,
    # the number of points sampled per class,
    numPoints = 1000

    # The categorical image to sample,
    # EOSS's KAZA LC legend can be looked at here https:docs.google.com/document/d/12K4MqsAeq2bmCx3XyOMZefx6yBAkQv3lg_FA8NIxoow/edit?usp=sharing
        # aggregate LC2020 sub-classes together to make training points
        # OpenHerbaceous 31,32>>1
        # Cropland 40>>2
        # Built-up 50>>3
        # BareArea 60,61>>4
        # Water 80,81>>5
        # Wetland 90,91,92>>6
        # Forest/Woodland 110,120,210>>7
        # Bushland/Shrubs 130,222,231,232>>8
    # lc_pal = ["#FAF9C4", "#E74029","#5E3A35", 
    #             "#5C5B5B", "#191BDE", "#19DDDE", 
    #             "#176408","#31E10E"]
    LC2020 = ee.Image("projects/sig-ee/WWF_KAZA_LC/Land_Cover_KAZA_2020_TFCA")

    image=LC2020.remap([31,32,40,50,60,61,80,81,90,91,92,110,120,130,210,222,231,232],
                                [1,1,2,3,4,4,5,5,6,6,6,7,7,8,7,8,8,8]).rename(landCover)

    # ######################### #
    # Stratify by unequal number of points
    # -------------------------------------------------- #
    # If you would like to have differnt samples perclass
    # set sampleClass to True then update classValues
    # classPoints accordingly. If all classValues are NOT
    # assigned numPoints will be used as their default
    # number of points sampled.
    # ######################### #
    diff_per_class = True

    ## @classValues : A list of class values for which to
    # override the numPixels parameter. Must be the same
    #  size as classPoints.
    #
    ## @classPoints : A list of the per-class maximum
    # number of pixels to sample for each class in the
    # classValues list. Must be the same size as
    # classValues.
    classValues = [1,2,3,4,5,6,7,8]
    classPoints = [2000,2000,1000,1000,1000,1000,2000,2000]

    if diff_per_class:
        stratSample = image.stratifiedSample(
        region=aoi.geometry(),
        numPoints=numPoints,
        classValues=classValues,
        classPoints=classPoints,
        scale=scale,
        geometries=True)
    else:
        stratSample = image.stratifiedSample(
        region=aoi.geometry(),
        numPoints=numPoints,
        scale=scale,
        geometries=True)


    def ceoClean(f):
        # LON,LAT,PLOTID,SAMPLEID.,
        fid = f.id()
        coords = f.geometry().coordinates()
        return f.set('LON',coords.get(0),
                    'LAT',coords.get(1),
                    'PLOTID',fid,
                    'SAMPLEID',fid)

    #print("First sample point :",ee.Feature(stratSample.map(ceoClean).first()).getInfo())

    e = stratSample.map(ceoClean)
    #print("Class labels and number of samples :", e.aggregate_histogram(landCover).getInfo())
    return e

# Have multiple AOIs to generate samples for, want to ensure each AOI gets same amount of training pts
all_s = ee.FeatureCollection(sample(aoi_list[0],diff_per_class=True)) # use first aoi to start the collection for all
for a in aoi_list[1:]:
    s = sample(a,diff_per_class=True)
    all_s = ee.FeatureCollection(all_s).merge(s)

print(f'Total training pts:{ee.FeatureCollection(all_s.size()).getInfo()}')

export(all_s,'asset')


# %%
