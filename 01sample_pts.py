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
aoi = ee.FeatureCollection("projects/wwf-sig/assets/kaza-lc/aoi/Hwange")
aoi2 = ee.FeatureCollection("projects/wwf-sig/assets/kaza-lc/aoi/Mufunta")
aoi3 = ee.FeatureCollection("projects/wwf-sig/assets/kaza-lc/aoi/Mulobesi")
aoi4 = ee.FeatureCollection("projects/wwf-sig/assets/kaza-lc/aoi/SNMC")
aoi5 = ee.FeatureCollection("projects/wwf-sig/assets/kaza-lc/aoi/Sichifulo")
aoi6 = ee.FeatureCollection("projects/wwf-sig/assets/kaza-lc/aoi/Zambezi")
aoi7 = ee.FeatureCollection("projects/wwf-sig/assets/kaza-lc/aoi/Binga")

aoi_list = [aoi,aoi2,aoi3,aoi4,aoi5,aoi6,aoi7]


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
    

    description = 'EOSS2020_derived' + year #+ 'testGID'

    # Drive Options,
    folder = "KAZA-LC-trainingpts"

    # Cloud Options,
    bucket = "testBucket"

    # Asset Option
    partialPath = f"projects/{project}/assets/kaza-lc/sample_pts/"
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
        
        # Bare 60,61>>0
        # Built 50>> 1
        # Cropland 40>> 2
        # Forest 110,120,210>> 3
        # Grassland 31,32>> 4
        # Shrubs 130,222,231,232>> 5
        # Water 80,81>> 6
        # Wetland 90,91,92>> 7
        
    LC2020 = ee.Image("projects/wwf-sig/assets/kaza-lc/Land_Cover_KAZA_2020_TFCA")

    # typology is in both alphabetic and numeric order
    image=LC2020.remap([31,32, # Grassland
                        40, # Crop
                        50, # Built
                        60,61, # Bare
                        80,81, # Water
                        90,91,92, # Wetland
                        110,120, # Forest
                        130, # Shrub
                        210, # Forest
                        222,231,232 # Shrub
                        ],
                        
                        [4,4, # Grassland
                        2, # Crop
                        1, # Built
                        0,0, # Bare
                        6,6, # Water
                        7,7,7, # Wetland
                        3,3, # Forest
                        5, # Shrub
                        3, # Forest
                        5,5,5, # Shrub
                        ]).rename(landCover)

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
    classValues = [0,1,2,3,4,5,6,7]
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
    
    return e
def plot_id_global(n,feat):
    """takes an index number (n) and adds it to current PLOTID property of a feature 
            to ensure PLOTID values are globally unique (necessary for multiple sets of AOI sampling)"""
    aoi_id = ee.String(str(n))
    f = ee.Feature(feat)
    gid = aoi_id.cat('_').cat(ee.String(f.get('PLOTID')))
    f = f.set('PLOTID',gid, 'SAMPLEID', gid)
    return f

#%%
# Have multiple AOIs to generate samples for, want to ensure each AOI gets same amount of training pts
all_s = ee.FeatureCollection(sample(aoi_list[0],diff_per_class=True)) # use first aoi to start the collection for all
counter=1
for a in aoi_list[1:]:
    s = sample(a,diff_per_class=True)
    aoi_id = str(counter) # make an AOI index to append to PLOTID 
    s = s.map(lambda f: plot_id_global(aoi_id,f)) # make PLOT ID globally unique using AOI index
    all_s = ee.FeatureCollection(all_s).merge(s)
    counter = counter+1

print(f'Total training pts:{ee.FeatureCollection(all_s.size()).getInfo()}')

year = '2021' # year the training pts are to be interpreted for
project="wwf-sig" # ee project 

export(all_s,'asset')

