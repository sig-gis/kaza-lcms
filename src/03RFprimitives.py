import ee
import os
from pathlib import Path
import argparse
from src.utils.check_exists import check_exists
from src.utils.primitives import primitives_to_collection

def main():
    ee.Initialize(project='wwf-sig')

    parser = argparse.ArgumentParser(
    description="Create land cover primitives for all classes in provided training data",
    usage = "python 03RFprimitives.py -i path/to/input_stack -t path/to/training_data -o path/to/output"
    )
    
    parser.add_argument(
        "-i",
        "--input_stack",
        type=str,
        required=True,
        help="full asset path to input stack"
    )
    
    parser.add_argument(
        "-t",
        "--training_data",
        type=str,
        required=True,
        help = "full asset path to training data"
    )
    
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=False,
        help="The full asset path for export. Defaults to: 'projects/wwf-sig/assets/kaza-lc/output_landcover/S2_[year]_Primitives_[aoi]' "
    )

    parser.add_argument(
        "-d",
        "--dry_run",
        dest="dry_run",
        action="store_true",
        help="goes through checks and prints paths to outputs but does not export them.",
        )

    args = parser.parse_args()

    input_stack_path = args.input_stack
    train_path = args.training_data
    output = args.output
    dry_run = args.dry_run

    # Run Checks

    # Check Input Stack exists
    assert check_exists(input_stack_path) == 0, f"Check input_stack asset exists: {input_stack_path}"
    
    # Check Reference data exists
    assert check_exists(train_path) == 0, f"Check training_data asset exists: {train_path}"
    
    # Check -o output value will work if provided 
    # you have to either provide full asset path to output asset or not provide -o value at all to use default output location 
    if output:
        if '/' not in output:
            raise ValueError("Incorrect -o argument: Provide full asset path to -o or leave argument blank to use default output location")
             
        img_coll_path = output
        outputbase = os.path.dirname(output)
        # if / in path but the parent folder for your provided Primitives IC path doesn't exist, catches it
        assert check_exists(outputbase) == 0, f"Check parent folder exists: {outputbase}"
        
    else:
        outputbase = "projects/wwf-sig/assets/kaza-lc/output_landcover"
        img_coll_path = f"{outputbase}/Primitives_{os.path.basename(input_stack_path)}" #default path
    
    # don't want to let user try to export new Images into pre-existing ImageCollection, would be messy to handle
    if check_exists(img_coll_path) == 0:
        raise AssertionError(f"Primitives ImageCollection already exists: {img_coll_path}")

    # Construct local 'metrics' folder path from -o output or a default name if not provided
    cwd = os.path.dirname(os.getcwd())
    metrics_path = os.path.join(cwd,"metrics",os.path.basename(img_coll_path))
    # Check that LC strata in strata.py matches LANDCOVER values of input reference_data 
    ref_data_values = ee.FeatureCollection(train_path).aggregate_array('LANDCOVER').distinct().getInfo()

    # print output locations and exit
    if dry_run: 
        print(f"Would Export Primitives ImageCollection to: {img_coll_path}")
        print(f"Would Export Model Metrics to: {metrics_path}")
        exit()
    
    else:
        # make local metrics folder
        if not os.path.exists(metrics_path):
            Path(metrics_path).mkdir(parents=True)
        print(f"Metrics will be exported to: {metrics_path}")
        
        # run analysis
        input_stack = ee.Image(input_stack_path)
        primitives_to_collection(input_stack,train_path,img_coll_path,metrics_path)

if __name__=="__main__":
    main()