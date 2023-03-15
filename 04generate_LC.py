import os
import ee
import argparse
from utils import helper

# Take Image Collection of RF Primitives, perform pixel-wise maximum of all Primitive probability images to return single-band LC image

# don't THINK we need the remapping of array values that John originally had in the function
def maxProbClassifyFromImage(image): # remapNum,orginalNum
  #// image: multiband image of probabilities
  #// remapNum: list, list of intergers 0-N matching the number of probability bands
  #// originalNum: list, list of inergers n-N matching the number of probability bands
  #//    that represent their desired map values
  maxProbClassification = (image.toArray()
                        .arrayArgmax()
                        .arrayFlatten([['classification']])
                        #// .remap(remapNum,
                        #//       originalNum
                        #//       )
                        .rename('classification')
                        )
  return maxProbClassification

def maxProbClassifyFromImageCollection(imagecollection):
  image = imagecollection.toBands()
  return maxProbClassifyFromImage(image)


# from = [0,1,2,3,4,5,6,7]
# to = [1,2,3,4,5,6,7,8]


def export_img(img,asset_id,aoi):
    """Export image to Primitives imageCollection"""
    
    # aoi = img.geometry().bounds()
    # aoi = ee.FeatureCollection(f"projects/wwf-sig/assets/kaza-lc/aoi/{aoi_s}")
    desc = os.path.basename(asset_id).replace('/','_') # f"{sensor}_{year}_LandCover_{aoi_s}"
    task = ee.batch.Export.image.toAsset(
          image=ee.Image(img),
          description=desc,
          assetId=asset_id, 
          region=aoi, #.geometry().bounds(), 
          scale=10, 
          crs='EPSG:32734', 
          maxPixels=1e13)

    task.start()
    print(f"Export Started for {asset_id}")
    

if __name__ == "__main__":
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

    args = parser.parse_args()

    input_path = args.input
    output_path = args.output
    
    if output_path:
      outputbase = os.path.dirname(output_path)
      asset_id = output_path
      if helper.check_exists(outputbase) == 0:
         os.popen(f"earthengine create folder {outputbase}").read()
      else:
         raise ValueError(f"Check output parent folder exists: {outputbase}")
    else:
       outputbase = "projects/wwf-sig/assets/kaza-lc/output_landcover"
       # assumes 'Primitives' in input_path string)
       asset_id = f"{outputbase}/{os.path.basename(input_path).replace('Primitives','LandCover')}"
    
    # If input ImageCollection does not exist, throw error
    assert helper.check_exists(asset_id), f"Output image already exists: {asset_id}"
    
    # If output Image exists already, throw error
    assert helper.check_exists(input_path) == 0, f"Input Primitives Collection does not exist: {input_path}"
    
    prims = ee.ImageCollection(input_path)
    max = maxProbClassifyFromImageCollection(prims)
    aoi = prims.first().geometry().bounds()
    export_img(max,asset_id,aoi)