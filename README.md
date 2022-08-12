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
conda install -c conda-forge earthengine-api
conda install -c conda-forge scikit-learn
```

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
## Option 1 - Authenticate without installing `gcloud` utility
### 1. In your shell, run:
```
earthengine authenticate --auth_mode notebook
```
### 2. In the browser window that opens, select the Google account that is tied to your EE account, select the wwf-sig cloud project, then click Generate Token at the bottom of the page.

![kaza_readme_notebookauthenticator](https://user-images.githubusercontent.com/51868526/184396026-be2dc257-eeb5-442c-9e76-e06cb0445db0.JPG)

### 3. On the next page, select your Google account again, then click Allow on the next page.
### 4. Copy the authorization token it generates to your clipboard and back in your shell, paste it and hit Enter.

![kaza_readme_commandline_pasteAuthToken](https://user-images.githubusercontent.com/51868526/184396045-e8c81cfd-5b55-4567-8d52-5abe4fcbf4f5.JPG)

### Option 2 - Authenticate with `gcloud` utility
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

### Authenticate to Earth Engine
### 1. Back in your separate shell window, first ensure you are in your custom conda env (`conda activate env-name`) and run:
```
earthengine authenticate
```
### 2. If you are running this from your local computer (not a virtual machine), it should automatically open a new tab in your browser to a Google Authentication page 
 
# Project Workflow
### The following workflow is executed for each region in KAZA (script name in parenthesis if applicable):
1. Generate and interpret land cover reference samples for training and testing data using Collect Earth Online (01sample_pts.py)
2. Generate input data stack from chosen sensor used by the model (02sentinel2_sr.py **currently only using Sentinel data)
3. Create land cover primitives (03RFprimitives.py)
4. Construct categorical land cover map from the set of land cover primitives (04generate_LC.py)
5. Conduct accuracy assessment (05accuracy.py)
6. Estimate area of each land cover class

# Scripts
### Each script will be run on the command-line. The user must provide values for each command-line argument to control the year and AOI to run the analysis for, and which sensor to use. The output Earth Engine asset from a given script must complete before the next script is run.

### Here is a list of possible arguments a script will require:
* -p --project - name of your cloud project
* -a --aoi_s  - the AOI to run the analysis for
* -y --year  - year to run the analysis for
* -s --sensor  - one of "S2" or "planet", determines which sensor the input data is compiled from

### You can use the `-h` flag to retrieve the script's usage example.

![kaza_readme_cmdline](https://user-images.githubusercontent.com/51868526/183131644-4568f7b1-a58d-4a94-a66a-0e8def39f280.JPG)

### If the script reports that an Export task has been started, go to the Code Editor to check on its progress.

![kaza_readme_exportRunning](https://user-images.githubusercontent.com/51868526/183131558-c0433f1b-ad3d-49b8-9d4d-9533a16cd216.JPG)

