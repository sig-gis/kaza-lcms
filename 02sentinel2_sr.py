import ee
import os
# from utils import covariates
# from utils import harmonics
from utils.s2process import s2process
from utils.exports import exportImgToAsset
from utils.check_exists import check_exists
import argparse
# idx = covariates.indices()

# def get_s2_sr_cld_col(aoi, start_date, end_date):
#     # Import and filter S2 SR.
#     s2_sr_col = (ee.ImageCollection('COPERNICUS/S2_SR')
#         .filterBounds(aoi)
#         .filterDate(start_date, end_date)
#         .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', CLOUD_FILTER)))

#     # Import and filter s2cloudless.
#     s2_cloudless_col = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
#         .filterBounds(aoi)
#         .filterDate(start_date, end_date))

#     # Join the filtered s2cloudless collection to the SR collection by the 'system:index' property.
#     return ee.ImageCollection(ee.Join.saveFirst('s2cloudless').apply(**{
#         'primary': s2_sr_col,
#         'secondary': s2_cloudless_col,
#         'condition': ee.Filter.equals(**{
#             'leftField': 'system:index',
#             'rightField': 'system:index'
#         })
#     }))
    
# def add_cloud_bands(img):
#     # Get s2cloudless image, subset the probability band.
#     cld_prb = ee.Image(img.get('s2cloudless')).select('probability')

#     # Condition s2cloudless by the probability threshold value.
#     is_cloud = cld_prb.gt(CLD_PRB_THRESH).rename('clouds')

#     # Add the cloud probability layer and cloud mask as image bands.
#     return img.addBands(ee.Image([cld_prb, is_cloud]))
    
# def add_shadow_bands(img):
#     # Identify water pixels from the SCL band.
#     not_water = img.select('SCL').neq(6)

#     # Identify dark NIR pixels that are not water (potential cloud shadow pixels).
#     SR_BAND_SCALE = 1e4
#     dark_pixels = img.select('B8').lt(NIR_DRK_THRESH*SR_BAND_SCALE).multiply(not_water).rename('dark_pixels')

#     # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
#     shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')));

#     # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
#     cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, CLD_PRJ_DIST*10)
#         .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
#         .select('distance')
#         .mask()
#         .rename('cloud_transform'))

#     # Identify the intersection of dark pixels with cloud shadow projection.
#     shadows = cld_proj.multiply(dark_pixels).rename('shadows')

#     # Add dark pixels, cloud projection, and identified shadows as image bands.
#     return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))

# def add_cld_shdw_mask(img):
#     # Add cloud component bands.
#     img_cloud = add_cloud_bands(img)

#     # Add cloud shadow component bands.
#     img_cloud_shadow = add_shadow_bands(img_cloud)

#     # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
#     is_cld_shdw = img_cloud_shadow.select('clouds').add(img_cloud_shadow.select('shadows')).gt(0)

#     # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
#     # 20 m scale is for speed, and assumes clouds don't require 10 m precision.
#     is_cld_shdw = (is_cld_shdw.focal_min(2).focal_max(BUFFER*2/20)
#         .reproject(**{'crs': img.select([0]).projection(), 'scale': 20})
#         .rename('cloudmask'))

#     # Add the final cloud-shadow mask to the image.
#     return img.addBands(is_cld_shdw)
  
# def apply_cld_shdw_mask(img):
#     # Subset the cloudmask band and invert it so clouds/shadow are 0, else 1.
#     not_cld_shdw = img.select('cloudmask').Not()

#     # Subset reflectance bands and update their masks, return the result.
#     return img.select('B.*').updateMask(not_cld_shdw)
    
# def add_covariates(img):
#     "Adds select indices to the S2 image, assumes band names have already been renamed (blue,green,red,etc)"
#     covariates = ["blue","green","red","nir","swir1","swir2","EVI","SAVI","IBI",] # full list of unique spectral covariate bands
#     img = ee.Image(img).addBands(idx.EVI(img)).addBands(idx.SAVI(img)).addBands(idx.IBI(img))
#     img = img.select(covariates) # because .addBands() will create duplicates of pre-existing bands
#     return img

# def rename_month_bands(img:ee.Image) :
#     def edit_names(str):
#         month_str = ee.String("_").cat(ee.Number.parse(ee.String(str).split('_').get(0)).add(1).format())
#         base = ee.String("_").cat(ee.String(str).split('_').get(1))
#         return ee.String("S2").cat(month_str).cat(base)
#     return ee.Image(img).rename(img.bandNames().map(edit_names))
 
####### Percentiles, harmonics, topo covariates ##############

if __name__ == "__main__":
    ee.Initialize(project='wwf-sig')
    parser = argparse.ArgumentParser(
    description="Create Input Stack for Classifier from Sentinel S2",
    usage = "python 02sentinel2_sr.py -a Zambezi -y 2021 -o projects/wwf-sig/assets/kaza-lc-test/input_stacks"
    )
    
    parser.add_argument(
    "-a",
    "--aoi",
    type=str,
    required=True,
    help="The full asset path to an aoi, or the base name of an exsiting asset located in 'projects/wwf-sig/assets/kaza-lc/aoi/' (i.e. Zambezi)"
    )
    
    parser.add_argument(
    "-y",
    "--year",
    type=int,
    required=True,
    help="The year to generate covariates."
    )

    parser.add_argument(
    "-o",
    "--output",
    type=str,
    required=False,
    help="The full asset path for export. Default: 'projects/wwf-sig/assets/kaza-lc/input_stacks/S2_[year]_stack_[aoi]' "
    )

    parser.add_argument(
    "-d",
    "--dry_run",
    dest="dry_run",
    action="store_true",
    help="goes through checks and prints output asset path but does not export.",
    )
    
    args = parser.parse_args()
    
    year = args.year#2021
    aoi = args.aoi
    output = args.output
    dry_run = args.dry_run

    if '/' in aoi:
        aoi_path = aoi.strip().rstrip('/')
        aoi_name = aoi_path.split('/')[-1]
    else:
        aoi_path = f"projects/wwf-sig/assets/kaza-lc/aoi/{aoi}"
        aoi_name = aoi
    # print('aoi_path',aoi_path)
    # print('aoi_name',aoi_name)
    if output:
        asset_id=output # user has provided full asset path to the asset (i.e. assetId for export function)
        outputbase = os.path.dirname(asset_id)
    else:
        outputbase = 'projects/wwf-sig/assets/kaza-lc/input_stacks'
        asset_id = f"{outputbase}/S2_{str(year)}_stack_{aoi_name}" 
    
    # print('output',output)
    # print('outputbase',outputbase)
    # print('asset_id',asset_id)
    
    # check inputs 
    aoi = ee.FeatureCollection(aoi_path)
    aoi_buffered = aoi.geometry().buffer(5000)
    assert check_exists(aoi_path) == 0, f"Check aoi exists: {aoi_path}"
    assert check_exists(outputbase) == 0, f"Check output folder exsits: {outputbase}"
    assert len(str(year)) == 4, "year should conform to YYYY format"

    # CLOUD_FILTER = 70
    # CLD_PRB_THRESH = 40
    # NIR_DRK_THRESH = 0.15
    # CLD_PRJ_DIST = 2
    # BUFFER = 100

    # START_DATE = ee.Date.fromYMD(year,1,1)
    # END_DATE = ee.Date.fromYMD(year,12,31)
    
    if check_exists(asset_id):
        # # make this entire portion a submodule
        # s2_sr_cld_col = get_s2_sr_cld_col(aoi_buffered, START_DATE, END_DATE)


        # imgColl =  ee.ImageCollection(s2_sr_cld_col.map(add_cld_shdw_mask)
        #             .map(apply_cld_shdw_mask)
        #             .select(["B2","B3","B4","B8","B11","B12"],['blue','green','red','nir','swir1','swir2'])
        #             )
        
        # percentiles = (imgColl.map(add_covariates)
        #             .reduce(ee.Reducer.percentile(percentiles=[10,25,50,75,90]))
        # )
        
        # # add time bands
        # timeField = "system:time_start"
        # timeCollection = harmonics.addTimeConstant(imgColl, timeField)
        
        # # compute harmonics
        # harmonics_nir =  harmonics.calculateHarmonic(timeCollection,ee.String("nir"))
        # harmonics_swir = harmonics.calculateHarmonic(timeCollection,ee.String("swir1"))
        
        # pct_harmonics = ee.Image.cat([percentiles,harmonics_nir,harmonics_swir])
        
        # stack = idx.addTopography(pct_harmonics)
        
        ## region =  aoi.geometry().bounds()

        # task = ee.batch.Export.image.toAsset(
        #     image=ee.Image(stack).clip(aoi), # do we want ot clip image to aoi or aoi buffer??
        #     description=os.path.basename(asset_id), # f"S2_{str(year)}_stack_{aoi_name}",
        #     assetId=asset_id,
        ##     region=region.getInfo()['coordinates'],
        #     maxPixels=1e13,
        #     scale=10 )
        if dry_run:
            print(f"would export: {asset_id}")
        else:
            output = s2process(aoi,year,year)
            exportImgToAsset(img=output,desc=os.path.basename(asset_id),asset_id=asset_id,region=aoi_buffered,scale=10)
    else:
        print(f"Image already exsits: {asset_id}")
        
