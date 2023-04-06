import ee
ee.Initialize(project='wwf-sig')

input_fc = ee.FeatureCollection("") # provide a polygon FC
eossLC = ee.Image("") # EOSS 2020 LC image as export region possibly

# mapping thru distinct years will make the computation that much more heavy.. i think this script should only be given one input FC representing one 
# unique year of reference data interpretation

years = input_fc.aggregate_array('YEAR').distinct()
print(years)

input_fcPolyImg = ee.Image(0).paint(input_fc,'YEARint').selfMask().rename('YEAR')
# Map.addLayer(input_fcPolyImg,{min:2021,max:2022,palette:['cyan','magenta']},'polyToRasterYEAR')

s2 = ee.ImageCollection("COPERNICUS/S2_SR")

def generateData(featColl):
  """Main-level function that executes whole workflow"""
  # distinct years of interpretation in the reference dataset
  years = ee.FeatureCollection(featColl).aggregate_array('YEAR').distinct()
  
  # Process S2 data by year inside yearly polygons
  s2processedByYear = years.map(s2preprocess)
  # create stratSample that's split into train/test points
  trainTest = s2processedByYear.map(stratSampleFromImage) # should be a list of two FCs per year
  # how to flatten into one FC then separate out by split
  return trainTest

def s2preprocess(year):
  # takes polygons of a certain interpretation year, 
  # masks S2 data to the polygons and does full preprocessing flow
  # finally extracts train/test points from the stacked input/predictor raster stack
  s2 = ee.ImageCollection("COPERNICUS/S2_SR")

  # get the polys with given Year in current map()
  filteredPolys = input_fc.filter(ee.Filter.eq('YEAR',year))
  # filter s2 collection by the year's polys and by the interpYear 
  startDate = ee.String(year).cat("-01-01")
  endDate = ee.String(year).cat("-12-31")
  filteredS2 = s2.filterBounds(filteredPolys).filterDate(startDate,endDate)
  # rasterize the polygons of interest on LANDCOVER to use as Sentinel2 image mask
  filteredPolysImg = ee.Image(0).paint(filteredPolys,'LANDCOVER').rename('LANDCOVER').selfMask()
  s2Masked = filteredS2.map(lambda img: img.updateMask(filteredPolysImg))
  
  # replace actual s2 preprocessing operations here...
  s2Processed = s2Masked.select(['B5','B4','B3','B2']).median()
  
  # stack predictor (LANDCOVER) with input bands (Sentinel2)
  return filteredPolysImg.addBands(s2Processed) 
  


# Shows how the s2 processing by year works outside the main function
s2processedByYear = years.map(s2preprocess)
# print(s2processedByYear.get(0))
# # Map.addLayer(input_fc.filter(ee.Filter.eq('YEAR','2021')))
# Map.addLayer(ee.Image(s2processedByYear.get(0)),{bands:['B4','B3','B2'],min:0,max:3000},'first year s2 processed')
# Map.addLayer(ee.Image(s2processedByYear.get(1)),{bands:['B5','B3','B2'],min:0,max:3000},'second year s2 processed')

# 
# create train/test samples
# stratified first by year (because we have an image composite for each year masked to the yearly polygons)
# then stratified by LANDCOVER class
# We will shoot for 10k points, 8k train, 2k test
# We have 2 years so 5k points per year, 5k/8 classes = 625 pts per class if doing equal allocation

# Oversampling Classes of Interest:
# If we wanted to bump up N for classes of interest and bump down N for majority/unimportant classes.. 
# we could do 625*0.6 for majority/unimportant classes and 6250*1.3 for rare/important classes
# so Bare:412, Built:412, Crop:812, Forest:812, Grass:625, Shrub:625, Water:625, Wetland: 625
#
seed=10110
def stratSampleFromImage(img):
  # takes an image containing input and predictor bands, 
  # predictor band is 'LANDCOVER' but for now we will use a dummy property
  stratSample = ee.Image(img).stratifiedSample({
    'numPoints':500, # equal allocation
    'classBand':'LANDCOVER', 
    'region':eossLC.geometry(),#EOSS landcover footprint? don't want to not specify something since the input img is computed on the fly it won't have a specific footprint..# 
    'scale':10, 
    # 'projection':undefined, 
    'seed':seed, 
    # 'classValues':[1,2,3,4,5,6,7,8], # Bare, Built, Crop, Forest, Grass, Shrub, Water, Wetland
    # 'classPoints':[4125,4125,8125,8125,6250,6250,6250,6250], 
    'dropNulls':True, 
    'tileScale':4, 
    'geometries':False})
  
  # stratify train/test 80/20
  featCollRand = ee.FeatureCollection(stratSample).randomColumn('random',seed)
  filt = ee.Filter.lt('random',0.8)
  train = featCollRand.filter(filt).map(lambda feat: ee.Feature(feat).set('split','train'))
  test = featCollRand.filter(filt.Not()).map(lambda feat: ee.Feature(feat).set('split','test'))
  return train.merge(test)
