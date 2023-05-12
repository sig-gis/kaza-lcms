# CHOOSE YOUR INPUT FEATURES 
# note: spectral bands [blue,green,red,nir,swir1,swir2] are included by default
model_inputs = {

### SPECTRAL INDICES ###
# refer to spectral index function names (self.functionList) in utils/covariates.py
'indices': ["EVI","SAVI","IBI"],
  
# include Tasseled Cap Indices?
# will add these variables: 
#   wetness, brightness, greenness, 
#   fourth, fifth, sixth, 
#   TCAngleBG, tcAngleGW, tcAngleBW,
#   tcDistBG, tcDistGW, tcDistBW
'addTasselCap':False,
########################

### ANCILLARY VARIABLES ###
# Include JRC Water Variables? 
# will add these variables: 
#   occurrence, change_abs, change_norm, seasonality, transition, max_extent
'addJRCWater': False,

# Include Topography Variables?
# will add these variables: 
#   elevation, slope, aspect, eastness, northness
'addTopography':True,
############################

### TIME SERIES FEATURES ###
# Which Statisitcal Percentile Composites to Generate from Time Series?
'percentileOptions': [10,25,50,75,90],

# Fit Harmonic Trend to Time Series?
# will add these variables per band specified in harmonicsOptions: 
#   amplitude, phase
'addHarmonics':True,

# specify band/index and Day of Year time period to fit time trend
'harmonicsOptions': {'nir':
                     {'start':1, # in Julian Days (Day of Year)
                      'end':365}, 
                      
                      'swir1':
                      {'start':1, # in Julian Days (Day of Year)
                      'end':365}, 
                    }
}