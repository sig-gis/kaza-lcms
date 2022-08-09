#%%
# Asses Overall, Producer's, User's Accuracies using testing points,
# maybe also export a confusion matrix heatplot 
import ee
from sklearn import metrics
import os
from pathlib import Path
import pandas as pd
import argparse

if __name__=="__main__":
    ee.Initialize()
    
    parser = argparse.ArgumentParser(
    description="Generate Accuracy report for land cover product",
    usage = "python 05accuracy.py -p kaza-lc -a Zambezi -y 2021 -s S2"
    )

    parser.add_argument(
    "-p",
    "--project",
    type=str,
    required=True
    )
    
    parser.add_argument(
    "-a",
    "--aoi_string",
    type=str,
    required=True
    )
    
    parser.add_argument(
    "-y",
    "--year",
    type=int,
    required=True
    )
    
    parser.add_argument(
    "-s",
    "--sensor",
    type=str,
    required=True
    )
    
    
    
    args = parser.parse_args()
    
    project=args.project #kaza-lc
    aoi_s = args.aoi_string #SNMC
    year = args.year #2021
    sensor=args.sensor #S2
    
    
    

    labels = [0,1,2,3,4,5,6,7]
    lc_dct = {
        0:'Bare',
        1:'Built',
        2:'Crop',
        3:'Forest',
        4:'Grass',
        5:'Shrub',
        6:'Water',
        7:'Wetland'
        }
    pred_LC_img = ee.Image(f"projects/{project}/assets/kaza-lc/output_landcover/{sensor}_{year}_LandCover_{aoi_s}")

    # EOSS's KAZA LC legend can be looked at here https:docs.google.com/document/d/12K4MqsAeq2bmCx3XyOMZefx6yBAkQv3lg_FA8NIxoow/edit?usp=sharing
        # aggregate LC2020 sub-classes together to make training points
        
        # Bare 60,61>>0
        # Built 50>> 1
        # Cropland 40>> 2
        # Forest 110,120,210>> 3
        # Grassland 31,32>> 4
        # Shrubs 130,222,231,232>> 5
        # Water 80,81>> 6
        # Wetland 90,91,92>> 7
        
    # Until we have independently interpreted LC refrence samples, the ground truth is the collapsed EOSS LC product 
    # we generated the training samples from, so the LANDCOVER property in the test points is the 'actual' for pred vs actual

    test_pts = ee.FeatureCollection(f"projects/{project}/assets/kaza-lc/sample_pts/testing{aoi_s}{year}") 
    print('Total Test samples: ',test_pts.size().getInfo())
    test_w_pred = pred_LC_img.sampleRegions(collection=test_pts,scale=10, projection='EPSG:32734', tileScale=2, geometries=True)

    #print(test_w_pred.first().getInfo()['properties'])

    pred = test_w_pred.aggregate_array('classification').getInfo()
    true = test_w_pred.aggregate_array('LANDCOVER').getInfo()
    # print('samples per class in ground truth',test_pts.aggregate_histogram('LANDCOVER').getInfo())

    # overall acc,prec,recall,f1
    acc = round(metrics.accuracy_score(true,pred),3)
    prec = round(metrics.precision_score(true,pred,average="weighted"),3)
    reca = round(metrics.recall_score(true,pred,average="weighted"),3)
    f1 = round(metrics.f1_score(true,pred,average="weighted"),3)
    # print('Overall Metrics')
    # print(f'Accuracy: {acc}')
    # print(f'Precision: {prec}')
    # print(f'Recall: {reca}')
    # print(f'F1: {f1}')

    # to get class-wise accuracies, must construct a confusion matrix 
    mcm = metrics.multilabel_confusion_matrix(true, pred, sample_weight=None, labels=[0,1,2,3,4,5,6,7], samplewise=False)
    # Returns list of 2x2 arrays of length labels 
    # true negatives == arr[0][0]
    # false negatives == arr[1][0]
    # true positives == arr[1][1]
    # false positives == arr[0][1]
    omit_col, comit_col, prod, user = [],[],[],[]
    for i in labels:
        # print('Class', i)
        arr = mcm[i]
        true_neg = arr[0][0]
        false_neg = arr[1][0]
        true_pos = arr[1][1]
        false_pos = arr[0][1]
        
        omission = (false_neg / (false_neg + true_pos))
        comission = (false_pos / (false_neg + true_pos))
        # print(f"Omission Error: {omission}")
        # print(f"Comission Error: {comission}")
        prod_acc = round(100 - (omission*100),2) # Producers accuracy = 100% - Omission error
        user_acc = round(100 - (comission*100),2) # Users accuracy = 100% - Comission Error
        # print(f"Producer's Accuracy: {prod_acc}")
        # print(f"User's Accuracy: {user_acc}")
        omit_col.append(omission)
        comit_col.append(comission)
        prod.append(prod_acc)
        user.append(user_acc)

    classes = [lc_dct[i] for i in labels]
    df_class = pd.DataFrame({'Class':classes, 'OmissionError':omit_col, 'ComissionError':comit_col, 'ProducerAcc':prod, 'UserAcc':user})    

    oa_content = f"Accuracy:{acc}\nPrecision:{prec}\nRecall:{reca}\nF1:{f1}"
    print(oa_content)

    cwd = os.getcwd()
    output_path = Path(f"{cwd}/metrics_{sensor}_{year}_{aoi_s}")
    if not os.path.exists(output_path):
        output_path.mkdir(parents=True)

    df_class.to_csv(f"{output_path}/classAccuracy.csv")
    with open(f"{output_path}/overallAccuracy.txt",'w') as f:
        f.write(oa_content)
   

# %%
