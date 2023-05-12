# Experimenting with automating different sampling allocation strategies..
# this one was for disproportional sampling by auto-calculating which classes
# were majority/minority class, given the total area of their reference polygons 
# against the total area of all polygons in the input_fc
import ee
ee.Initialize(project='wwf-sig')

# input_fc = ee.FeatureCollection("projects/wwf-sig/assets/kaza-lc/sample_pts/hwange_polygons")
input_fc = ee.FeatureCollection("projects/wwf-sig/assets/kaza-lc/sample_pts/zambezi_polygons")
# input_fc = ee.FeatureCollection("projects/wwf-sig/assets/kaza-lc/sample_pts/mufunta_polygons")

ref_label = 'LANDCOVER'
dct = input_fc.aggregate_histogram(ref_label) # polygons per class

keys = dct.keys()

# determine which classes are majority / minority given the polygon area totals

# print(with_area.first().getInfo()['properties'])
# test = with_area.filter(ee.Filter.eq('LANDCOVER',1))
# print(test.size().getInfo())
# take a land cover value and return sum of area for all features in that filtered result
def area_by_class(input_fc,group_property):
    with_area = input_fc.map(lambda f: f.set('area',f.area()))
    filter_vals = with_area.aggregate_array(group_property).distinct().sort()
    empty_dct = ee.Dictionary()
    def mapped_fnc(val):
        class_n = with_area.filter(ee.Filter.eq(group_property,val))
        val_key = ee.String(ee.Number.format(val)) # convert value to string to be a dict key
        area_sum = class_n.reduceColumns(ee.Reducer.sum(),['area']).rename(['sum'],[val_key])
        return empty_dct.combine(ee.Dictionary([val_key,area_sum.values()])) # we get a list of dictionaries, one dict per dict key..
    return filter_vals.map(mapped_fnc)

# need one dictionary..

area_by_class_test = area_by_class(input_fc, 'LANDCOVER')
print(area_by_class_test.getInfo())

k = area_by_class_test.map(lambda d: ee.Dictionary(d).keys()).flatten()
v = area_by_class_test.map(lambda d: ee.Dictionary(d).values()).flatten()
print(k.getInfo())
print(v.getInfo())

area_total = ee.List(v).reduce(ee.Reducer.sum())
print(area_total.getInfo())

props = v.map(lambda val: ee.Number(val).divide(area_total))
print(props.getInfo())

# this must be statistically based from the population of area proportions values of each class
props_mean = props.reduce(ee.Reducer.mean())
props_med = props.reduce(ee.Reducer.median())
print('mean',props_mean.getInfo())
print('median',props_med.getInfo())
maj_min = props.map(lambda p: ee.Number(p).gte(props_mean))
print('maj_min classification',maj_min.getInfo())

# if user provides multiplier for proportional or disproportional allocation,
# prop allocation just multiplies ..
# although prop allocation of polygon didn't calc area so we need to revisit that function?
# but for disprop allocation, we can use an equal allocation list then multiply it by the (multiplier*proportion)
class_values = [1,2,3,4,5,6,7,8]
class_points = [200,200,200,200,200,200,200,200]
n_multiplier = 10
n_points = 500

# i think for now we just let the user change the class values and class points parameters at command-line..? 
# automatically computing these things may be not worth the hassle, and if anything maybe the tools should just guide the 
# user to make a good sampling allocation they make up..








def maj_min():
    area_by_class_test = area_by_class(input_fc,'LANDCOVER')
    total_area = area_by_class_test.values().sum()
    return total_area
# maj_min_test = maj_min()
# print(maj_min_test.getInfo())