import argparse
import os
from src.utils.check_exists import check_exists
from src.utils.sampling import strat_sample_w_extraction, split_train_test
from src.utils.exports import exportTableToAsset
import ee
import numpy as np
ee.Initialize(project='wwf-sig')

def main():
    parser = argparse.ArgumentParser(
    description="Extract Train and Test Data from Input Image within Reference Polygon Areas",
    usage = "python 01train_test.py -i path/to/reference_polygon_fc -y 2021 -o projects/wwf-sig/assets/kaza-lc/sample_pts/dummyPointsKDW"
    )
    
    parser.add_argument(
    "-rp",
    "--reference_polygons",
    type=str,
    required=True,
    help="The full asset path to the reference polygon ee.FeatureCollection"
    )
    
    parser.add_argument(
    "-im",
    "--input_img",
    type=str,
    required=True,
    help="The full asset path to the input stack ee.Image"
    )

    parser.add_argument(
    "-o",
    "--output",
    type=str,
    required=False,
    help="The output asset path basename for export. Default: 'projects/wwf-sig/assets/kaza-lc/sample_pts/[input_fc_basename]_[train|test]' "
    )

    # parser.add_argument(
    # "--n_points",
    # type=int,
    # required=False,
    # help="Number of points per class. Default: 200"
    # )
    
    parser.add_argument(
    '--class_values', 
    type=int, 
    nargs='+',
    required=True,
    help="list of unique LANDCOVER values in input Feature Collection"
    )

    parser.add_argument(
    "--class_points",
    type=int,
    nargs='+',
    required=True,
    help="number of samples to collect per class"
    )
    
    parser.add_argument(
    "-ns",
    "--no_split",
    dest="no_split",
    action="store_true",
    help="don't split extracted points into train and test",
    )
    
    parser.add_argument(
    "-r",
    "--reshuffle",
    dest="reshuffle",
    action="store_true",
    help="randomizes seed used in all functions",
    )

    parser.add_argument(
    "-d",
    "--dry_run",
    dest="dry_run",
    action="store_true",
    help="goes through checks and prints output asset path but does not export",
    )
    
    args = parser.parse_args()
    
    input_fc = args.reference_polygons
    input_img = args.input_img
    output = args.output
    # n_points = args.n_points
    class_values = args.class_values
    class_points = args.class_points
    dry_run = args.dry_run
    no_split = args.no_split
    reshuffle = args.reshuffle

    if output: # user has provided full asset id basename
        asset_id_basename=output 
        output_folder = os.path.dirname(asset_id_basename)
    else:
        output_folder = 'projects/wwf-sig/assets/kaza-lc/sample_pts' #use default folder and asset_id basename for _train and _test exports
        asset_id_basename = f"{output_folder}/{os.path.basename(input_fc)}"
    
    assert check_exists(input_fc) == 0, f"Check input FeatureCollection exists: {input_fc}"
    assert check_exists(output_folder) == 0, f"Check output folder exsits: {output_folder}"
    
    # # value checks if class_values and class_points args are both provided
    # if ((class_values != None) and (class_points != None)):
        
    # class_values and class_points must be equal length
    if len(class_values) != len(class_points):
        print(f"Error: class_points and class_values are of unequal length: {class_values} {class_points}")
        exit()
        
    # user may not want to sample all classes, but provide warning to catch user error
    class_values_actual = ee.FeatureCollection(input_fc).aggregate_array('LANDCOVER').distinct().sort().getInfo()
    if class_values_actual != class_values:
        print(f"Warning: All classes in the reference dataset will not be sampled with class_values provided by user (EE-Reported class_values:{class_values_actual}). Processing will continue.")

    # # if only one is provided, error 
    # elif (class_values != None and class_points == None) or (class_values == None and class_points != None):
    #     print(f"Error: class_values and class_points args are codependent, provide both or neither. class_values:{class_values}, class_points:{class_points}")
    
    # else:
    #     print(f"Error: class_values and class_points args are codependent, provide both or neither. class_values:{class_values}, class_points:{class_points}")
    # i think we get rid of n_points because it makes logic more complex. 
    # if neither provided, n_points must be provided, otherwise we set a default n_points value 
    # else:
    #     if n_points != None:
    #         n_points=100
    #         class_points = 
    #     else:
    #         print(f"Warning: Defaulting to equal allocation of default n ({n_points}). Set n_points or class_values and class_points to control sample allocation.")
    
    if dry_run:
        if no_split:
            print(f"would export (Asset): {asset_id_basename}_pts")
            exit()
        else:
            print(f"would export (Asset): {asset_id_basename}_train|test_pts")
            exit()
    else:
        # do the work
        # default seed set, will re-randomize seed if reshuffle==True
        seed=90210
        if reshuffle:
            seed = np.random.randint(1, high=None, size=None, dtype=int)
            print(f"reshuffled new seed: {seed}")
        
        image = ee.Image(input_img)
        fc = ee.FeatureCollection(input_fc)
        pts = strat_sample_w_extraction(img=image,
                                         collection=fc,
                                         class_band='LANDCOVER', # should this be a CLI arg or set in model_inputs.py? i feel like no
                                         scale=10, # should this be a CLI arg or set in model_inputs.py? i feel like no
                                         seed=seed, # should this be a CLI arg or set in model_inputs.py? i feel like no
                                         class_values=class_values,
                                         class_points=class_points)
        
        if no_split==False: # split into train and test pts
            train,test = split_train_test(pts,seed)
            train_assetid = f"{asset_id_basename}_train_pts"
            train_description = os.path.basename(train_assetid).replace('/','_')
            exportTableToAsset(train,train_description,train_assetid)

            test_assetid = f"{asset_id_basename}_test_pts"
            test_description = os.path.basename(test_assetid).replace('/','_')
            exportTableToAsset(test,test_description,test_assetid)
        
        else: # export all pts as is
            assetid = f"{asset_id_basename}_pts"
            description = os.path.basename(assetid).replace('/','_')
            exportTableToAsset(pts,description,assetid)
        
    
    
      

            

if __name__ == "__main__":
    main()



