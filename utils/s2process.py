import ee
from utils import covariates
from utils import harmonics
idx = covariates.indices()

CLOUD_FILTER = 70
CLD_PRB_THRESH = 40
NIR_DRK_THRESH = 0.15
CLD_PRJ_DIST = 2
BUFFER = 100

# the point at which using this workflow for generating an inference stack may diverge from using this workflow to extract data to reference polygons would be
# after get_s2_sr_cld_col, before add_cld_shadow_mask and apply_cld_shadow_mask are run,
# we would want to use the rasterized polygons to mask the result of get_s2_sr_cld_col before doing the cloud/shadow masking and computing covariates
# there's a chance it will work ok without doing this though, its just that the polygons will be so spread out for field collected data so more s2 images needing
# to be pulled...

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

# main-level function
def s2process(aoi:ee.FeatureCollection,start_year:int,end_year:int):
    """Computes preprocessed Sentinel-2 multi-band composite for an AOI"""
    start_date = ee.Date.fromYMD(start_year,1,1)
    end_date = ee.Date.fromYMD(end_year,12,31)
    
    s2_sr_cld_col = get_s2_sr_cld_col(aoi, start_date, end_date)

    imgColl =  ee.ImageCollection(s2_sr_cld_col.map(add_cld_shdw_mask)
                .map(apply_cld_shdw_mask)
                .select(["B2","B3","B4","B8","B11","B12"],['blue','green','red','nir','swir1','swir2'])
                )

    percentiles = (imgColl.map(add_covariates)
                .reduce(ee.Reducer.percentile(percentiles=[10,25,50,75,90]))
    )

    # add time bands
    timeField = "system:time_start"
    timeCollection = harmonics.addTimeConstant(imgColl, timeField)

    # compute harmonics
    harmonics_nir =  harmonics.calculateHarmonic(timeCollection,ee.String("nir"))
    harmonics_swir = harmonics.calculateHarmonic(timeCollection,ee.String("swir1"))

    pct_harmonics = ee.Image.cat([percentiles,harmonics_nir,harmonics_swir])

    stack = idx.addTopography(pct_harmonics)
    return ee.Image(stack)

def s2process_refdata(ref_polys:ee.FeatureCollection,ref_label:str,ref_year:int):
    """Computes preprocessed Sentinel-2 multi-band composite within reference polygons"""
    start_date = ee.Date.fromYMD(ref_year,1,1)
    end_date = ee.Date.fromYMD(ref_year,12,31)
    
    ref_poly_img = ee.Image(0).paint(ref_polys,ref_label).rename(ref_label).selfMask()

    s2_sr_cld_col = get_s2_sr_cld_col(ref_polys, start_date, end_date)

    imgColl =  ee.ImageCollection(s2_sr_cld_col.map(add_cld_shdw_mask)
                .map(lambda img: ee.Image(img).updateMask(ref_poly_img)) #mask imgs to ref poly areas before doing more heavy compute
                .map(apply_cld_shdw_mask)
                .select(["B2","B3","B4","B8","B11","B12"],['blue','green','red','nir','swir1','swir2'])
                )

    percentiles = (imgColl.map(add_covariates)
                .reduce(ee.Reducer.percentile(percentiles=[10,25,50,75,90]))
    )

    # add time bands
    timeField = "system:time_start"
    timeCollection = harmonics.addTimeConstant(imgColl, timeField)

    # compute harmonics
    harmonics_nir =  harmonics.calculateHarmonic(timeCollection,ee.String("nir"))
    harmonics_swir = harmonics.calculateHarmonic(timeCollection,ee.String("swir1"))

    pct_harmonics = ee.Image.cat([percentiles,harmonics_nir,harmonics_swir])

    stack = idx.addTopography(pct_harmonics)
    return ee.Image(stack)