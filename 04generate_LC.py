import ee

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
    
    aoi = ee.FeatureCollection(f"projects/sig-ee/WWF_KAZA_LC/aoi/{aoi_s}")
    imgcoll_p = "projects/sig-ee/WWF_KAZA_LC/output_landcover"
    desc = f"{sensor}{aoi_s}{year}LandCover"
    
    task = ee.batch.Export.image.toAsset(
        image=ee.Image(img),
        description=desc,
        assetId=f"{imgcoll_p}/{desc}", 
        region=aoi.geometry().bounds(), 
        scale=10, 
        crs='EPSG:32734', 
        maxPixels=1e13)

    task.start()
    print(f"Export Started for {desc}")

if __name__ == "__main__":
    ee.Initialize()
    sensor = "planet"
    aoi_s = "SNMC"
    year = "2021"

    prims = ee.ImageCollection(f"projects/sig-ee/WWF_KAZA_LC/output_landcover/{sensor}{aoi_s}{year}Primitives")
    max = maxProbClassifyFromImageCollection(prims)
    export_img(max,sensor,aoi_s,year)