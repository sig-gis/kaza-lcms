import ee
import os
from src.utils.s2process import s2process, s2process_refdata
from src.utils.exports import exportImgToAsset
from src.utils.check_exists import check_exists
import argparse

ee.Initialize(project='wwf-sig')
poly_path = "projects/wwf-sig/assets/kaza-lc/aoi/testSeshekeWater"
aoi_path = "projects/wwf-sig/assets/kaza-lc/sample_pts/BingaDummyReferencePolys"
year=2020
asset_id = 'projects/wwf-sig/assets/kaza-lc/input_stacks/S2_2020_stack_BingaDummyReferencePolys_testMultiPolyExportUpdateMask'

polygons=True

if polygons:
    # check inputs 
    aoi = ee.FeatureCollection(poly_path)
    # trying to get this to work for polygon geoms not one contiguous geometry
    aoi_buffered = aoi.geometry().buffer(1000).bounds() # .bounds() should make the geom easier to parse like a AOI poly geom?
    r=aoi_buffered#.getInfo()['coordinates']
    output = ee.Image(s2process(aoi,year,year)).clip(aoi)

if polygons:
    output = ee.Image(s2process(aoi,year,year)).clip(aoi)
else:
    output = s2process_refdata(aoi,'LANDCOVER',2020) # try refdata func instead with an export region of one polygon geom

exportImgToAsset(img=output,desc=os.path.basename(asset_id),asset_id=asset_id,region=r,scale=10)
