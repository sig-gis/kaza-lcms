import ee
"""
Generate stratified random training points for each AOI
Currently uses EOSS 2020 LC product as stratification but can adapt for making points to be interpreted in CEO
"""
def sample_points(img,aoi,year):
    aoi_s = ee.String(ee.FeatureCollection(aoi).get('system:id')).split('/').get(-1)
    samples=ee.Image(img).stratifiedSample(
    2000,
    'LC',
    ee.FeatureCollection(aoi).first().geometry(),
    10,
    None,
    5151,
    [1,2,3,4,5,6,7,8],
    [2000,2000,2000,2000,2000,2000,2000,2000],
    True,
    4,
    True).map(lambda f: f.set('year',year,'aoi',aoi_s))
    return samples

def export_points(pts,year):
    aoi_s = ee.FeatureCollection(pts).first().get('aoi').getInfo()
    outpath = f'projects/sig-ee/WWF_KAZA_LC/trainingPts/{aoi_s}_{year}'
    desc = outpath.replace('/','_')
    task = ee.batch.Export.table.toAsset(pts,desc,outpath)
    task.start()
    print(f"Export Training Pts: {outpath}")


if __name__ == "__main__":
    ee.Initialize()
    year=2021
    list_aois = [ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/Hwange"),
                     ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/Mufunta"),
                     ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/Mulobesi"),
                     ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/SNMC"),
                     ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/Sichifulo"),
                     ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/aoi/Zambezi")]
                     # Bengo need to add, havent imported to EE yet
    
    # **using collapsed EOSS LC product temporarily for stratified sampling,can random sample from aoi boundaries in future?**

    # legend can be looked at here https:docs.google.com/document/d/12K4MqsAeq2bmCx3XyOMZefx6yBAkQv3lg_FA8NIxoow/edit?usp=sharing
    # aggregate LC2020 sub-classes together to make training points
    # OpenHerbaceous 31,32>>1
    # Cropland 40>>2
    # Built-up 50>>3
    # BareArea 60,61>>4
    # Water 80,81>>5
    # Wetland 90,91,92>>6
    # Forest/Woodland 110,120,210>>7
    # Bushland/Shrubs 130,222,231,232>>8

    LC2020 = ee.Image("projects/sig-ee/WWF_KAZA_LC/Land_Cover_KAZA_2020_TFCA")

    LC2020_collapsed=LC2020.remap([31,32,40,50,60,61,80,81,90,91,92,110,120,130,210,222,231,232],
                                [1,1,2,3,4,4,5,5,6,6,6,7,7,8,7,8,8,8]).rename('LC')

    for aoi in list_aois:
        
        pts = sample_points(LC2020_collapsed,aoi,year)
        export_points(pts,year)
        print(pts.aggregate_histogram('LC').getInfo())
        
        