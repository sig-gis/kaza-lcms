import argparse
import os
from utils.check_exists import check_exists
from utils.sampling import generate_train_test
import ee
ee.Initialize(project='wwf-sig')

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
    "--n_points",
    type=int,
    required=False,
    help="Number of points per class. Default: 200"
    )
    # fix list parsing..
    parser.add_argument(
    '--class_values', 
    type=int, 
    nargs='+',
    required=False,
    help="list of unique LANDCOVER values in input Feature Collection"
    )


    parser.add_argument(
    "--class_points",
    type=int,
    nargs='+',
    required=False,
    help="number of samples to collect per class"
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
    n_points = args.n_points
    class_values = args.class_values
    class_points = args.class_points

    if output:
        asset_id_basename=output # user has provided full asset id basename
        output_folder = os.path.dirname(asset_id_basename)
    else:
        output_folder = 'projects/wwf-sig/assets/kaza-lc/sample_pts' #use default folder and asset_id basename for _train and _test exports
        asset_id_basename = f"{output_folder}/{os.path.basename(input_fc)}"
    
    assert check_exists(input_fc) == 0, f"Check input FeatureCollection exists: {input_fc}"
    assert check_exists(output_folder) == 0, f"Check output folder exsits: {output_folder}"
    assert len(str(year)) == 4, "year should conform to YYYY format"
    
    # class_values and class_points must be equal length
    if len(class_values) != len(class_points):
        raise ValueError(f"class_points and class_values are of unequal length: {class_values} {class_points}")

    # user may not want to sample all classes, but provide warning to catch user error
    class_values_actual = ee.FeatureCollection(input_fc).aggregate_array('LANDCOVER').distinct().sort().getInfo()
    if class_values_actual != class_values:
        raise RuntimeWarning(f"All classes in the reference dataset will not be sampled with class_values provided by user. EE-Reported class_values:{class_values}")
    
    if dry_run:
        print(f"would export: {asset_id_basename}_{str(year)}_train|test_pts")
        exit()
    else:
        generate_train_test(input_fc,year,asset_id_basename,n_points,class_values,class_points)
    
    
    
    
