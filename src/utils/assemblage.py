import os
import ee

# Take Image Collection of RF Primitives, perform pixel-wise maximum of all Primitive probability images to return single-band LC image

# Array computation returns img values from 0 to n-1 due to 0-base indexing, so we .add(1) to match LC strata
# assumes LC strata values are already alphanumerically sorted (Bare:1, Built:2, Crop:3, etc)
def maxProbClassifyFromImage(image): # remapNum,orginalNum
  # image: multiband image of probabilities
  # remapNum: list, list of intergers 0-N matching the number of probability bands
  # originalNum: list, list of inergers n-N matching the number of probability bands
  #   that represent their desired map values
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
  return (maxProbClassifyFromImage(image)
          .add(1))

# would need to do a remap if order is not alphanumeric
# from = [0,1,2,3,4,5,6,7]
# to = [1,2,3,4,5,6,7,8]

def export_img(img,asset_id,aoi):
    """Export image to Primitives imageCollection"""
    
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