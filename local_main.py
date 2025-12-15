import pandas as pd
import numpy as np
import joblib
import os
import sys
import json
import datetime
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_percentage_error, r2_score

# Configuration
ROOT_DIR = os.getcwd()
DATA_PATH = os.path.join(ROOT_DIR, "data", "raw", "DATA RUMAH.xlsx")
MODEL_DIR = os.path.join(ROOT_DIR, "api", "models")
MODEL_1_PATH = os.path.join(MODEL_DIR, "model_1.pkl")
MODEL_2_PATH = os.path.join(MODEL_DIR, "model_2.pkl")
METRICS_PATH = os.path.join(MODEL_DIR, "metrics.json")

def train_models():
    """Forces training of both models and saves them."""
    print("\n[INFO] Memulai proses training model...")
    
    if not os.path.exists(DATA_PATH):
        print(f"[ERROR] Datasets tidak ditemukan di {DATA_PATH}")
        return False
        
    try:
        df = pd.read_excel(DATA_PATH)
        features = ["LB", "LT", "KT", "KM", "GRS"]
        target = "HARGA"
        
        # Cleaning
        df = df.dropna(subset=features + [target])
        Q1 = df[target].quantile(0.25)
        Q3 = df[target].quantile(0.75)
        IQR = Q3 - Q1
        df_clean = df[(df[target] >= (Q1 - 1.5 * IQR)) & (df[target] <= (Q3 + 1.5 * IQR))]
        
        X = df_clean[features]
        y = df_clean[target]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Model 1
        print("Training Model 1 (Linear Regression)...")
        m1 = LinearRegression()
        m1.fit(X_train, y_train)
        pred1 = m1.predict(X_test)
        r2_1 = r2_score(y_test, pred1)
        mape1 = mean_absolute_percentage_error(y_test, pred1)
        
        # Model 2
        print("Training Model 2 (Random Forest)...")
        m2 = RandomForestRegressor(n_estimators=100, random_state=42)
        m2.fit(X_train, y_train)
        pred2 = m2.predict(X_test)
        r2_2 = r2_score(y_test, pred2)
        mape2 = mean_absolute_percentage_error(y_test, pred2)
        
        # Save
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(m1, MODEL_1_PATH)
        joblib.dump(m2, MODEL_2_PATH)
        
        metrics = {
            "model1": {"name": "Linear Regression", "r2": r2_1, "mape": mape1},
            "model2": {"name": "Random Forest", "r2": r2_2, "mape": mape2},
            "last_updated": datetime.datetime.now().strftime("%d %B %Y %H:%M")
        }
        
        with open(METRICS_PATH, "w") as f:
            json.dump(metrics, f, indent=4)
            
        print(f"[SUCCESS] Training selesai. Metrics tersimpan.")
        return True
    except Exception as e:
        print(f"[ERROR] Training gagal: {e}")
        return False

def load_resources():
    if not os.path.exists(METRICS_PATH) or not os.path.exists(MODEL_1_PATH):
        print("[WARN] Model belum tersedia. Otomatis menjalankan training...")
        if not train_models():
            return None, None, None
            
    try:
        m1 = joblib.load(MODEL_1_PATH)
        m2 = joblib.load(MODEL_2_PATH)
        with open(METRICS_PATH, "r") as f:
            metrics = json.load(f)
        return m1, m2, metrics
    except Exception as e:
        print(f"[ERROR] Gagal memuat resource: {e}")
        return None, None, None

def predict_price():
    m1, m2, metrics = load_resources()
    if not m1: return
    
    print("\n--- 🏠 INPUT DATA RUMAH ---")
    try:
        lb = float(input("Luas Bangunan (m2): "))
        lt = float(input("Luas Tanah (m2): "))
        kt = float(input("Jumlah Kamar Tidur: "))
        km = float(input("Jumlah Kamar Mandi: "))
        grs = float(input("Kapasitas Garasi: "))
        
        input_data = pd.DataFrame([[lb, lt, kt, km, grs]], columns=["LB", "LT", "KT", "KM", "GRS"])
        
        # Logic Switching
        r2_m1 = metrics["model1"]["r2"]
        pred1 = m1.predict(input_data)[0]
        pred2 = m2.predict(input_data)[0]
        
        active_prediction = pred1
        model_name = metrics["model1"]["name"]
        
        # SWITCHING LOGIC
        used_backup = False
        if r2_m1 < 0.65:
            active_prediction = pred2
            model_name = metrics["model2"]["name"]
            used_backup = True
            
        print("\n" + "="*40)
        print(f"💰 ESTIMASI HARGA: Rp {active_prediction:,.0f}")
        print("="*40)
        
        # Admin Info Inline
        print("\n--- 🔧 INFO ADMIN (Backend Logic) ---")
        print(f"Status Model 1 ({metrics['model1']['name']}):")
        print(f"   - Akurasi (R2): {metrics['model1']['r2']:.4f}")
        print(f"   - Prediksi: Rp {pred1:,.0f}")
        
        print(f"Status Model 2 ({metrics['model2']['name']}):")
        print(f"   - Akurasi (R2): {metrics['model2']['r2']:.4f}")
        print(f"   - Prediksi: Rp {pred2:,.0f}")
        
        print(f"\n[KEPUTUSAN SYSTEM]")
        if used_backup:
            print(f"⚠️ Akurasi Model 1 ({r2_m1:.2%}) dibawah standar 65%.")
            print(f"✅ MENGGUNAKAN MODEL 2 ({model_name}) sebagai hasil akhir.")
        else:
            print(f"✅ Akurasi Model 1 ({r2_m1:.2%}) memenuhi standar.")
            print(f"✅ MENGGUNAKAN MODEL 1 ({model_name}) sebagai hasil akhir.")
            
    except ValueError:
        print("[ERROR] Masukkan angka yang valid.")

def show_admin_dashboard():
    _, _, metrics = load_resources()
    if not metrics: return
    
    print("\n" + "="*40)
    print("📊 ADMIN DASHBOARD - MONITORING PERFORMANCE")
    print("="*40)
    print(f"Last Updated: {metrics.get('last_updated', '-')}")
    
    m1 = metrics["model1"]
    m2 = metrics["model2"]
    
    print(f"\nModel 1: {m1['name']}")
    print(f"  - R2 Score : {m1['r2']:.4f}")
    print(f"  - MAPE     : {m1['mape']:.2%}")
    print(f"  - Status   : {'⚠️ LOW ACCURACY' if m1['r2'] < 0.65 else '✅ OPTIMAL'}")
    
    print(f"\nModel 2: {m2['name']} (Backup)")
    print(f"  - R2 Score : {m2['r2']:.4f}")
    print(f"  - MAPE     : {m2['mape']:.2%}")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    while True:
        # clear_screen() # Optional: keep history visible or clear
        print("\n" + "="*40)
        print("   🏠 APLIKASI PREDIKSI HARGA RUMAH")
        print("   Mode: Local Console (Tanpa Streamlit)")
        print("="*40)
        print("1. 🔮 Prediksi Harga (User Mode)")
        print("2. 📊 Admin Dashboard (Status Model)")
        print("3. 🔄 Training Ulang Model")
        print("4. 🚪 Keluar")
        print("-"*40)
        
        choice = input(">> Pilih menu (1-4): ")
        
        if choice == '1':
            predict_price()
            input("\n[Tekan Enter untuk kembali...]")
        elif choice == '2':
            show_admin_dashboard()
            input("\n[Tekan Enter untuk kembali...]")
        elif choice == '3':
            train_models()
            input("\n[Tekan Enter untuk kembali...]")
        elif choice == '4':
            print("\nTerima kasih telah menggunakan aplikasi ini.")
            break
        else:
            print("\n[!] Pilihan tidak valid.")
            
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram dihentikan.")
