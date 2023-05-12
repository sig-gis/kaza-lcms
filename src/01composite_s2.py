import ee
import os
from src.utils.s2process import s2process, s2process_refdata
from src.utils.exports import exportImgToAsset
from src.utils.check_exists import check_exists
import argparse

def main():
    ee.Initialize(project='wwf-sig')
    parser = argparse.ArgumentParser(
    description="Create Sentinel-2 Composite for an AOI or reference polygons",
    usage = "python 02composite_s2.py -a Zambezi -y 2021 -o projects/wwf-sig/assets/kaza-lc-test/input_stacks"
    )
    
    parser.add_argument(
    "-a",
    "--aoi",
    type=str,
    required=True,
    help="The full asset path to an aoi, or the base name of an exsiting asset located in 'projects/wwf-sig/assets/kaza-lc/aoi/' (i.e. Zambezi)"
    )
    
    parser.add_argument(
    "-y",
    "--year",
    type=int,
    required=True,
    help="Year of data to composite"
    )

    parser.add_argument(
    "-o",
    "--output",
    type=str,
    required=False,
    help="The full asset path for export. Default: 'projects/wwf-sig/assets/kaza-lc/input_stacks/S2_[year]_stack_[aoi]' "
    )

    parser.add_argument(
    "-p",
    "--polygons",
    dest="polygons",
    action="store_true",
    help="set this flag if your aoi (--aoi) is a multi-polygon dataset, not a single polygon AOI",
    )
    
    parser.add_argument(
    "-d",
    "--dry_run",
    dest="dry_run",
    action="store_true",
    help="goes through checks and prints output asset path but does not export.",
    )
    
    args = parser.parse_args()
    
    year = args.year
    aoi = args.aoi
    output = args.output
    polygons = args.polygons
    dry_run = args.dry_run

    if '/' in aoi:
        aoi_path = aoi.strip().rstrip('/')
        aoi_name = aoi_path.split('/')[-1]
    else:
        aoi_path = f"projects/wwf-sig/assets/kaza-lc/aoi/{aoi}"
        aoi_name = aoi
   
    if output:
        asset_id=output # user has provided full asset path to the asset (i.e. assetId for export function)
        outputbase = os.path.dirname(asset_id)
    else:
        outputbase = 'projects/wwf-sig/assets/kaza-lc/input_stacks'
        asset_id = f"{outputbase}/S2_{str(year)}_stack_{aoi_name}" 
    
    # check inputs 
    aoi = ee.FeatureCollection(aoi_path)
    # # trying to get this to work for polygon geoms not one contiguous geometry
    # aoi_buffered = aoi.geometry().buffer(1000) 
    assert check_exists(aoi_path) == 0, f"Check aoi exists: {aoi_path}"
    assert check_exists(outputbase) == 0, f"Check output folder exsits: {outputbase}"
    assert len(str(year)) == 4, "year should conform to YYYY format"
    
    if check_exists(asset_id):
        
        if dry_run:
            print(f"would export: {asset_id}")
        else:
            if polygons:
                # use s2process_refdata() to only process satellite data inside polygons, exporting to polygons' minimum bbox
                region = aoi.geometry().bounds()
                output = s2process_refdata(aoi,'LANDCOVER',year)
                exportImgToAsset(img=output,desc=os.path.basename(asset_id),asset_id=asset_id,region=region,scale=10)
 
            else:
                # use s2process() to process all satellite data inside the aoi, exporting to a 1km buffer of the aoi
                region = aoi.geometry().buffer(1000)
                output = s2process(aoi,year,year)
                exportImgToAsset(img=output,desc=os.path.basename(asset_id),asset_id=asset_id,region=region,scale=10)
    else:
        print(f"Image already exsits: {asset_id}")
        


if __name__ == "__main__":
    main()