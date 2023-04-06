import ee
ee.Initialize(project='wwf-sig')

def exportImgToAsset(img,desc,asset_id,region,scale):
    export_region = region
    task = ee.batch.Export.image.toAsset(
        image=ee.Image(img),
        description=desc,
        assetId=asset_id,
        region=export_region.getInfo()['coordinates'],
        maxPixels=1e13,
        scale=scale)
    task.start()
    print(f"export started: {asset_id}") 
    return