# Take Image Collection of RF Primitives, perform pixel-wise maximum of all Primitive probability images to return single-band LC image

# Array computation returns img values from 0 to n-1 due to 0-base indexing, so we .add(1) to match LC strata
# assumes LC strata values are already alphanumerically sorted (Bare:1, Built:2, Crop:3, etc)
def maxProbClassifyFromImage(image): # remapNum,orginalNum
  """
  image: multiband image of probabilities
  remapNum: list, list of intergers 0-N matching the number of probability bands
  originalNum: list, list of inergers n-N matching the number of probability bands
             that represent their desired map values
  """
  maxProbClassification = (image.toArray()
                        .arrayArgmax()
                        .arrayFlatten([['classification']])
                        #// .remap(remapNum, # see comment above we don't rely on remapping since LC strata are in alpha-numeric order
                        #//       originalNum
                        #//       )
                        .rename('classification')
                        )
  return maxProbClassification

def maxProbClassifyFromImageCollection(imagecollection):
  image = imagecollection.toBands()
  return (maxProbClassifyFromImage(image)
          .add(1)).rename('LANDCOVER')