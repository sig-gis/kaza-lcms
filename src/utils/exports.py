import ee
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
    print(f"export started: {asset_id}") 
    return