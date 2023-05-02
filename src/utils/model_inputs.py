#%%
model_inputs = {
# refer to spectral index function names (self.functionList) in utils/covariates.py
'indices': ["ND_blue_green","ND_blue_red","ND_blue_nir","ND_blue_swir1","ND_blue_swir2",
			"ND_green_red","ND_green_nir","ND_green_swir1","ND_green_swir2",
            "ND_red_swir1","ND_red_swir2",
            "ND_nir_red","ND_nir_swir1","ND_nir_swir2",
            "ND_swir1_swir2","R_swir1_nir","R_red_swir1","EVI","SAVI","IBI"],
    
# include Tasseled Cap indices
# (wetness, brightness, greenness)
'addTasselCap':True,

# include JRC-derived water variables 
# (occurrence, change_abs, change_norm, seasonality, transition, max_extent)
'addJRCWater': True,

# include topography variables 
# (elevation, slope, aspect, eastness, northness)
'addTopography':True,

# include intra-year harmonic coefficients
# (band_amplitude, band_phase)
'addHarmonics':True,

# specify band/index and Day of Year time period to compute time trend
'harmonicsOptions': {'swir1':
                     {'start':1, # in Julian Days (Day of Year)
                      'end':365}
}

}
#%%
# ho = model_inputs['harmonicsOptions']
# for k in ho:
#     print(ho[k]['start'])
    
# %%
