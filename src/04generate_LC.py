import os
import ee
import argparse
from src.utils.assemblage import maxProbClassifyFromImageCollection
from src.utils.check_exists import check_exists
from src.utils.exports import exportImgToAsset
    
def main():
    ee.Initialize(project='wwf-sig')
    
    parser = argparse.ArgumentParser(
    description="Generate single land cover image from land cover primitives image collection",
    usage = "python 04generate_LC.py -i input_primitive_collection -o output_landcover_image"
    )
    
    parser.add_argument(
    "-i",
    "--input",
    type=str,
    required=True,
    help="GEE asset path to input Primitives ImageCollection"
    )

    parser.add_argument(
    "-o",
    "--output",
    type=str,
    required=False,
    help="GEE asset path for export. Defaults to: projects/wwf-sig/assets/kaza-lc/output_landcover/[LandCover]_input_basename"
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
    output_path = args.output
    dry_run = args.dry_run

    if output_path:
      outputbase = os.path.dirname(output_path)
      asset_id = output_path
      if check_exists(outputbase) == 0:
         os.popen(f"earthengine create folder {outputbase}").read()
      else:
         raise ValueError(f"Check output parent folder exists: {outputbase}")
    else:
       outputbase = "projects/wwf-sig/assets/kaza-lc/output_landcover"
       # assumes 'Primitives' in input_path string)
       asset_id = f"{outputbase}/{os.path.basename(input_path).replace('Primitives','LandCover')}"
    
    # If input ImageCollection does not exist, throw error
    assert check_exists(asset_id), f"Output image already exists: {asset_id}"
    
    # If output Image exists already, throw error
    assert check_exists(input_path) == 0, f"Input Primitives Collection does not exist: {input_path}"
    
    if dry_run:
            print(f"would export: {asset_id}")
    else:
      prims = ee.ImageCollection(input_path)
      max = maxProbClassifyFromImageCollection(prims)
      aoi = prims.first().geometry().bounds()
      description = os.path.basename(asset_id).replace('/','_')
      exportImgToAsset(img=max,desc=description,asset_id=asset_id,region=aoi,scale=10)

if __name__ == "__main__":
   main()    