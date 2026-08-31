import os
import json
from datasets import load_dataset
from tqdm import tqdm

def save_devign():
    print("Loading Devign dataset from google/code_x_glue_cc_defect_detection...")
    dataset = load_dataset("google/code_x_glue_cc_defect_detection")
    
    base_dir = os.path.join("data", "raw_c_files", "devign")
    
    for split in dataset.keys():
        print(f"Processing Devign {split} split...")
        split_dir = os.path.join(base_dir, split)
        os.makedirs(split_dir, exist_ok=True)
        
        # Save a metadata file as well to keep track of the original JSON info
        metadata = []
        
        for idx, item in enumerate(tqdm(dataset[split])):
            item_id = item.get('id', idx)
            target = item.get('target', -1)
            project = item.get('project', 'unknown')
            
            # Clean filename
            filename = f"id_{item_id}_label_{target}_{project}.c"
            filepath = os.path.join(split_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(item['func'])
            
            item_meta = dict(item)
            item_meta['c_file_path'] = filepath
            metadata.append(item_meta)
            
        with open(os.path.join(base_dir, f"{split}_metadata.json"), 'w', encoding='utf-8') as f:
            json.dump(metadata, f)

def save_reveal():
    print("Loading Reveal dataset from claudios/ReVeal...")
    try:
        dataset = load_dataset("claudios/ReVeal")
    except Exception as e:
        print(f"Failed to load claudios/ReVeal ({e}), trying Oscaraandersson/reveal...")
        dataset = load_dataset("Oscaraandersson/reveal")
    
    base_dir = os.path.join("data", "raw_c_files", "reveal")
    
    for split in dataset.keys():
        print(f"Processing Reveal {split} split...")
        split_dir = os.path.join(base_dir, split)
        os.makedirs(split_dir, exist_ok=True)
        
        metadata = []
        
        for idx, item in enumerate(tqdm(dataset[split])):
            item_id = item.get('hash', idx)
            target_val = item.get('label', item.get('output', item.get('target', 0)))
            func_code = item.get('functionSource', item.get('input', item.get('func', item.get('code', ''))))
            project = item.get('project', 'reveal')
            
            if not func_code or not str(func_code).strip():
                continue
                
            filename = f"id_{idx}_hash_{item_id}_label_{target_val}_{project}.c"
            filepath = os.path.join(split_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(str(func_code))
                
            item_meta = dict(item)
            item_meta['c_file_path'] = filepath
            item_meta['id'] = str(item_id)
            item_meta['target'] = int(target_val) if isinstance(target_val, (int, float, str)) and str(target_val).isdigit() else target_val
            metadata.append(item_meta)
            
        with open(os.path.join(base_dir, f"{split}_metadata.json"), 'w', encoding='utf-8') as f:
            json.dump(metadata, f)

if __name__ == "__main__":
    import sys
    os.makedirs(os.path.join("data", "raw_c_files"), exist_ok=True)
    
    # Check if we should process devign or skip if already downloaded
    devign_train_dir = os.path.join("data", "raw_c_files", "devign", "train")
    if os.path.exists(devign_train_dir) and len(os.listdir(devign_train_dir)) > 1000:
        print(f"Devign dataset already extracted ({len(os.listdir(devign_train_dir))} train files found). Skipping Devign.")
    else:
        try:
            save_devign()
        except Exception as e:
            print(f"Error processing Devign: {e}")
        
    try:
        save_reveal()
    except Exception as e:
        print(f"Error processing Reveal: {e}")
        
    print("Dataset preparation complete! Raw C files are saved in data/raw_c_files/")
