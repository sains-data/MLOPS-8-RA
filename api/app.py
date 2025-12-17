from flask import Flask, request, jsonify
import pandas as pd
import util as utils
import joblib
import os
import json
from datetime import datetime
from collections import deque
import numpy as np

# Evidently for Data Drift Detection (v0.4.x API)
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset
from evidently.metrics import DataDriftTable, DatasetDriftMetric

app = Flask(__name__)

# -----------------------------------------------------------------------------
# PREDICTION LOGGING SYSTEM
# -----------------------------------------------------------------------------
MAX_LOG_SIZE = 100
prediction_logs = deque(maxlen=MAX_LOG_SIZE)

def log_prediction(input_data, prediction, status="success", error_msg=None, model_used="Unknown", details=None):
    """Log each prediction request"""
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input": input_data,
        "prediction": prediction,
        "status": status,
        "error": error_msg,
        "model_used": model_used,
        "details": details
    }
    prediction_logs.append(log_entry)
    return log_entry

# -----------------------------------------------------------------------------
# DATA DRIFT DETECTION WITH EVIDENTLY
# -----------------------------------------------------------------------------
# Reference data from training (will be loaded on startup)
reference_data = None
reference_stats = None

def load_reference_stats():
    """Load training data for drift detection with Evidently"""
    global reference_data, reference_stats
    
    # helper for stats
    def calc_stats(df):
        return {
            "mean": df.mean().to_dict(),
            "std": df.std().to_dict(),
            "min": df.min().to_dict(),
            "max": df.max().to_dict(),
            "count": len(df)
        }

    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dirs = [
            os.path.join(base_dir, "..", "data"), # Local
            os.path.join(base_dir, "data")        # Docker
        ]
        
        # 1. Try Pickle
        try:
            for d in data_dirs:
                p = os.path.join(d, "processed", "x_train.pkl")
                if os.path.exists(p):
                    print(f"Loading reference from {p}")
                    reference_data = pd.read_pickle(p)
                    reference_stats = calc_stats(reference_data)
                    print(f"Loaded {len(reference_data)} rows from pickle.")
                    return
        except Exception as e:
            print(f"Failed to load pickle: {e}")

        # 2. Try Excel
        try:
            for d in data_dirs:
                p = os.path.join(d, "raw", "DATA RUMAH.xlsx")
                if os.path.exists(p):
                    print(f"Loading reference from {p}")
                    df = pd.read_excel(p)
                    features = ["LB", "LT", "KT", "KM", "GRS"]
                    reference_data = df[features].dropna()
                    reference_stats = calc_stats(reference_data)
                    print(f"Loaded {len(reference_data)} rows from Excel.")
                    return
        except Exception as e:
            print(f"Failed to load Excel: {e}")

        # 3. Fallback: Synthetic
        print("Using synthetic reference data.")
        np.random.seed(42)
        n_samples = 100
        reference_data = pd.DataFrame({
            "LB": np.random.normal(150, 80, n_samples).clip(30, 500),
            "LT": np.random.normal(180, 100, n_samples).clip(50, 600),
            "KT": np.random.normal(4, 1.5, n_samples).clip(1, 10).astype(int),
            "KM": np.random.normal(3, 1.2, n_samples).clip(1, 8).astype(int),
            "GRS": np.random.normal(2, 1, n_samples).clip(0, 5).astype(int)
        })
        reference_stats = calc_stats(reference_data)

    except Exception as e:
        print(f"Critical error in load_reference_stats: {e}")
        # Final safety net
        reference_data = pd.DataFrame(columns=["LB", "LT", "KT", "KM", "GRS"])
        reference_stats = calc_stats(reference_data)

def calculate_drift_evidently(recent_predictions):
    """Calculate data drift using Evidently library"""
    global reference_data
    
    # Check if reference data is available and not empty
    if reference_data is None or len(reference_data) == 0:
        return None
        
    if len(recent_predictions) < 5:
        return None
    
    # Extract input features from recent predictions
    recent_inputs = []
    for log in recent_predictions:
        if log["status"] == "success":
            input_data = log["input"]
            clean_input = {}
            for key, val in input_data.items():
                if isinstance(val, list):
                    clean_input[key] = val[0] if len(val) > 0 else 0
                else:
                    clean_input[key] = val
            recent_inputs.append(clean_input)
    
    if len(recent_inputs) < 5:
        return None
    
    # Create current data DataFrame
    current_data = pd.DataFrame(recent_inputs)
    features = ["LB", "LT", "KT", "KM", "GRS"]
    
    # Ensure both dataframes have the same columns
    for f in features:
        if f not in current_data.columns:
            current_data[f] = 0
    
    current_data = current_data[features]
    ref_data = reference_data[features].copy()
    
    try:
        # Create Evidently Data Drift Report
        drift_report = Report(metrics=[
            DatasetDriftMetric(),
            DataDriftTable()
        ])
        
        drift_report.run(reference_data=ref_data, current_data=current_data)
        
        # Extract results from report
        report_dict = drift_report.as_dict()
        
        # Parse Evidently results
        drift_results = parse_evidently_report(report_dict, current_data, ref_data)
        drift_results["sample_size"] = len(recent_inputs)
        drift_results["reference_size"] = len(reference_data)
        drift_results["method"] = "evidently"
        
        return drift_results
        
    except Exception as e:
        print(f"Evidently error: {e}")
        # Fallback to simple method if Evidently fails
        return calculate_drift_simple(recent_inputs, features)

def parse_evidently_report(report_dict, current_data, ref_data):
    """Parse Evidently report dictionary to extract drift information"""
    features = ["LB", "LT", "KT", "KM", "GRS"]
    feature_names = {
        "LB": "Luas Bangunan",
        "LT": "Luas Tanah",
        "KT": "Kamar Tidur",
        "KM": "Kamar Mandi",
        "GRS": "Garasi"
    }
    
    drift_report = {}
    dataset_drift = False
    drift_share = 0.0
    
    # Extract metrics from report
    for metric_result in report_dict.get("metrics", []):
        metric_id = metric_result.get("metric", "")
        result = metric_result.get("result", {})
        
        # Dataset-level drift
        if "DatasetDriftMetric" in metric_id:
            dataset_drift = result.get("dataset_drift", False)
            drift_share = result.get("drift_share", 0.0)
        
        # Per-column drift from DataDriftTable
        if "DataDriftTable" in metric_id:
            drift_by_columns = result.get("drift_by_columns", {})
            
            for feature in features:
                if feature in drift_by_columns:
                    col_data = drift_by_columns[feature]
                    
                    is_drifted = col_data.get("drift_detected", False)
                    drift_score = col_data.get("drift_score", 0)
                    stattest_name = col_data.get("stattest_name", "unknown")
                    p_value = col_data.get("p_value", 1.0) if col_data.get("p_value") is not None else 1.0
                    
                    # Determine severity based on p-value and drift detection
                    if is_drifted:
                        if p_value < 0.01:
                            severity = "high"
                        elif p_value < 0.05:
                            severity = "medium"
                        else:
                            severity = "medium"
                    else:
                        severity = "low"
                    
                    drift_report[feature] = {
                        "feature_name": feature_names.get(feature, feature),
                        "drift_detected": is_drifted,
                        "drift_score": round(drift_score, 4) if drift_score else 0,
                        "p_value": round(p_value, 4) if p_value else 1.0,
                        "stattest": stattest_name,
                        "severity": severity,
                        "reference_mean": round(ref_data[feature].mean(), 2),
                        "current_mean": round(current_data[feature].mean(), 2),
                        "reference_std": round(ref_data[feature].std(), 2),
                        "current_std": round(current_data[feature].std(), 2)
                    }
    
    # If no per-column data, create basic report
    if not drift_report:
        for feature in features:
            if feature in current_data.columns and feature in ref_data.columns:
                ref_mean = ref_data[feature].mean()
                cur_mean = current_data[feature].mean()
                ref_std = ref_data[feature].std()
                
                # Simple drift score
                drift_score = abs(cur_mean - ref_mean) / ref_std if ref_std > 0 else 0
                
                drift_report[feature] = {
                    "feature_name": feature_names.get(feature, feature),
                    "drift_detected": drift_score > 0.5,
                    "drift_score": round(drift_score, 4),
                    "p_value": None,
                    "stattest": "z-score",
                    "severity": "high" if drift_score > 1.5 else ("medium" if drift_score > 0.5 else "low"),
                    "reference_mean": round(ref_mean, 2),
                    "current_mean": round(cur_mean, 2),
                    "reference_std": round(ref_std, 2),
                    "current_std": round(current_data[feature].std(), 2)
                }
    
    # Determine overall status
    severities = [d["severity"] for d in drift_report.values()]
    drifted_count = sum(1 for d in drift_report.values() if d.get("drift_detected", False))
    
    if dataset_drift or drifted_count >= 3 or "high" in severities:
        overall_status = "high"
    elif drifted_count >= 1 or "medium" in severities:
        overall_status = "medium"
    else:
        overall_status = "low"
    
    return {
        "overall_status": overall_status,
        "dataset_drift": dataset_drift,
        "drift_share": round(drift_share, 2),
        "drifted_features_count": drifted_count,
        "total_features": len(features),
        "features": drift_report
    }

def calculate_drift_simple(recent_inputs, features):
    """Fallback simple drift calculation"""
    df_recent = pd.DataFrame(recent_inputs)
    
    drift_report = {}
    feature_names = {
        "LB": "Luas Bangunan",
        "LT": "Luas Tanah",
        "KT": "Kamar Tidur",
        "KM": "Kamar Mandi",
        "GRS": "Garasi"
    }
    
    for feature in features:
        if feature in df_recent.columns:
            recent_mean = df_recent[feature].mean()
            recent_std = df_recent[feature].std()
            ref_mean = reference_stats["mean"].get(feature, 0)
            ref_std = reference_stats["std"].get(feature, 1)
            
            drift_score = abs(recent_mean - ref_mean) / ref_std if ref_std > 0 else 0
            
            if drift_score < 0.5:
                severity = "low"
            elif drift_score < 1.5:
                severity = "medium"
            else:
                severity = "high"
            
            drift_report[feature] = {
                "feature_name": feature_names.get(feature, feature),
                "drift_detected": drift_score > 0.5,
                "drift_score": round(drift_score, 4),
                "p_value": None,
                "stattest": "z-score",
                "severity": severity,
                "reference_mean": round(ref_mean, 2),
                "current_mean": round(recent_mean, 2),
                "reference_std": round(ref_std, 2),
                "current_std": round(recent_std, 2)
            }
    
    severities = [d["severity"] for d in drift_report.values()]
    drifted_count = sum(1 for d in drift_report.values() if d.get("drift_detected", False))
    
    if "high" in severities:
        overall_status = "high"
    elif "medium" in severities:
        overall_status = "medium"
    else:
        overall_status = "low"
    
    return {
        "overall_status": overall_status,
        "dataset_drift": overall_status in ["high", "medium"],
        "drift_share": drifted_count / len(features),
        "drifted_features_count": drifted_count,
        "total_features": len(features),
        "features": drift_report,
        "method": "fallback"
    }

# Load config
config_path = utils.get_config_path()
config = utils.load_params(config_path)

# Load Models (Model 1: Linear Regression, Model 2: Random Forest)
model1 = None
model2 = None
model1_metadata = {}
model2_metadata = {}

try:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model1_path = os.path.join(base_dir, "models", "model_1.pkl")
    model2_path = os.path.join(base_dir, "models", "model_2.pkl")
    
    if os.path.exists(model1_path):
        model1 = utils.pickle_load(model1_path)
        print("Model 1 (Linear Regression) loaded.")
    
    if os.path.exists(model2_path):
        model2 = utils.pickle_load(model2_path)
        print("Model 2 (Random Forest) loaded.")
        
    # Also load the old production_model if model 1 is missing, for backward compatibility
    if model1 is None:
        prod_path = os.path.join(base_dir, "models", "production_model.pkl")
        if os.path.exists(prod_path):
             model1 = utils.pickle_load(prod_path)
             print("Legacy Production Model loaded as Model 1.")

    # Load Metrics to determine accuracy
    metrics_path = os.path.join(base_dir, "models", "metrics.json")
    if os.path.exists(metrics_path):
        with open(metrics_path, 'r') as f:
            metrics_data = json.load(f)
            # Parse structure: could be old (flat) or new (nested)
            if "model1" in metrics_data:
                model1_metadata = metrics_data["model1"]
                model2_metadata = metrics_data.get("model2", {})
            else:
                # Old format
                model1_metadata = {"r2": metrics_data.get("r2", 0), "mape": metrics_data.get("mape", 0)}
                model2_metadata = {}
    
except Exception as e:
    print(f"Error loading models: {e}")

# Load reference stats for drift detection
load_reference_stats()

import data_preparation
import preprocessing
# Helper needed for pickle loading if it uses classes from these modules

@app.route('/')
def home():
    return "House Price Prediction API is Up! (Dual Model Supported)"

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data_json = request.get_json()
        
        # Expecting input keys matching the predictors
        predictors = config['prediktor'] # LB, LT, KT, KM, GRS
        
        # Ensure all predictors are present
        input_data = {}
        missing_fields = []
        for p in predictors:
            if p not in data_json:
                missing_fields.append(p)
            else:
                input_data[p] = [data_json[p]]
        
        if missing_fields:
             return jsonify({"error": f"Missing features: {missing_fields}"}), 400

        # Create DataFrame
        df = pd.DataFrame(input_data)
        
        # Ensure correct data types (int64)
        for p in predictors:
            df[p] = df[p].astype('int64')

        # Validate data
        try:
           data_preparation.cek_data(df, config, True)
        except AssertionError as ae:
            return jsonify({"status": "error", "message": f"Validation Error: {str(ae)}"}), 400

        # Predict with Model 1 (Linear Regression)
        pred1 = 0
        if model1:
            pred1 = model1.predict(df)[0]
        
        # Predict with Model 2 (Random Forest)
        pred2 = 0
        if model2:
            pred2 = model2.predict(df)[0]
        
        # Decision Logic: Use the model with higher accuracy
        active_prediction = pred1
        active_model_name = "Model 1 (Linear Regression)"
        
        model1_r2 = model1_metadata.get("r2", 0)
        model2_r2 = model2_metadata.get("r2", 0)
        
        use_model2 = False
        
        if model2 and model1:
             if model2_r2 > model1_r2:
                 use_model2 = True
                 print(f"Choosing Model 2 (R2: {model2_r2:.4f}) over Model 1 (R2: {model1_r2:.4f})")
             else:
                 print(f"Choosing Model 1 (R2: {model1_r2:.4f}) over Model 2 (R2: {model2_r2:.4f})")
        elif model2 and not model1:
             use_model2 = True
             print("Model 1 missing, using Model 2")
             
        if use_model2:
            active_prediction = pred2
            active_model_name = "Model 2 (Random Forest)"
        
        # Result
        result = float(active_prediction)
        
        # Log the successful prediction with clean data (not list format)
        log_input = {p: data_json[p] for p in predictors}
        
        details = {
            "model1": {
                "prediction": float(pred1) if model1 else None,
                "r2": model1_r2
            },
            "model2": {
                "prediction": float(pred2) if model2 else None,
                "r2": model2_metadata.get("r2", 0)
            },
            "switched": active_model_name.startswith("Model 2")
        }
        
        log_prediction(log_input, result, "success", model_used=active_model_name, details=details)
        
        return jsonify({
            "status": "success",
            "prediction": result,
            "model_used": active_model_name,
            "details": details
        })
        
    except Exception as e:
        # Log the failed prediction
        log_prediction(data_json if 'data_json' in dir() else {}, None, "error", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/metrics', methods=['GET'])
def get_metrics():
    try:
        # Resolve metrics.json relative to this file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        metrics_path = os.path.join(base_dir, "models", "metrics.json")
        
        if os.path.exists(metrics_path):
            import json
            with open(metrics_path, "r") as f:
                metrics = json.load(f)
            return jsonify({"status": "success", "data": metrics})
        else:
            return jsonify({"status": "error", "message": "Metrics not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    """Get prediction logs with optional filtering"""
    try:
        limit = request.args.get('limit', 50, type=int)
        status_filter = request.args.get('status', None)
        
        logs_list = list(prediction_logs)
        
        # Filter by status if specified
        if status_filter:
            logs_list = [log for log in logs_list if log["status"] == status_filter]
        
        # Return most recent first, limited
        logs_list = logs_list[-limit:][::-1]
        
        # Calculate summary stats
        total_logs = len(prediction_logs)
        success_count = sum(1 for log in prediction_logs if log["status"] == "success")
        error_count = total_logs - success_count
        
        return jsonify({
            "status": "success",
            "data": {
                "logs": logs_list,
                "summary": {
                    "total_requests": total_logs,
                    "success_count": success_count,
                    "error_count": error_count,
                    "success_rate": round(success_count / total_logs * 100, 2) if total_logs > 0 else 0
                }
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/drift', methods=['GET'])
def get_drift():
    """Get data drift analysis using Evidently"""
    try:
        recent_logs = list(prediction_logs)
        
        # Use Evidently-based drift detection
        drift_analysis = calculate_drift_evidently(recent_logs)
        
        if drift_analysis:
            return jsonify({
                "status": "success",
                "data": drift_analysis
            })
        else:
            return jsonify({
                "status": "success",
                "data": {
                    "overall_status": "insufficient_data",
                    "message": "Minimal 5 prediksi berhasil diperlukan untuk analisis drift",
                    "current_samples": len([l for l in recent_logs if l.get("status") == "success"])
                }
            })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
