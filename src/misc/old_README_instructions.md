(not using 05accurcy.py script anymore)
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

**The new files are confMatrix.jpg, confMatrix.csv, classAccuracy.csv, overallAccuracy.txt**


(not using pixelCounter script -> Area Estimation google sheet workflow anymore)
# Area Estimation (last step, not Python)

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