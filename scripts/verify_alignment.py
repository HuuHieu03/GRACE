import json
import pandas as pd

df_val = pd.read_csv('runs/step0_real_reveal/canonical_reveal_val.csv')
meta_val = json.load(open('data/raw_c_files/reveal/validation_metadata.json', encoding='utf-8'))
val_match = all(df_val.iloc[i]['id'] == f"reveal:validation:{meta_val[i]['id']}#{i}" for i in range(len(df_val)))
print('Reveal val all match:', val_match, len(df_val))

df_test = pd.read_csv('runs/step0_real_reveal/canonical_reveal_test.csv')
meta_test = json.load(open('data/raw_c_files/reveal/test_metadata.json', encoding='utf-8'))
test_match = all(df_test.iloc[i]['id'] == f"reveal:test:{meta_test[i]['id']}#{i}" for i in range(len(df_test)))
print('Reveal test all match:', test_match, len(df_test))

df_dev_val = pd.read_csv('runs/step0_real_devign/canonical_devign_val.csv')
meta_dev_val = json.load(open('data/raw_c_files/devign/validation_metadata.json', encoding='utf-8'))
dev_val_match = all(df_dev_val.iloc[i]['id'] == f"devign:validation:{meta_dev_val[i]['id']}" for i in range(len(df_dev_val)))
print('Devign val all match:', dev_val_match, len(df_dev_val))

df_dev_test = pd.read_csv('runs/step0_real_devign/canonical_devign_test.csv')
meta_dev_test = json.load(open('data/raw_c_files/devign/test_metadata.json', encoding='utf-8'))
dev_test_match = all(df_dev_test.iloc[i]['id'] == f"devign:test:{meta_dev_test[i]['id']}" for i in range(len(df_dev_test)))
print('Devign test all match:', dev_test_match, len(df_dev_test))
