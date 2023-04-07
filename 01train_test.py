import os
import ee
import argparse
from utils.s2process import s2process_refdata
from utils.check_exists import check_exists
ee.Initialize(project='wwf-sig')
 
seed=10110
def strat_sample(img,region):
  """Stratified sample from a multi-band image containing input and predictor bands""" 
    
    # Strat Sample Notes for later..
    # Our predictor band/property is 'LANDCOVER'

    # for WWF KAZA, the resulting train and test FCs will likely be one of several merged together 
    # to train and validate the model results, so we don't want to specify a per-class sampling number (N)
    # that you hope to put straight into the classifier
    # instead, this number would be just a proportion of the total points you aim for per-class.
    
    # it also works out that doing it piece-meal this way, while not a one-click solution to generate all your train/test data,
    # creates much more bite-sized batch processing tasks for Earth Engine

    # Oversampling Classes of Interest:
    # If we wanted to bump up N for classes of interest and bump down N for majority/unimportant classes.. 
    # we could do N*0.6 for majority/unimportant classes and N*1.3 for rare/important classes
    # letting N represent an equal allocation sample number 
    # ex: N = 500, so N*0.6 = 300 and N*1.3 = 650
    # so Bare:300, Built:300, Crop:650, Forest:650, Grass:500, Shrub:500, Water:500, Wetland: 500
    
  stratSample = ee.Image(img).stratifiedSample(
    numPoints=500, # equal allocation
    classBand='LANDCOVER', 
    region=region,#EOSS landcover footprint? don't want to not specify something since the input img is computed on the fly it won't have a specific footprint..# 
    scale=10, 
    # 'projection':undefined, 
    seed=seed, 
    # 'classValues':[1,2,3,4,5,6,7,8], # Bare, Built, Crop, Forest, Grass, Shrub, Water, Wetland
    # 'classPoints':[4125,4125,8125,8125,6250,6250,6250,6250], 
    dropNulls=True, 
    tileScale=4, 
    geometries=True)
  
  return stratSample
  
#   # stratify train/test 80/20
#   featCollRand = ee.FeatureCollection(stratSample).randomColumn('random',seed)
#   filt = ee.Filter.lt('random',0.8)
#   train = featCollRand.filter(filt).map(lambda feat: ee.Feature(feat).set('split','train'))
#   test = featCollRand.filter(filt.Not()).map(lambda feat: ee.Feature(feat).set('split','test'))
#   return train.merge(test)

def split_train_test(pts):
    """stratify 80/20 train and test points"""
    
    featColl = ee.FeatureCollection(pts)
    featColl = featColl.randomColumn(columnName='random', seed=seed)
    filt = ee.Filter.lt('random',0.8)
    train = featColl.filter(filt)
    test = featColl.filter(filt.Not())
    # print('train size', train.size().getInfo())
    # print('train breakdown',train.aggregate_histogram('LANDCOVER').getInfo())
    # print('test size', test.size().getInfo())
    # print('test breakdown',test.aggregate_histogram('LANDCOVER').getInfo())
    
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

def generate_train_test(input_fc_path:str,year:int,output_basename:str):
    """
    extracts S2 composite data to generated train/test points within reference polygon footprints
    
    """
    
    # input_fc_path = "projects/wwf-sig/assets/kaza-lc/sample_pts/BingaDummyReferenceData"
    input_fc = ee.FeatureCollection(input_fc_path) # provide a polygon FC
    # year = 2021
    # EOSS 2020 LC image as export region possibly
    eossLC = ee.Image("projects/wwf-sig/assets/kaza-lc/Land_Cover_KAZA_2020_TFCA") 

    # process s2 data within reference poly footprints
    s2processed = s2process_refdata(ref_polys=input_fc,ref_label='LANDCOVER',ref_year=2021)

    # extract sample points from s2 data within reference poly footprints
    sampled_pts = strat_sample(s2processed,eossLC.geometry())

    #stratify sample points into train/test
    train,test = split_train_test(sampled_pts)

    # export train and test pts
    train_assetid = f"{output_basename}_{str(year)}_train_pts"
    export_pts(train,train_assetid)

    test_assetid = f"{output_basename}_{str(year)}_test_pts"
    export_pts(test,test_assetid)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
    description="Extract Train and Test Points from Reference Polygon Data",
    usage = "python 01train_test.py -i path/to/reference_polygon_fc -y 2021 -o projects/wwf-sig/assets/kaza-lc/sample_pts/dummyPointsKDW"
    )
    
    parser.add_argument(
    "-i",
    "--input_fc",
    type=str,
    required=True,
    help="The full asset path to the reference polygon FeatureCollection"
    )
    
    parser.add_argument(
    "-y",
    "--year",
    type=int,
    required=True,
    help="The year to generate input data for"
    )

    parser.add_argument(
    "-o",
    "--output",
    type=str,
    required=False,
    help="The output asset path basename for export. Default: 'projects/wwf-sig/assets/kaza-lc/sample_pts/[input_fc_basename]_[train|test]' "
    )

    parser.add_argument(
    "-d",
    "--dry_run",
    dest="dry_run",
    action="store_true",
    help="goes through checks and prints output asset path but does not export.",
    )
    
    args = parser.parse_args()
    
    input_fc = args.input_fc
    year = args.year
    output = args.output
    dry_run = args.dry_run

    if output:
        asset_id_basename=output # user has provided full asset id basename
        output_folder = os.path.dirname(asset_id_basename)
    else:
        output_folder = 'projects/wwf-sig/assets/kaza-lc/sample_pts' #use default folder and asset_id basename for _train and _test exports
        asset_id_basename = f"{output_folder}/{os.path.basename(input_fc)}"
    
    assert check_exists(input_fc) == 0, f"Check input FeatureCollection exists: {input_fc}"
    assert check_exists(output_folder) == 0, f"Check output folder exsits: {output_folder}"
    assert len(str(year)) == 4, "year should conform to YYYY format"
    
    if dry_run:
        print(f"would export: {asset_id_basename}_{str(year)}_train|test_pts")
        exit()
    else:
        generate_train_test(input_fc,year,asset_id_basename)
    
    
    
    
