import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_percentage_error, r2_score
import joblib
import os
import sys
import json
import datetime

# Paths
ROOT_DIR = os.getcwd()
DATA_PATH = os.path.join(ROOT_DIR, "data", "raw", "DATA RUMAH.xlsx")
MODEL_DIR = os.path.join(ROOT_DIR, "api", "models")
MODEL_1_PATH = os.path.join(MODEL_DIR, "model_1.pkl")
MODEL_2_PATH = os.path.join(MODEL_DIR, "model_2.pkl")
METRICS_PATH = os.path.join(MODEL_DIR, "metrics.json")

def train():
    print("Starting training process...")
    
    if not os.path.exists(DATA_PATH):
        print(f"Error: Data file not found at {DATA_PATH}")
        sys.exit(1)

    # 1. Load Data
    print("Loading data...")
    df = pd.read_excel(DATA_PATH)
    
    # 2. Preprocessing
    # Filter features
    features = ["LB", "LT", "KT", "KM", "GRS"]
    target = "HARGA"
    
    # Simple cleaning: Drop NaNs
    df = df.dropna(subset=features + [target])
    
    # Outlier Removal (Simple IQR) for Price
    Q1 = df[target].quantile(0.25)
    Q3 = df[target].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    df_clean = df[(df[target] >= lower_bound) & (df[target] <= upper_bound)]
    print(f"Data shape after cleaning: {df_clean.shape} (Original: {df.shape})")
    
    X = df_clean[features]
    y = df_clean[target]
    
    # 3. Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 4. Train Model 1 (Linear Regression) - Primary
    print("Training Model 1 (Linear Regression)...")
    model1 = LinearRegression()
    model1.fit(X_train, y_train)
    
    # Evaluate Model 1
    y_pred1 = model1.predict(X_test)
    mape1 = mean_absolute_percentage_error(y_test, y_pred1)
    r2_1 = r2_score(y_test, y_pred1)
    
    print(f"Model 1 Performance:")
    print(f"MAPE: {mape1:.2%}")
    print(f"R2 Score: {r2_1:.4f}")
    
    # 5. Train Model 2 (Random Forest) - Backup
    print("Training Model 2 (Random Forest)...")
    model2 = RandomForestRegressor(n_estimators=100, random_state=42)
    model2.fit(X_train, y_train)
    
    # Evaluate Model 2
    y_pred2 = model2.predict(X_test)
    mape2 = mean_absolute_percentage_error(y_test, y_pred2)
    r2_2 = r2_score(y_test, y_pred2)
    
    print(f"Model 2 Performance:")
    print(f"MAPE: {mape2:.2%}")
    print(f"R2 Score: {r2_2:.4f}")
    
    # 6. Save Models
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model1, MODEL_1_PATH)
    joblib.dump(model2, MODEL_2_PATH)
    print(f"Models saved to {MODEL_DIR}")

    # 7. Save Metrics
    metrics_data = {
        "model1": {
            "name": "Linear Regression",
            "mape": mape1,
            "r2": r2_1
        },
        "model2": {
            "name": "Random Forest Regressor",
            "mape": mape2,
            "r2": r2_2
        },
        "last_updated": datetime.datetime.now().strftime("%d %B %Y %H:%M")
    }
    
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics_data, f, indent=4)
    print(f"Metrics saved to {METRICS_PATH}")

if __name__ == "__main__":
    train()
