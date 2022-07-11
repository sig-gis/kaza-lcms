import ee
import covariates
idx = covariates.indices()


ee.Initialize()


def get_s2_sr_cld_col(aoi, start_date, end_date):
    # Import and filter S2 SR.
    s2_sr_col = (ee.ImageCollection('COPERNICUS/S2_SR')
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', CLOUD_FILTER)))

    # Import and filter s2cloudless.
    s2_cloudless_col = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
        .filterBounds(aoi)
        .filterDate(start_date, end_date))

    # Join the filtered s2cloudless collection to the SR collection by the 'system:index' property.
    return ee.ImageCollection(ee.Join.saveFirst('s2cloudless').apply(**{
        'primary': s2_sr_col,
        'secondary': s2_cloudless_col,
        'condition': ee.Filter.equals(**{
            'leftField': 'system:index',
            'rightField': 'system:index'
        })
    }))
    
    
    
    
        
def add_cloud_bands(img):
    # Get s2cloudless image, subset the probability band.
    cld_prb = ee.Image(img.get('s2cloudless')).select('probability')

    # Condition s2cloudless by the probability threshold value.
    is_cloud = cld_prb.gt(CLD_PRB_THRESH).rename('clouds')

    # Add the cloud probability layer and cloud mask as image bands.
    return img.addBands(ee.Image([cld_prb, is_cloud]))
    
    
def add_shadow_bands(img):
    # Identify water pixels from the SCL band.
    not_water = img.select('SCL').neq(6)

    # Identify dark NIR pixels that are not water (potential cloud shadow pixels).
    SR_BAND_SCALE = 1e4
    dark_pixels = img.select('B8').lt(NIR_DRK_THRESH*SR_BAND_SCALE).multiply(not_water).rename('dark_pixels')

    # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
    shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')));

    # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
    cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, CLD_PRJ_DIST*10)
        .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
        .select('distance')
        .mask()
        .rename('cloud_transform'))

    # Identify the intersection of dark pixels with cloud shadow projection.
    shadows = cld_proj.multiply(dark_pixels).rename('shadows')

    # Add dark pixels, cloud projection, and identified shadows as image bands.
    return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))


def add_cld_shdw_mask(img):
    # Add cloud component bands.
    img_cloud = add_cloud_bands(img)

    # Add cloud shadow component bands.
    img_cloud_shadow = add_shadow_bands(img_cloud)

    # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
    is_cld_shdw = img_cloud_shadow.select('clouds').add(img_cloud_shadow.select('shadows')).gt(0)

    # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
    # 20 m scale is for speed, and assumes clouds don't require 10 m precision.
    is_cld_shdw = (is_cld_shdw.focal_min(2).focal_max(BUFFER*2/20)
        .reproject(**{'crs': img.select([0]).projection(), 'scale': 20})
        .rename('cloudmask'))

    # Add the final cloud-shadow mask to the image.
    return img.addBands(is_cld_shdw)
  
    
def apply_cld_shdw_mask(img):
    # Subset the cloudmask band and invert it so clouds/shadow are 0, else 1.
    not_cld_shdw = img.select('cloudmask').Not()

    # Subset reflectance bands and update their masks, return the result.
    return img.select('B.*').updateMask(not_cld_shdw)
    
def add_covariates(img):
    "Adds select indices to the S2 image, assumes band names have already been renamed (blue,green,red,etc)"
    covariates = ["blue","green","red","nir","swir1","swir2","EVI","SAVI","IBI",] # full list of unique spectral covariate bands
    img = ee.Image(img).addBands(idx.EVI(img)).addBands(idx.SAVI(img)).addBands(idx.IBI(img))
    img = img.select(covariates) # because .addBands() will create duplicates of pre-existing bands
    return img

def rename_month_bands(img:ee.Image) :
    def edit_names(str):
        month_str = ee.String("_").cat(ee.Number.parse(ee.String(str).split('_').get(0)).add(1).format())
        base = ee.String("_").cat(ee.String(str).split('_').get(1))
        return ee.String("S2").cat(month_str).cat(base)
    return ee.Image(img).rename(img.bandNames().map(edit_names))
 
if __name__ == "__main__":
    #def composite(aoi,year):

    ee.Initialize()
    year = 2021



    aoi = ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/SNMC").geometry().buffer(5000)


    CLOUD_FILTER = 70
    CLD_PRB_THRESH = 40
    NIR_DRK_THRESH = 0.15
    CLD_PRJ_DIST = 2
    BUFFER = 100

    months = [1,2,3,4,5,6,7,8,9,10,11,12]
    img_list=[]
    for month in months:
        
        START_DATE = ee.Date.fromYMD(year,month,1)
        END_DATE = ee.Date.fromYMD(year,month,30)
        
        if month == 2:
            END_DATE = ee.Date.fromYMD(year,month,28)
             
        s2_sr_cld_col = get_s2_sr_cld_col(aoi, START_DATE, END_DATE)

                
        img =  ee.Image(s2_sr_cld_col.map(add_cld_shdw_mask)
                    .map(apply_cld_shdw_mask).median()
                    .toInt().select(["B2","B3","B4","B8","B11","B12"],['blue','green','red','nir','swir1','swir2'])
                    )
        #print(img.bandNames().size().getInfo())
        img = add_covariates(img)
        #print(month,img.bandNames().size().getInfo())                
        
        img = ee.Image(img).set("system:time_start",ee.Date.fromYMD(year,month,1))
        img_list.append(img)
        
      
    stack = ee.ImageCollection.fromImages(img_list).toBands()
    #print(stack.bandNames().getInfo())
    
    topo = idx.addTopography(img).select("elevation","slope","aspect","eastness","northness")
    stack = rename_month_bands(stack).addBands(topo)
    #print(stack.bandNames().getInfo())
  
    region =  ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/SNMC").geometry().bounds()
                                
    outputName = "projects/sig-ee/WWF_KAZA_LC/input_stacks/" + "sentinel2_" + str(year) + "_monthlyCompositeStack_SNMC"

    task_ordered = ee.batch.Export.image.toAsset(image=ee.Image(stack).clip(aoi).toInt(), description="Export sentinel2_"+str(year)+"_monthlyCompositeStack_SNMC", assetId=outputName,region=region.getInfo()['coordinates'], maxPixels=1e13,scale=10 )
                    
    task_ordered.start()
    print(f"export started: {outputName}")