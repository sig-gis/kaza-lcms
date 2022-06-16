import ee
from time import sleep

import math
import numpy as np
import random
from numpy.random import seed
from numpy.random import rand
import sys

ee.Initialize()


seed(1044)
values = rand(15000)
valInt = np.random.randint(10000, size=10000)


def main ():

    week = 1#int(sys.argv[1])
    print('week ',week)

    featureNames = ['VH','VV','ratio']
    RESPONSE = ['water']
    FEATURES = featureNames + RESPONSE
    
    # Get the projection that is needed for the study area
    projection = ee.Projection('EPSG:4326')
    
    # Load in the GLAD Alert Images
    #geom = ee.FeatureCollection("projects/servir-mekong/admin/eo_Mekong_River_Basin_MRC").geometry().buffer(5000)
    # import country layers
    #countries = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017");
    # select Cambodia
    #geom = countries.filter(ee.Filter.eq("country_na", "Burma")).geometry().buffer(5000);
    geom = ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/SNMC").geometry().buffer(5000)
    
    #MODE = 'DESCENDING'
    # Import Sentinel-1 Collection 
    s1 =  ee.ImageCollection('COPERNICUS/S1_GRD')\
			.filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))\
			.filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))\
			.filter(ee.Filter.eq('instrumentMode', 'IW'))
			#//.filter(ee.Filter.eq('orbitProperties_pass', MODE))
    
    
    start = ee.Date.fromYMD(2021,1,4).advance(week,"week")
    end = start.advance(2,"week")

    s1img = s1.filterBounds(geom)\
	      .filterDate(start,end)\
	      .map(terrainCorrection)\
	      .map(applySpeckleFilter)\
	      .map(addRatio)\
	      .map(erodeGeometry)
	    
	    
    output = ee.Image(s1img.mean()).select(['VH','VV']).multiply(10000).toInt().clip(geom)
    output = output.set("system:time_start",start)
    outputName = "projects/sig-ee/WWF_KAZA_LC/sentinel1_2021_"+str(week).zfill(2) + "_"+str(week+2).zfill(2) 
    geom =  ee.FeatureCollection("projects/sig-ee/WWF_KAZA_LC/SNMC").geometry().bounds().getInfo()
    print(geom['coordinates'])
    
    task_ordered = ee.batch.Export.image.toAsset(image=output, description="sentinel1 ", assetId=outputName,region=geom['coordinates'], maxPixels=1e13,scale=10 )
    task_ordered.start()
    
    
    
# Produces a kernel of a given sized fro sampling in GEE
def get_kernel (kernel_size):
    eelist = ee.List.repeat(1, kernel_size)
    lists = ee.List.repeat(eelist, kernel_size)
    kernel = ee.Kernel.fixed(kernel_size, kernel_size, lists)
    return kernel			
			
			
# Implementation by Andreas Vollrath (ESA), inspired by Johannes Reiche (Wageningen)
def terrainCorrection(image):
    date = ee.Date(image.get('system:time_start'))
    imgGeom = image.geometry()
    srtm = ee.Image('USGS/SRTMGL1_003').clip(imgGeom)  # 30m srtm 
    sigma0Pow = ee.Image.constant(10).pow(image.divide(10.0))

    #Article ( numbers relate to chapters) 
    #2.1.1 Radar geometry 
    theta_i = image.select('angle')
    phi_i = ee.Terrain.aspect(theta_i).reduceRegion(ee.Reducer.mean(), theta_i.get('system:footprint'), 1000).get('aspect')

    #2.1.2 Terrain geometry
    alpha_s = ee.Terrain.slope(srtm).select('slope')
    phi_s = ee.Terrain.aspect(srtm).select('aspect')

    # 2.1.3 Model geometry
    # reduce to 3 angle
    phi_r = ee.Image.constant(phi_i).subtract(phi_s)

    #convert all to radians
    phi_rRad = phi_r.multiply(math.pi / 180)
    alpha_sRad = alpha_s.multiply(math.pi / 180)
    theta_iRad = theta_i.multiply(math.pi / 180)
    ninetyRad = ee.Image.constant(90).multiply(math.pi / 180)

    # slope steepness in range (eq. 2)
    alpha_r = (alpha_sRad.tan().multiply(phi_rRad.cos())).atan()

    # slope steepness in azimuth (eq 3)
    alpha_az = (alpha_sRad.tan().multiply(phi_rRad.sin())).atan()

    # local incidence angle (eq. 4)
    theta_lia = (alpha_az.cos().multiply((theta_iRad.subtract(alpha_r)).cos())).acos()
    theta_liaDeg = theta_lia.multiply(180 / math.pi)
  
    # 2.2 
    # Gamma_nought_flat
    gamma0 = sigma0Pow.divide(theta_iRad.cos())
    gamma0dB = ee.Image.constant(10).multiply(gamma0.log10())
    ratio_1 = gamma0dB.select('VV').subtract(gamma0dB.select('VH'))

    # Volumetric Model
    nominator = (ninetyRad.subtract(theta_iRad).add(alpha_r)).tan()
    denominator = (ninetyRad.subtract(theta_iRad)).tan()
    volModel = (nominator.divide(denominator)).abs()

    # apply model
    gamma0_Volume = gamma0.divide(volModel)
    gamma0_VolumeDB = ee.Image.constant(10).multiply(gamma0_Volume.log10())

    # we add a layover/shadow maskto the original implmentation
    # layover, where slope > radar viewing angle 
    alpha_rDeg = alpha_r.multiply(180 / math.pi)
    layover = alpha_rDeg.lt(theta_i);

    # shadow where LIA > 90
    shadow = theta_liaDeg.lt(85)

    # calculate the ratio for RGB vis
    ratio = gamma0_VolumeDB.select('VV').subtract(gamma0_VolumeDB.select('VH'))

    output = gamma0_VolumeDB.addBands(ratio).addBands(alpha_r).addBands(phi_s).addBands(theta_iRad)\
			    .addBands(layover).addBands(shadow).addBands(gamma0dB).addBands(ratio_1)

    return output.select(['VV', 'VH'], ['VV', 'VH']).set("system:time_start",date).clip(imgGeom ).copyProperties(image)


#
# * Clips 5km edges
# */
def erodeGeometry(image):
    return image.clip(image.geometry().buffer(-5))

def clipEdge(image):
    return image.clip(image.geometry().buffer(-5))


def applySpeckleFilter(img):
    
    vv = img.select('VV')
    vh = img.select('VH')
    vv = speckleFilter(vv).rename('VV');
    vh = speckleFilter(vh).rename('VH');
    return ee.Image(ee.Image.cat(vv,vh).copyProperties(img,['system:time_start'])).clip(img.geometry()).copyProperties(img);


def speckleFilter(image):
    """ apply the speckle filter """
    ksize = 3
    enl = 7; 
    
    geom = image.geometry()
    
    # Convert image from dB to natural values
    nat_img = toNatural(image);

    # Square kernel, ksize should be odd (typically 3, 5 or 7)
    weights = ee.List.repeat(ee.List.repeat(1,ksize),ksize);

    # ~~(ksize/2) does integer division in JavaScript
    kernel = ee.Kernel.fixed(ksize,ksize, weights, int(ksize/2), int(ksize/2), False); # changed to python int division

    # Get mean and variance
    mean = nat_img.reduceNeighborhood(ee.Reducer.mean(), kernel);
    variance = nat_img.reduceNeighborhood(ee.Reducer.variance(), kernel);

    # "Pure speckle" threshold
    ci = variance.sqrt().divide(mean);# square root of inverse of enl

    # If ci <= cu, the kernel lies in a "pure speckle" area -> return simple mean
    cu = 1.0/math.sqrt(enl);

    # If cu < ci < cmax the kernel lies in the low textured speckle area
    # -> return the filtered value
    cmax = math.sqrt(2.0) * cu;

    alpha = ee.Image(1.0 + cu*cu).divide(ci.multiply(ci).subtract(cu*cu));
    b = alpha.subtract(enl + 1.0);
    d = mean.multiply(mean).multiply(b).multiply(b).add(alpha.multiply(mean).multiply(nat_img).multiply(4.0*enl));
    f = b.multiply(mean).add(d.sqrt()).divide(alpha.multiply(2.0));

    # If ci > cmax do not filter at all (i.e. we don't do anything, other then masking)
    # Compose a 3 band image with the mean filtered "pure speckle", 
    # the "low textured" filtered and the unfiltered portions
    out = ee.Image.cat(toDB(mean.updateMask(ci.lte(cu))),toDB(f.updateMask(ci.gt(cu)).updateMask(ci.lt(cmax))),image.updateMask(ci.gte(cmax)));	
		
    return out.reduce(ee.Reducer.sum()).clip(geom);

def addRatio(img):
    geom = img.geometry()
    vv = toNatural(img.select(['VV'])).rename(['VV']);
    vh = toNatural(img.select(['VH'])).rename(['VH']);
    ratio = vh.divide(vv).rename(['ratio']);
    return ee.Image(ee.Image.cat(vv,vh,ratio).copyProperties(img,['system:time_start'])).clip(geom).copyProperties(img);


def toNatural(img):
    """Function to convert from dB to natural"""
    return ee.Image(10.0).pow(img.select(0).divide(10.0));
		
def toDB(img):
    """ Function to convert from natural to dB """
    return ee.Image(img).log10().multiply(10.0);

if __name__ == "__main__":
    print('Program started..')
    main()
    print('\nProgram completed.')

