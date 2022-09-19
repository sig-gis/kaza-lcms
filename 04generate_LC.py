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


def export_img(img,sensor,aoi_s,year):
    """Export image to Primitives imageCollection"""
    
    aoi = ee.FeatureCollection(f"projects/{project}/assets/kaza-lc/aoi/{aoi_s}")
    imgcoll_p = f"projects/{project}/assets/kaza-lc/output_landcover"
    desc = f"{sensor}_{year}_LandCover_{aoi_s}"
    output_id = f"{imgcoll_p}/{desc}"
    if helper.check_exsits(output_id):
      task = ee.batch.Export.image.toAsset(
          image=ee.Image(img),
          description=desc,
          assetId=output_id, 
          region=aoi.geometry().bounds(), 
          scale=10, 
          crs='EPSG:32734', 
          maxPixels=1e13)

      task.start()
      print(f"Export Started for {output_id}")
    else:
        print(f"Image already exsits: {output_id}")

if __name__ == "__main__":
    ee.Initialize()
    
    parser = argparse.ArgumentParser(
    description="Generate single land cover image from land cover primitives image collection",
    usage = "python 04generate_LC.py -p wwf-sig -a Zambezi -y 2021 -s S2 "
    )

    
    parser.add_argument(
    "-p",
    "--project",
    type=str,
    required=True
    )
    
    parser.add_argument(
    "-a",
    "--aoi_string",
    type=str,
    required=True
    )
    
    parser.add_argument(
    "-y",
    "--year",
    type=int,
    required=True
    )
    
    parser.add_argument(
    "-s",
    "--sensor",
    type=str,
    required=True
    )
    
    args = parser.parse_args()

    project=args.project #kaza-lc
    aoi_s = args.aoi_string #SNMC
    year = args.year #2021
    sensor=args.sensor #S2

    prims = ee.ImageCollection(f"projects/{project}/assets/kaza-lc/output_landcover/{sensor}_{year}_Primitives_{aoi_s}")
    max = maxProbClassifyFromImageCollection(prims)
    export_img(max,sensor,aoi_s,year)