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
		  }).float();
		img = img.addBands(savi.rename(['SAVI']))

		return img

def addIndices(img):
	ndvi = img.normalizedDifference(['N','R']).rename('NDVI').select('NDVI') # must select otherwise returns img input plus output ND band
	ndwi = img.normalizedDifference(['G','N']).rename('NDWI').select('NDWI')
	savi = SAVI(img).select('SAVI')
	return (ndvi).addBands(ndwi).addBands(savi).toFloat()#.select("NDVI","NDWI","SAVI")


if __name__ == "__main__":
	
	# bandCast = ee.Dictionary({""})
	ee.Initialize()

	year = 2021

	nicfi = ee.ImageCollection('projects/planet-nicfi/assets/basemaps/africa')
	stack = nicfi.filter(ee.Filter.calendarRange(year,year,'year'))

	stack = stack.map(lambda img: ee.Image(img).addBands(addIndices(img))).toBands() #spectral bands are int, indices are float

	#print(stack.bandTypes().getInfo())
	# print(stack.bandNames().size().getInfo())

	aoi = ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/SNMC").geometry().buffer(5000)
	region =  ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/SNMC").geometry().bounds()
								
	outputName = "projects/sig-ee/WWF_KAZA_LC/input_stacks/" + "planet_" + str(year) + "_monthlyCompositeStack"

	task_ordered = ee.batch.Export.image.toAsset(image=ee.Image(stack).clip(aoi), description="Export planet_"+str(year)+"_monthlyCompositeStack", assetId=outputName,region=region.getInfo()['coordinates'], maxPixels=1e13,scale=10 )
					
	task_ordered.start()
	print(f"export started: {outputName}")