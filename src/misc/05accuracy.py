#%%
# Asses Overall, Producer's, User's Accuracies using testing points,
# maybe also export a confusion matrix heatplot 
import ee
from sklearn.metrics import multilabel_confusion_matrix, confusion_matrix, ConfusionMatrixDisplay, accuracy_score, precision_score, f1_score, recall_score
import os
from pathlib import Path
import pandas as pd
import argparse
import matplotlib.pyplot as plt
from utils import helper

if __name__=="__main__":
    ee.Initialize(project='wwf-sig')
    
    parser = argparse.ArgumentParser(
    description="Generate Accuracy report for land cover product",
    usage = "python 05accuracy.py -i input_landcover_img -t testing_sample_pts -o output_metrics_folder"
    )

    parser.add_argument(
    "-i",
    "--input",
    type=str,
    required=True,
    help="asset path to land cover image"
    )

    parser.add_argument(
    "-t",
    "--test_points",
    type=str,
    required=True,
    help="asset path to testing points"
    )

    parser.add_argument(
    "-o",
    "--output",
    type=str,
    required=True,
    help="local output folder to save metrics to"
    )
    
    args = parser.parse_args()
    
    image_id = args.input
    sample_id = args.test_points
    output_path = args.output

#%%
    labels = list(lc_dct.keys())

    if helper.check_exists(image_id):
        raise ee.ee_exception.EEException('image does not exsit')
    elif helper.check_exists(sample_id):
        raise ee.ee_exception.EEException('samples do not exsit')
    else:
        pred_LC_img = ee.Image(image_id)
        test_pts = ee.FeatureCollection(sample_id) 
    
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

    print('Total Test samples: ',test_pts.size().getInfo())
    print('samples per class in ground truth',test_pts.aggregate_histogram('LANDCOVER').getInfo())

    test_w_pred = pred_LC_img.sampleRegions(collection=test_pts,scale=10, projection='EPSG:32734', tileScale=2, geometries=True)
    
    pred = test_w_pred.aggregate_array('classification').getInfo()
    true = test_w_pred.aggregate_array('LANDCOVER').getInfo()
    unique_pred = set(pred)
    unique_true = set(true)
    assert unique_pred==unique_true, f"unique values of predicted and ground truth do not match. pred:{unique_pred}, truth:{unique_true}"
    
    # overall acc,prec,recall,f1
    acc = round(accuracy_score(true,pred),3)
    prec = round(precision_score(true,pred,average="weighted"),3)
    reca = round(recall_score(true,pred,average="weighted"),3)
    f1 = round(f1_score(true,pred,average="weighted"),3)
    # print('Overall Metrics')
    # print(f'Accuracy: {acc}')
    # print(f'Precision: {prec}')
    # print(f'Recall: {reca}')
    # print(f'F1: {f1}')

    # to get class-wise accuracies, must construct a multi-label confusion matrix, outputs true/false positives/negatives per label
    # mcm = multilabel_confusion_matrix(true, pred, sample_weight=None)
    mcm = multilabel_confusion_matrix(true, pred, sample_weight=None, labels=labels, samplewise=False)
    # C:\Users\kyle\anaconda3\envs\gee\lib\site-packages\sklearn\metrics\_classification.py:1334: UndefinedMetricWarning: 
    # Precision is ill-defined and being set to 0.0 in labels with no predicted samples. Use `zero_division` parameter to control this behavior.
    
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

    # Create confusion matrix as dataframe
    cm=confusion_matrix(true, pred)
    cm_df = pd.DataFrame(cm, columns = lc_dct.values(), index = lc_dct.values())
    # plot a confusion matrix to save as a fig, make two diff versions, one where boxes contain actual sample pt counts, other where we normalize counts as % of all samples
    disp_actual = ConfusionMatrixDisplay.from_predictions(y_true=true,y_pred=pred,display_labels=lc_dct.values(),xticks_rotation='vertical')
    disp_norm = ConfusionMatrixDisplay.from_predictions(y_true=true,y_pred=pred,display_labels=lc_dct.values(),xticks_rotation='vertical',normalize='true') # normalize: 'true' (rows), 'pred' (columns), or 'all' (total sample count)
    # Exports
    # cwd = os.getcwd()
    # output_path = Path(f"{cwd}/metrics_{sensor}_{year}_{aoi_s}")
    if not os.path.exists(output_path):
        Path(output_path).mkdir(parents=True)

    # export class accuracies to csv
    df_class.to_csv(f"{output_path}/classAccuracy.csv")

    # export overall accuracy to txt 
    with open(f"{output_path}/overallAccuracy.txt",'w') as f:
        f.write(oa_content)
    print(f"Overall and Class Accuracy reports exported to: {output_path}")

    # export CM to csv
    cm_df.to_csv(f"{output_path}/confMatrix.csv")

    # export CM plot to jpg
    disp_actual.figure_.savefig(f"{output_path}/confMatrix_actualValues.jpg")
    disp_norm.figure_.savefig(f"{output_path}/confMatrix_normalized.jpg")
    print(f"Confusion Matrix CSV file and figure exported to: {output_path}")
# %%
