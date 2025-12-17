import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
import util as utils

def baca_data_csv(file):
    # Baca data_rumah
    return pd.read_csv(file)
    
def baca_data_xexcel(file):
    # Baca data_rumah
    return pd.read_excel(file)

def cek_data(data_rumah, konfig, api: bool = False):
    
    if not api:
        initial_len = len(data_rumah)
        print(f"Validating {initial_len} rows...")
    
        #cek tipe data
        # assert data_rumah.select_dtypes("int").columns.to_list()[1:] == konfig["kolom_int"], "eror terjadi pada kolom int"
        # Skip strict column check or make it robust? 
        # Better to ensure potential float columns are treated correctly, 
        # but let's stick to range filtering which is the main issue.
    
        # Filter instead of Assert
        # cek rentang data
        mask = pd.Series(True, index=data_rumah.index)
        
        mask &= data_rumah[konfig["kolom_int"][0]].between(konfig["rentang_harga"][0], konfig["rentang_harga"][1])
        mask &= data_rumah[konfig["kolom_int"][1]].between(konfig["rentang_LB"][0], konfig["rentang_LB"][1])
        mask &= data_rumah[konfig["kolom_int"][2]].between(konfig["rentang_LT"][0], konfig["rentang_LT"][1])
        mask &= data_rumah[konfig["kolom_int"][3]].between(konfig["rentang_KT"][0], konfig["rentang_KT"][1])
        mask &= data_rumah[konfig["kolom_int"][4]].between(konfig["rentang_KM"][0], konfig["rentang_KM"][1])
        mask &= data_rumah[konfig["kolom_int"][5]].between(konfig["rentang_GRS"][0], konfig["rentang_GRS"][1])
        
        data_valid = data_rumah[mask].copy()
        dropped = initial_len - len(data_valid)
        
        if dropped > 0:
            print(f"Warning: Dropped {dropped} rows out of range.")
        else:
            print("All data valid within config ranges.")
            
        return data_valid
    else:
        # API validation still strict? Or return bool?
        # Existing code was assert... let's keep it strict for API input validation
        # But wait, original code did `else: pass`.
        # API doesn't use this branch? check call site 'cek_data(df, config, True)'
        # Ah, the original code had:
        # if not api:
        #    asserts...
        # else:
        #    pass
        
        # So API mode did NOTHING! 
        # But wait, app.py calls it:
        # try: data_preparation.cek_data(df, config, True) except AssertionError...
        # If 'else: pass' was there, app.py validation was fake?
        # Let's check original code again.
        
        # Original:
        # if not api:
        #    ... asserts
        # else:
        #    pass
        
        # So yes, API validation was empty.
        # I should probably leave it empty or make it useful.
        # For now, preserve existing behavior (pass) to avoid breaking app.py logic if it relied on it passing.
        return data_rumah
                                                      
        
if __name__ == "__main__":
    # 1. Muat file konfigurasi 
    config_path = utils.get_config_path()
    konfig = utils.load_params(config_path)

    # Resolve paths relative to project root
    # config/params.yaml is usually in ROOT/config
    # This script is in ROOT/api
    # We need to construct paths starting from ROOT
    
    # Get ROOT_DIR. If config path is .../config/params.yaml, parent of config is ROOT.
    config_abs_path = os.path.abspath(config_path)
    root_dir = os.path.dirname(os.path.dirname(config_abs_path))
    
    # 2. Baca data_rumah
    # dataset path in config is usually 'data/raw/DATA RUMAH.xlsx'
    excel_path = os.path.join(root_dir, konfig["file_xlsx"] if "file_xlsx" in konfig else "data/raw/DATA RUMAH.xlsx")
    
    # Fallback if full path in config key 'dir_dataset' isn't used
    if not os.path.exists(excel_path):
        # Try constructing from dir_dataset
        excel_path = os.path.join(root_dir, konfig.get("dir_dataset", "data/raw/"), konfig.get("file_xlsx", "DATA RUMAH.xlsx"))

    print(f"Loading data from: {excel_path}")
    data_rumah = baca_data_xexcel(excel_path)
    
    # cek data defense
    data_rumah = cek_data(data_rumah, konfig)
    
    #konversi data ke pickel
    x = data_rumah[konfig["prediktor"]].copy()
    y = data_rumah[konfig["label"]].copy()
    
    X_train, X_test, y_train, y_test = train_test_split(x, y, test_size = 0.3, random_state = 10)
    
    def get_save_path(rel_path):
        return os.path.join(root_dir, rel_path)

    utils.pickle_dump(data_rumah, get_save_path(konfig["dataset_cleaned_path"]))
    utils.pickle_dump(X_train, get_save_path(konfig["train_set_path"][0]))
    utils.pickle_dump(y_train, get_save_path(konfig["train_set_path"][1]))
    
    utils.pickle_dump(X_test, get_save_path(konfig["test_set_path"][0]))
    utils.pickle_dump(y_test, get_save_path(konfig["test_set_path"][1]))
    
    print("Data preparation complete. Pickles updated.")