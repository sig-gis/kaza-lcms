#%%
import os
import ee
import argparse
import src.utils.sampling as sampling
from src.utils.check_exists import check_exists
import src.utils.exports as exports

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

## GLOBAL VARS
scale = 10 # for Sentinel2
# landCover is the named field which will hold each
# it is the class band in the image that is being sampled
landCover = 'classification'

def ceoClean(f):
        # LON,LAT,PLOTID,SAMPLEID.,
        fid = f.id()
        coords = f.geometry().coordinates()
        return f.set('LON',coords.get(0),
                    'LAT',coords.get(1),
                    'PLOTID',fid,
                    'SAMPLEID',fid)

def plot_id_global(n,feat):
    """takes an index number (n) and adds it to current PLOTID property of a feature 
            to ensure PLOTID values are globally unique (necessary for multiple sets of AOI sampling)"""
    aoi_id = ee.String(str(n))
    f = ee.Feature(feat)
    gid = aoi_id.cat('_').cat(ee.String(f.get('PLOTID')))
    f = f.set('PLOTID',gid, 'SAMPLEID', gid)
    return f

def main():
    ee.Initialize(project='wwf-sig')

    parser = argparse.ArgumentParser(
    description="Generate Sample Points From an ee.Image",
    usage = "00sample_pts -im input/path/to/image -o output/path/to/sample_pts --n_points 100 --to_drive"
    )
    
    parser.add_argument(
    "-im",
    "--input_image",
    type=str,
    required=True,
    help="asset path to image you are sampling from"
    )

    parser.add_argument(
    "-o",
    "--output",
    type=str,
    required=False,
    help="The output asset path basename for export. Default: 'projects/wwf-sig/assets/kaza-lc/sample_pts/[input_fc_basename]_labelOnly' "
    )
    
    parser.add_argument(
    "--n_points",
    type=int,
    required=False,
    help="Number of points per class. Default: 200"
    )

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
    "-ta",
    "--to_asset",
    dest="to_asset",
    action="store_true",
    help="exports to GEE Asset only",
    )
    
    parser.add_argument(
    "-td",
    "--to_drive",
    dest="to_drive",
    action="store_true",
    help="exports to Google Drive only",
    )
    parser.add_argument(
    "-d",
    "--dry_run",
    dest="dry_run",
    action="store_true",
    help="goes through checks and prints output asset path but does not export.",
    )

    args = parser.parse_args()
    
    input_path = args.input
    output = args.output
    n_points = args.n_points
    class_values = args.class_values
    class_points = args.class_points
    to_asset = args.to_asset
    to_drive = args.to_drive
    dry_run = args.dry_run

    if output:
        asset_id_basename=output # user has provided full asset id basename
        output_folder = os.path.dirname(asset_id_basename)
    else:
        output_folder = 'projects/wwf-sig/assets/kaza-lc/sample_pts' #use default folder and asset_id basename for _train and _test exports
        asset_id_basename = f"{output_folder}/{os.path.basename(input_path)}_sample_pts"
    
    assert check_exists(input_path) == 0, f"Check input FeatureCollection exists: {input_path}"
    assert check_exists(output_folder) == 0, f"Check output folder exsits: {output_folder}"
    
    # value checks if class_values and class_points args are both provided
    if ((class_values != None) and (class_points != None)):
        
        # class_values and class_points must be equal length
        if len(class_values) != len(class_points):
            print(f"Error: class_points and class_values are of unequal length: {class_values} {class_points}")
            exit()

    # if only one is provided, error 
    elif (class_values != None and class_points == None) or (class_values == None and class_points != None):
        print(f"Error: class_values and class_points args are codependent, provide both or neither. class_values:{class_values}, class_points:{class_points}")
    
    # if neither provided, n_points must be provided, otherwise we set a default n_points value 
    else:
        if n_points != None:
            pass
        else:
            print("Warning: Defaulting to equal allocation of default n. Set n_points or class_values and class_points to control sample allocation.")
    
    
    img = ee.Image(input_path)
    bbox = img.geometry().bounds() # region

    samples = sampling.strat_sample(img=img,
                                    class_band=landCover,
                                    region=bbox,
                                    scale=scale,
                                    n_points=n_points,
                                    class_values=class_values,
                                    class_points=class_points).map(ceoClean)

    # set up export info
    description = os.path.basename(asset_id_basename).replace('/','_')
    drive_folder = 'kaza-lc'
    drive_desc = description+'-Drive'
    asset_desc = description+'-Asset'
    selectors = 'LON,LAT,PLOTID,SAMPLEID,'+landCover
    # will export to drive or asset if you specify one or the other
    if to_asset==True and to_drive==False:
        if dry_run:
            print(f"would export (Asset): {asset_id_basename}")
            exit()
        else:
            exports.exportTableToAsset(samples,asset_desc,asset_id_basename)
    
    elif to_drive==True and to_asset==False:
        if dry_run:
            print(f"would export (Drive): {drive_folder}/{drive_desc}")
            exit()
        else:
            exports.exportTableToDrive(samples,drive_desc,drive_folder,selectors)
    
    else: # export both ways if neither or both of the --to_drive and --to_asset flags are given
        if dry_run:
            print(f"would export (Asset): {asset_id_basename}")
            print(f"would export (Drive): {drive_folder}/{drive_desc}")
            exit()
        else:
            exports.exportTableToAsset(samples,asset_desc,asset_id_basename)
            exports.exportTableToDrive(samples,drive_desc,drive_folder,selectors)
        
if __name__ == "__main__":
    main()
