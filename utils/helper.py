import ee
ee.Initialize()

def check_exsits(ee_path:str):
    try:
        ee.data.getAsset(ee_path)
        return 0
    except ee.ee_exception.EEException:
        return 1
