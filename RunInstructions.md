# Running KAZA Regional Land Cover Monitoring System

# Python Environment Setup
### 1. Install Anaconda 
* Go to the Anaconda distribution [page](https://www.anaconda.com/products/distribution), scroll to the bottom and find the Anaconda installer file for your Operating System. 
* Run the installer .exe and follow all recommendations in the installer. This [installation docs page](https://docs.anaconda.com/anaconda/install/) provides step-by-step guidance depending on your OS and use-case.
* When Anaconda asks you "Do you wish the installer to initialize Anaconda3?" Say Yes
### 2. Test your Anaconda Installation
* Open your command-prompt/shell/terminal and type `conda list`. You should see something like this.

![kaza_readme_condalist](https://user-images.githubusercontent.com/51868526/184011797-51781e24-396c-42a8-8ee8-d516e92fbb64.JPG)

* Scroll the list of installed packages that came shipped with anaconda (notice we're in the `base` environment by default, as indicated by the command-line). We almost have every package we need already.
### 3. Create a custom virtual environment
Keep your shell open and paste each one of these commands.
* Create a new conda env named 'gee'
```
conda create -n gee 
```
* Activate your new 'gee' env
```
conda activate gee
```
* In your shell, run this code block:
```
conda install -c conda-forge earthengine-api
conda install -c conda-forge scikit-learn
```
# Earth Engine Setup






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

