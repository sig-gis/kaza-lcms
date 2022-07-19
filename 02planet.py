#planet covariates
import ee
import covariates
idx = covariates.indices()

def SAVI(img):
		# Add Soil Adjust Vegetation Index (SAVI)
		# using L = 0.5;
		savi = img.expression(
			'(NIR - RED) * (1 + 0.5)/(NIR + RED + 0.5)', {
			  'NIR': img.select('N'),
			  'RED': img.select('R')
		  }).float()
		img = img.addBands(savi.rename(['SAVI']))

		return img

def addIndices(img):
	ndvi = img.normalizedDifference(['N','R']).rename('NDVI').select('NDVI') # must select otherwise returns img input plus output ND band
	ndwi = img.normalizedDifference(['G','N']).rename('NDWI').select('NDWI')
	savi = SAVI(img).select('SAVI')
	return (ndvi).addBands(ndwi).addBands(savi).toFloat()#.select("NDVI","NDWI","SAVI")


if __name__ == "__main__":
	
	ee.Initialize()
	# SNMC Mufunta or Zambezi
	aoi_s = "Mufunta"
	year = 2021

	nicfi = ee.ImageCollection('projects/planet-nicfi/assets/basemaps/africa')
	stack = nicfi.filter(ee.Filter.calendarRange(year,year,'year'))

	stack = stack.map(lambda img: ee.Image(img).addBands(addIndices(img))).toBands() 
	stack = idx.addTopography(stack)
	
	aoi = ee.FeatureCollection(f"projects/sig-ee/WWF_KAZA_LC/aoi/{aoi_s}").geometry().buffer(5000)
	region =  ee.FeatureCollection(f"projects/sig-ee/WWF_KAZA_LC/aoi/{aoi_s}").geometry().bounds()
								
	outputName = f"projects/sig-ee/WWF_KAZA_LC/input_stacks/planet_{str(year)}_monthlyCompositeStack_{aoi_s}"
	desc = outputName.split('/')[-1]
	
	task_ordered = ee.batch.Export.image.toAsset(image=ee.Image(stack).clip(aoi), description=desc, assetId=outputName,region=region.getInfo()['coordinates'], maxPixels=1e13,scale=10 )
					
	task_ordered.start()
	print(f"export started: {outputName}")