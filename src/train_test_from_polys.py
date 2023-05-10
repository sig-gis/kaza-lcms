import argparse
import os
from src.utils.check_exists import check_exists
from src.utils.sampling import strat_sample_no_extraction
import ee
ee.Initialize(project='wwf-sig')

# params
polys = ee.FeatureCollection("projects/wwf-sig/assets/kaza-lc/sample_pts/zambezi_polygons")
class_band='LANDCOVER'
s=902550
scale=10
n_points = 1000
class_values = [1,2,3,4,5,6,7,8]
class_points_stratified = [1500,500,500,1500,1500,500,500,1500]

train,test = strat_sample_no_extraction(
                           collection=polys,
                           class_band=class_band,
                           scale=scale,
                           seed=s,
                           class_values=class_values,
                           class_points=class_points_stratified,
                           split=True)

pts = strat_sample_no_extraction(
                           collection=polys,
                           class_band=class_band,
                           scale=scale,
                           seed=s,
                           class_values=class_values,
                           class_points=class_points_stratified,
                           )

# print(pts.limit(10,'random',False).getInfo())
print('all pts')
print(pts.aggregate_histogram(class_band).getInfo())
print('\n')
print('train/test')
print(train.aggregate_histogram(class_band).getInfo())
print(test.aggregate_histogram(class_band).getInfo())
