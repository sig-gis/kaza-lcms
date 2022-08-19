# Running KAZA Regional Land Cover Monitoring System
# Setup Instructions
## Python Environment Setup
### 1. Install Anaconda 
* Go to the Anaconda distribution [page](https://www.anaconda.com/products/distribution), scroll to the bottom and find the Anaconda installer file for your Operating System. 
* Run the installer .exe and follow all recommendations in the installer. This [installation docs page](https://docs.anaconda.com/anaconda/install/) provides step-by-step guidance depending on your OS and use-case.
* When Anaconda asks you "Do you wish the installer to initialize Anaconda3?" Say Yes
### 2. Test your Anaconda Installation
* Open your command-prompt/shell/terminal and type `conda list`. You should see something like this.

![kaza_readme_condalist](https://user-images.githubusercontent.com/51868526/184011797-51781e24-396c-42a8-8ee8-d516e92fbb64.JPG)

* notice we're in the `base` environment by default, as indicated by the command-line. We want to operate from a custom python environment.
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
conda install -c conda-forge earthengine-api scikit-learn pandas
```
* Wait for package solver to finish and type y to proceed with installation.

## Git Setup
### 1. Download the Git installer for your OS from the Git downloads [page](https://git-scm.com/downloads). Run the installer following all recommended settings
### 2. Once installation is complete, open your command prompt/shell/terminal and type 
```
git --version
```

![kaza_gitVersion](https://user-images.githubusercontent.com/51868526/184142833-ae1dac16-6196-4aaf-a130-28e0e6707825.JPG)

### 3. Clone the kaza repository to a local folder 

```
git clone https://github.com/kyle-woodward/kaza-lc.git
```

![kaza_redme_gitClone](https://user-images.githubusercontent.com/51868526/184143024-31f4e6e0-0963-44bb-a72d-5b2778de5446.JPG)

### 4. `cd` into your new kaza-lc folder and `ls`(linux/MacOS) or `dir`(Windows) to see its contents

![kaza_readme_cdToKazalc](https://user-images.githubusercontent.com/51868526/184143297-bbcd50ee-20eb-4466-b438-2855b01e6585.JPG)

## Earth Engine Setup
### Earth Engine requires you to authenticate your account credentials to access the Earth Engine API and your chosen Cloud Project. We do this with the `gcloud` python utility
### 1. Download the installer for the `glcoud` command-line python [utility](https://cloud.google.com/sdk/docs/install) from Google
### 2. Run the installer
### 3. Select Single User and use the default Destination Folder
### 4. Leave the Selected Components to Install as-is and click Install
### 5. Leave all four boxes checked, and click Finish. This will open a new command-prompt window and auto run gcloud initialization
### 6. It asks whether yo'd like to log in, type y - this will open a new browser window to a Google Authentication page

![kaza_readme_gcloudInstaller_initializing](https://user-images.githubusercontent.com/51868526/184163126-7505745b-f7c3-4745-bb36-3948d1b9ff76.JPG)

### 7. Choose your Google account that is linked to your Earth Engine account, then click Allow on the next page.

![kaza_readme_gcloudInstaller_InitializingSignIn](https://user-images.githubusercontent.com/51868526/184163514-4604ac83-cdad-4dd8-bc67-c37224d6aafc.JPG)

### 8. You will be redirected to a page that says "You are now authenticated with the gcloud CLI!"
### 9. Go back to your shell that had been opened for you by gcloud. It asks you to choose a cloud project and lists all available cloud projects that your google account has access to. Look for `wwf-sig` and then type the number it is listed as to set your project. 

![kaza_readme_gcloudInstaller_chooseCloudProject_chooseWWF-SIG](https://user-images.githubusercontent.com/51868526/184165192-c602f058-b485-419c-b5ea-401c7087fb9f.JPG)

### 10. Back in your separate shell window, first ensure you are in your custom conda env (running `conda activate env-name`), then run:
```
earthengine authenticate
```
### 11. In the browser window that opens, select the Google account that is tied to your EE account, select the wwf-sig cloud project, then click Generate Token at the bottom of the page.
### 12. On the next page, select your Google account again, then click Allow on the next page.
### 13. Copy the authorization token it generates to your clipboard and back in your shell, paste it and hit Enter. 

# Testing Your Setup
### Test that earthengine is setup and authenticated by checking the folder contents within the `wwf-sig` cloud project. 
### * In your shell, run:
```
earthengine ls projects/wwf-sig/assets/kaza-lc
```

![kaza_earthenginels](https://user-images.githubusercontent.com/51868526/184402268-5876a8eb-7e1d-4d1f-aef6-658c6e20fe8c.JPG)

If you do not get an error and it returns a list of folders and assets similar to this then you are good to go! :tada:

# Project Workflow
### The following workflow is executed for each region in KAZA (script name in parenthesis if applicable):
### 1. Generate and interpret land cover reference samples for training and testing data using Collect Earth Online (01sample_pts.py)
### 2. Generate input data stack from chosen sensor used by the model (02sentinel2_sr.py **currently only using Sentinel data)
### 3. Create land cover primitives (03RFprimitives.py)
### 4. Construct categorical land cover map from the set of land cover primitives (04generate_LC.py)
### 5. Conduct accuracy assessment (05accuracy.py)
### 6. Estimate area of each land cover class (code editor JS script: users/kwoodward/kazaLC/pixelCounter & Area Estimation Google Sheets in Google Drive)

click this link to accept the kazaLC Javascript repo: https://code.earthengine.google.com/?accept_repo=users/kwoodward/kazaLC

click this link to gain access to the WWF_KAZA Google Drive folder: https://drive.google.com/drive/folders/1Qd3Xo9ISQjQV15xxwqfgE-Dr1JFJ49M4?usp=sharing

# Python Scripts
### Each script will be run on the command-line. The user must provide values for each command-line argument to control the year, AOI, and sensor to run the analysis with. The output Earth Engine asset from a given script must complete before the next script is run.
### Back in your terminal window, first ensure you have changed into your `kaza-lc` directory (`cd path/to/kaza-lc`) where the scripts are located
## 1. 01sample_pts.py 
### This script generates sample points to be used as training and testing for your given AOI. Currently you provide the year for which the points are to be used and it exports points for all AOIs as Earth Engine Feature Collection and as a CSV file to a Google Drive folder. 
### **Note 08/19/22: This script can be effectively skipped for the testing phase since we have already exported sample points as an Earth Engine asset for testing. This script will likely change as we decide on the best way to conduct point interpretation in CEO, finalize Land Cover typologies, and decide the best way to re-import those sample point datasets to Earth Engine.**


### * Run the script with python, choosing values for its required arguments
### example:
```
python 01sample_pts.py -p wwf-sig -y 2021
```
Tip: First run the script (and all the others) only declaring the `-h` flag, which will bring up the help dialog with a usage example and a description of required command-line arguments. 

![01sample_pts_output](https://user-images.githubusercontent.com/51868526/185672231-41b25bfc-8b0c-4339-aeb2-4c7e51b7e0ce.PNG)

## 2. 02sentinel2_sr.py
### This script creates a data stack of input covariates to feed into the land cover models. It executes this process for one AOI and year that the user specifies.
### * Run the script with python, choosing values for its required arguments
### example:
```
python 02sentinel2sr.py -p wwf-sig -a Mufunta -y 2021
```

![02sentinel_outputs](https://user-images.githubusercontent.com/51868526/185678779-d9a2dc2e-604d-42c8-a223-fd684e85359a.PNG)

### * The script reports that it is exporting a new dataset to the Earth Engine project. You can monitor submitted Earth Engine tasks in the [code editor](https://code.earthengine.google.com/) and clicking on Tasks tab in top-right

![script2_EEtaskRunning](https://user-images.githubusercontent.com/51868526/185678769-e91f6434-23ee-4fea-bcfb-f16eb409f65f.PNG)

### * Once the export task has completed, confirm that the new dataset exists. In the [code editor](https://code.earthengine.google.com/), go to Assets tab on top-left and navigate to the `wwf-sig` cloud project folder. Find the dataset at the path that was reported in the previous script.

![input_stack_exists_in_folder](https://user-images.githubusercontent.com/51868526/185693779-cf06d1d2-2a72-41d6-a8c8-1f8847118363.PNG)

## 3. 03RFprimitives.py 
### This script trains probability Random Forest models for each land cover class in your typology and exports them one at a time into a land cover 'Primitives' collection. While doing so, it also reports out some model performance metrics saved to a new folder created in your *local* `kaza-lc` folder on your computer.
### * Run the script with python, choosing values for its required arguments
### example:
```
python 03RFprimitives.py -p wwf-sig -a Mufunta -y 2021 -s S2
```
### Important: the argument values must be the same as before. Each script outputs the input for the next script.

![Rfprims_CLIoutput](https://user-images.githubusercontent.com/51868526/185696652-2ebb3e7f-0408-42c4-9b20-0e1d474d5467.PNG)

### * Once the script completes, check several things:
#### 1. Check that the exports have been submitted by looking at the Tasks tab in the [code editor](https://code.earthengine.google.com/)
![RFprims_tasklist](https://user-images.githubusercontent.com/51868526/185696700-f3ce7aed-45b8-4fc5-bb84-0141846d0f21.PNG)
#### 2. Go into your local `kaza-lc` folder on your computer, check that a new folder named `metrics_[sensorID]_[AOI]_[year]` was created
#### 3. Investigate the metric files located within. 
![metricsFolder_inside](https://user-images.githubusercontent.com/51868526/185681947-66457302-ff14-4c86-be9d-baa5f8b531db.PNG)

There is one oobError .txt file and one varImportance .csv file per land cover. The oobError .txt files contain the Out-of-Bag Error estimate for that land cover's Random Forest model. The varImportance .csv files report out the relative importance of each input feature (covariate) in the input data stack.

## 4. 04generateLC.py
### This script takes the RF primitives collection generated from the previous script and creates a single-band land cover image from them.
### * Run the script with python, choosing values for its required arguments
### example:
```
python 04generateLC.py -p wwf-sig -a Mufunta -y 2021 -s S2
```
![04generate_LC_CLIoutputs](https://user-images.githubusercontent.com/51868526/185698346-cd12d4bb-0f6d-4557-bb2d-e45922968a83.PNG)

### * Like you've done previously, check that the export task has been submitted in the [code editor](https://code.earthengine.google.com/), and when the task completes, check that the new output file exists in the Assets tab. 

## 5. 05accuracy.py 
### This script generates useful accuracy assessment metrics for your chosen land cover image, exporting them to the `kaza-lc\metrics...` folder on your local computer 
### * Run the script with python, choosing values for its required arguments
### example:
```
python 05accuracy.py -p wwf-sig -a Mufunta -y 2021 -s S2
```
![05accuracy_CLIoutput](https://user-images.githubusercontent.com/51868526/185699762-a57a05a3-a5ce-4f4e-a6c2-4cc536b5da4c.PNG)

### * Investigate the metrics files in the designated metrics folder
![metricsFolder_afterAccuracy](https://user-images.githubusercontent.com/51868526/185699976-61c2c8b4-d24c-4ea9-a504-c0dbaf4e779e.PNG)

The new files are confMatrix.jpg, confMatrix.csv, classAccuracy.csv, overallAccuracy.txt

# Inspecting Land Cover Outputs
### In addition to digging into the files in your metrics folders, you should also look at the output land cover image to gain insight into how the land cover models are performing
### * In the [code editor](https://code.earthengine.google.com/), in the Scripts tab top-left, find the code repository named 'users/kwoodward/inspectingLCOutputs' and open it. Edit it as necessary to display the land cover products you would like to look at and click Run.
![inspectingLCOutputs](https://user-images.githubusercontent.com/51868526/185697784-415a4367-f52b-48d1-8647-cf6fad81644f.PNG)
![insepctingLCoutputs](https://user-images.githubusercontent.com/51868526/185688973-483f3d81-df16-4613-93bf-7a89fe839b42.PNG)

You can zoom in, and change the transparency of layers in the Layers widget in the top-right of the Map window.

# Area Estimation (last step, not Python)
### Once you have completed steps 1-5 for a given region and have a final Land Cover ee.Image in your Earth Engine folder, you are ready to estimate Land Cover area from that image.
### 1. Open the Earth Engine [code editor](https://code.earthengine.google.com/)
### 2. In the Scripts tab at the top-left find the script named 'users/kwoodward/kazaLC/pixelCounter' and open it.

![kaza_readme_pixelCounter](https://user-images.githubusercontent.com/51868526/185140333-9d98daaa-f635-4eb0-a712-7d0d53a49cd1.JPG)
This script takes an Earth Engine path to a Land Cover image and exports the amount of pixels in each Land Cover class as a CSV file to the WWF_KAZA Google Drive folder
### 3. On Line 1 of the script, change the `img_path` string to the path of your chosen land cover image and Click Run at the top

![kaza_readme_pixelCounter_Run](https://user-images.githubusercontent.com/51868526/185140532-ba6b7a70-bc1b-4a23-8815-f7fdaa872153.JPG)

### 4. The Tasks tab is now highlighted orange meaning there is a new export task waiting for you to confirm. Click the Tasks tab and you'll see one new task item under 'Unsubmitted Tasks'. Click Run.

### 5. A new window pops up showing the export details. All should be left as default. Click Run again and the task will be sent to the Task queue with a spinning Earth Engine logo indicating it has been submitted. 

![kaza_readme_pixelCounter_RunExport](https://user-images.githubusercontent.com/51868526/185143746-9ac8d4a1-7f99-4e2f-94ec-330d1165243e.JPG)

### 6. While you are waiting for the export to complete (should take less than 10 mins), go into the WWF_KAZA GDrive folder again, find the Area Estimation Google Sheet for your Region and open it.

![AreaEstimationPasteTotalPixelCount](https://user-images.githubusercontent.com/51868526/185145031-ffe8c332-8287-4f06-bfd1-0f2cb395ede4.JPG)

This spreadsheet computes Area Estimation of each Land Cover class within your land cover image with a 95% confidence interval. The cells that you want to update are highlighted in yellow. We need to update the Pixel Counts as well as the entire Confusion Matrix, which we will do using the pixelCount export you just exported as well as the Confusion Matrix CSV that the 05accuracy.py script exported to your local computer.

### 7. Once the pixelCounter export completes, go to the WWF_KAZA Google Drive folder and find the new .csv file called 'countsReadable_[name of land cover image].csv'. Open it with Google Sheets and Copy the counts column values.

![countsReadableCopy](https://user-images.githubusercontent.com/51868526/185142449-1431a1b0-7129-44e3-8822-2e099f3c785d.JPG)

### 8. Paste the values in the Total Pixel Count column off to the right (highlighted in yellow) in the Area Estimation google sheet.

### 9. Similarly open the local kaza-lc folder on your computer and find the 'metrics..' folder for your land cover image, and copy the entire grid of cells in that CSV file and paste it in the Confusion Matrix to update those values.

![openConfMatrixCSV](https://user-images.githubusercontent.com/51868526/185145782-70a1914b-bfd9-44f5-80fc-c66b15156d78.JPG)

### 10. As long as there are no #ERROR values in any of the cells (try Paste Special->Values if so), you are good to go! 🎉
