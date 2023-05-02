import os
import ee
from src.utils.s2process import s2process_refdata
from src.utils.check_exists import check_exists
ee.Initialize(project='wwf-sig')
 
seed=10110

def pt_calc_prop(input_fc:ee.FeatureCollection,ref_label:str,multiplier:int):
  # automating different sampling allocations is a little complex using refernce polygons, may not be worthwhile ATM..
  """
  Proportional allocation; takes a static integer multiplier and applies to each n of polygons per class
  args:
    input_fc: input polygon FeatureClass
    ref_label: Land cover reference property in the FC
    multiplier: integer
  returns:
    class_values (list): list of reference label class values i.e. [1,2,3,4]
    class_points (list) list of per-class n to be plugged into a stratified sampler i.e. [480,120,560,220]
  """
  dct = input_fc.aggregate_histogram(ref_label) # polygons per class
  keys = dct.keys()
  def ptCalc(key):
    return ee.Number(dct.get(key)).multiply(multiplier)
  
  class_values = keys.map(lambda k: ee.Number.parse(k))
  class_points = keys.map(ptCalc)
  
  return class_values,class_points

def strat_sample(img,region,n_points,class_values,class_points):
    """Stratified sample from a multi-band image containing input and predictor bands"""
    stratSample = ee.Image(img).stratifiedSample(
        numPoints=n_points,
        classBand='LANDCOVER', 
        region=region,
        scale=10, 
        seed=seed, 
        classValues=class_values,
        classPoints=class_points,
        dropNulls=True, 
        tileScale=8,  # increased from 4 to reduce computation time outs on generate_train_test().
        geometries=True)
  
    return stratSample

def split_train_test(pts):
    """stratify 80/20 train and test points"""
    
    featColl = ee.FeatureCollection(pts)
    featColl = featColl.randomColumn(columnName='random', seed=seed)
    filt = ee.Filter.lt('random',0.8)
    train = featColl.filter(filt)
    test = featColl.filter(filt.Not())

    return train, test

def export_pts(pts:ee.FeatureCollection,asset_id):
    """export train or test points to asset"""
    if check_exists(asset_id) == 1:
        task = ee.batch.Export.table.toAsset(pts,os.path.basename(asset_id).replace('/','_'),asset_id)
        task.start()
        print(f'Export started: {asset_id}')
    else:
        print(f"{asset_id} already exists")
    
    return

def generate_train_test(input_fc_path:str,year:int,output_basename:str,n_points:int,class_values:list,class_points:list,no_split:bool=False):
    """
    extracts S2 composite data to generated train/test points within reference polygon footprints
    """
    # default n_points if none provided
    if n_points == None:
       n_points = 20

    input_fc = ee.FeatureCollection(input_fc_path) # provide a polygon FC

    bbox = input_fc.geometry().bounds() # region
    
    # process s2 data within reference poly footprints
    s2processed = s2process_refdata(ref_polys=input_fc,ref_label='LANDCOVER',ref_year=year)

    # extract sample points from s2 data within reference poly footprints
    # debugging..
    # print(n_points)
    # print(class_values)
    # print(class_points)
    sampled_pts = strat_sample(s2processed,bbox,n_points,class_values,class_points)

    if no_split:
      assetid = f"{output_basename}_{str(year)}_pts"
      export_pts(sampled_pts,assetid)
    
    else:
      #stratify sample points into train/test
      train,test = split_train_test(sampled_pts)
      #debugging..
      # print(train.aggregate_histogram('LANDCOVER').getInfo())
      # print(test.aggregate_histogram('LANDCOVER').getInfo())
      
      # export train and test pts
      train_assetid = f"{output_basename}_{str(year)}_train_pts"
      export_pts(train,train_assetid)

      test_assetid = f"{output_basename}_{str(year)}_test_pts"
      export_pts(test,test_assetid)