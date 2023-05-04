import ee
import os
from src.utils.check_exists import check_exists
ee.Initialize(project='wwf-sig')

def exportImgToAsset(img,desc,asset_id,region,scale):
    export_region = region
    task = ee.batch.Export.image.toAsset(
        image=ee.Image(img),
        description=desc,
        assetId=asset_id,
        region=export_region.getInfo()['coordinates'],
        scale=scale,
        crs='EPSG:32734',
        maxPixels=1e13)
    task.start()
    print(f"Export started (Asset): {asset_id}") 
    return

def exportTableToAsset(collection:ee.FeatureCollection,description:str,asset_id:str):
    """export FeatureCollection to GEE Asset"""
    if check_exists(asset_id) == 1:
        task = ee.batch.Export.table.toAsset(
            collection=collection,
            description=description,
            assetId=asset_id,
            )
        task.start()
        print(f'Export started (Asset): {asset_id}')
    else:
        print(f"{asset_id} already exists")
    
    return

def exportTableToDrive(collection:ee.FeatureCollection,description:str,folder:str,selectors:str):
    """export FeatureCollection to Google Drive"""
    task = ee.batch.Export.table.toDrive(
        collection=collection, 
        description=description, 
        folder=folder,
        fileNamePrefix=description,
        selectors=selectors)
    task.start()
    print(f'Export started (Drive): {folder}/{description}')
    return