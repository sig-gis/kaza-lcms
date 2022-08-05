# Running KAZA Regional Land Cover Monitoring System

# Python Environment setup

### The only required python packages that do not ship with a python install is `earthengine-api` and `scikit-learn`. Use your preferred python environment manager to install each:
[earthengine-api](https://developers.google.com/earth-engine/guides/python_install)

[scikit-learn](https://scikit-learn.org/stable/install.html)

#
# Asset Management
### We will organize our Earth Engine assets (files) in an EE cloud project. We have AOIs, input stacks, output land cover product, and reference samples. We will have this basic structure setup already.

![kaza_readme_folderOrg](https://user-images.githubusercontent.com/51868526/183120715-58a6c92d-79fe-4345-9e26-c821978fa485.JPG)

# Workflow

## The following workflow is executed for each region in KAZA (script name in parenthesis if applicable):
### 1) Generate and interpret land cover reference samples for training and testing data using Collect Earth Online (01sample_pts.py)
### 2) Generate input data stack from chosen sensor used by the model (02sentinel2_sr.py **currently only using Sentinel data)
### 3) Create land cover primitives (03RFprimitives.py)
### 4) Construct categorical land cover map from the set of land cover primitives (04generate_LC.py)
### 5) Conduct accuracy assessment (05accuracy.py)
### 6) Estimate area of each land cover class
#
# Scripts

## Each script will be run on the command-line. The user must provide values for each command-line argument to control the year and AOI to run the analysis for, and which sensor to use. The output Earth Engine asset from a given script must complete before the next script is run.

## Here is a list of possible arguments a script will require:
* -p --project - name of your cloud project
* -a --aoi_s  - the AOI to run the analysis for
* -y --year  - year to run the analysis for
* -s --sensor  - one of "S2" or "planet", determines which sensor the input data is compiled from

## You can use the `-h` flag to retrieve the script's usage example.

![kaza_readme_cmdline](https://user-images.githubusercontent.com/51868526/183131644-4568f7b1-a58d-4a94-a66a-0e8def39f280.JPG)

## If the script reports that an Export task has been started, go to the Code Editor to check on its progress.

![kaza_readme_exportRunning](https://user-images.githubusercontent.com/51868526/183131558-c0433f1b-ad3d-49b8-9d4d-9533a16cd216.JPG)

