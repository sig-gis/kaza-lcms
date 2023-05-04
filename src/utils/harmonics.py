# harmonics.py
import ee
import math
from src.utils.model_inputs import model_inputs

ee.Initialize(project='wwf-sig')


def addHarmonicTerms(image):
    timeRadians = image.select("t").multiply(2 * math.pi)
    return image.addBands(timeRadians.cos().rename("cos")).addBands(
        timeRadians.sin().rename("sin")
    )


def calculateHarmonic(imageCollection: ee.ImageCollection, dependent: ee.String):
    harmonicIndependents = ee.List(["constant", "t", "cos", "sin"])
    #  Add harmonic terms as new image bands.
    harmonicLandsat = imageCollection.map(addHarmonicTerms)
    # The output of the regression reduction is a 4x1 array image.
    harmonicTrend = harmonicLandsat.select(harmonicIndependents.add(dependent)).reduce(
        ee.Reducer.linearRegression(harmonicIndependents.length(), 1)
    )

    # Turn the array image into a multi-band image of coefficients.
    harmonicTrendCoefficients = (
        harmonicTrend.select("coefficients")
        .arrayProject([0])
        .arrayFlatten([harmonicIndependents])
    )

    # // Compute phase and amplitude.
    phase = (
        harmonicTrendCoefficients.select("cos")
        .atan2(harmonicTrendCoefficients.select("sin"))
        .rename(dependent.cat("_phase"))
    )

    amplitude = (
        harmonicTrendCoefficients.select("cos")
        .hypot(harmonicTrendCoefficients.select("sin"))
        .rename(dependent.cat("_amplitude"))
    )
    return ee.Image.cat(phase, amplitude)


def harmonicRGB(harmonics: ee.Image):
    # // Use the HSV to RGB transform to display phase and amplitude
    amplitude = harmonics.select(".*amplitude")
    phase = harmonics.select(".*phase")

    rgb = (
        phase.unitScale(-math.pi, math.pi)
        .addBands(amplitude.multiply(2.5))
        .addBands(ee.Image(1))
        .hsvToRgb()
    )
    return rgb


def addTimeConstant(imageCollection: ee.ImageCollection, timeField: str):
    def _(image, timeField):
        # // Compute time in fractional years since the epoch.
        date = ee.Date(image.get(timeField))
        years = date.difference(ee.Date("1970-01-01"), "year")
        # // Return the image with the added bands.
        return image.addBands(ee.Image(years).rename("t").float()).addBands(
            ee.Image.constant(1)
        )

    return imageCollection.map(lambda i: _(i, timeField))

def doHarmonicsFromOptions(imgColl:ee.ImageCollection):
    imgColl = ee.ImageCollection(imgColl)

    # construct EE dict from model_inputs python dict
    eedict = ee.Dictionary(model_inputs)
    
    # get harmonicsOptions dictionary
    harmonicsOptions = eedict.get('harmonicsOptions')
    
    # get band keys as list
    bands = ee.Dictionary(harmonicsOptions).keys()
    
    def harmonicByBand(band):
        band = ee.String(band)
        # get the params for that band
        bandwiseParams = ee.Dictionary(harmonicsOptions).get(band)
        
        # get the start and end DOY parameters
        start = ee.Dictionary(bandwiseParams).get('start')
        end = ee.Dictionary(bandwiseParams).get('end')
        
        # create temporal filtered imgColl for that band
        imgCollByBand = (ee.ImageCollection(imgColl)
                            .select(band)
                            .filter(ee.Filter.dayOfYear(start,end)))
        # add time bands
        timeField = "system:time_start"
        timeCollection = addTimeConstant(imgCollByBand, timeField)
        
        return ee.Image(calculateHarmonic(timeCollection,band))
    
    # do harmonics by band key in model_inputs dictionary
    listOfImages = ee.Image.cat(ee.List(bands).map(harmonicByBand))
    bandStack = ee.Image(ee.ImageCollection.fromImages(listOfImages).toBands())
    
    # to remove srcImg band name indexing resulting from .toBands() 
    # (i.e. [0_swir1_phase, 0_swir1_amplitude] -> [swir1_phase, swir1_amplitude] )
    bandNames = bandStack.bandNames()
    fixedBandNames = bandNames.map(lambda e: ee.String(e).split("_").slice(-2).join("_"))
    return bandStack.rename(fixedBandNames)

if __name__ == "__main__":
    # inputs
    roi = ee.Geometry.Point([22.5019, -17.9789])
    imageCollection = ee.ImageCollection("COPERNICUS/S2_SR")
    timeField = "system:time_start"
    dependent = ee.String("B8")

    # Napkin tests...
    # prep image collection for test
    filteredCollection = imageCollection.filterBounds(roi).filterDate(
        "2019-01-01", "2021-01-01"
    )

    # test add time bands
    timeCollection = addTimeConstant(filteredCollection, timeField)

    assert timeCollection.select("t", "constant").first().bandNames().getInfo() == [
        "t",
        "constant",
    ]

    harmonics = calculateHarmonic(timeCollection, dependent)
    # test harmonics returns correect bands
    assert (
        harmonics.bandNames().getInfo()
        == ee.List([dependent.cat("_phase"), dependent.cat("_amplitude")]).getInfo()
    )

    rgb = harmonicRGB(harmonics)
    # test rgb returns correct bands
    eetest = ee.Algorithms.IsEqual(rgb.bandNames(), ["red", "green", "blue"]).getInfo()
    assert eetest is True

    harmonicsByOptions = doHarmonicsFromOptions(imageCollection)
    optionBands = 'swir1'
    assert (harmonicsByOptions.bandNames().getInfo() 
            == ee.List([optionBands.cat("_phase"), optionBands.cat("_amplitude")]).getInfo()
            ) 