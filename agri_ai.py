"""
Krishi_Kaar — Agriculture AI Engine (Production-Grade)

Trains and serves Random Forest models for:
1. Crop Recommendation (22 crops from N/P/K/Temp/Hum/pH/Rainfall)
2. Fertilizer Recommendation (from soil + climate features)
3. Irrigation Prediction (from moisture/temp/humidity)

Thread-safe, cached, with confidence scores and validation.
"""
import numpy as np
import pickle
import os
import threading
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from config import Config

MODEL_FILE = Config.AGRI_MODEL_FILE

_models = None
_models_lock = threading.Lock()


def train_agri_models():
    """
    Train industrial-grade Random Forest models using real datasets.
    Returns the trained models dict.
    """
    data_dir = Config.DATA_DIR
    
    models = {}
    
    # --- 1. Crop Model ---
    crop_csv = os.path.join(data_dir, 'Crop_recommendation.csv')
    if os.path.exists(crop_csv):
        df_crop = pd.read_csv(crop_csv)
        feature_cols = ['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']
        X_crop = df_crop[feature_cols].values
        y_crop = df_crop['label'].values
        rf_crop = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
        rf_crop.fit(X_crop, y_crop)
        models['crop'] = rf_crop
        print(f"[AGRI_AI] Crop model trained on {len(X_crop)} samples, {len(rf_crop.classes_)} classes")
    else:
        print(f"[AGRI_AI] WARNING: {crop_csv} not found, using fallback")
        models['crop'] = RandomForestClassifier(n_estimators=10).fit([[50,50,50,25,60,7,50]], ["Unknown"])

    # --- 2. Fertilizer Model ---
    fert_csv = os.path.join(data_dir, 'Fertilizer Prediction.csv')
    if os.path.exists(fert_csv):
        df_fert = pd.read_csv(fert_csv)
        fert_features = ['Temparature', 'Humidity', 'Moisture', 'Nitrogen', 'Potassium', 'Phosphorous']
        X_fert = df_fert[fert_features].values
        y_fert = df_fert['Fertilizer Name'].values
        rf_fert = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_fert.fit(X_fert, y_fert)
        models['fertilizer'] = rf_fert
        print(f"[AGRI_AI] Fertilizer model trained on {len(X_fert)} samples")
    else:
        print(f"[AGRI_AI] WARNING: {fert_csv} not found, using fallback")
        models['fertilizer'] = RandomForestClassifier(n_estimators=10).fit([[25,60,50,50,50,50]], ["Stable"])

    # --- 3. Irrigation Model (v2) ---
    irri_csv = os.path.join(data_dir, 'irrigation_prediction.csv')
    if os.path.exists(irri_csv):
        df_irri = pd.read_csv(irri_csv)
        irri_features = ['Soil_Type', 'Soil_pH', 'Soil_Moisture', 'Temperature_C', 'Humidity', 'Rainfall_mm', 'Crop_Type']
        
        # Standardize strings
        for col in ['Soil_Type', 'Crop_Type', 'Irrigation_Need']:
            df_irri[col] = df_irri[col].astype(str).str.title()
            
        soil_enc = LabelEncoder()
        crop_enc = LabelEncoder()
        label_enc = LabelEncoder()
        
        df_irri['Soil_Type'] = soil_enc.fit_transform(df_irri['Soil_Type'])
        df_irri['Crop_Type'] = crop_enc.fit_transform(df_irri['Crop_Type'])
        df_irri['Irrigation_Need'] = label_enc.fit_transform(df_irri['Irrigation_Need'])
        
        X_irr = df_irri[irri_features].values
        y_irr = df_irri['Irrigation_Need'].values
        
        rf_irr = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
        rf_irr.fit(X_irr, y_irr)
        
        models['irrigation'] = rf_irr
        models['irr_encoders'] = {'soil': soil_enc, 'crop': crop_enc, 'label': label_enc}
        print(f"[AGRI_AI] Irrigation v2 model trained on {len(X_irr)} samples")
    else:
        print(f"[AGRI_AI] WARNING: {irri_csv} not found, using basic fallback")
        models['irrigation'] = RandomForestClassifier(n_estimators=10).fit([[1, 7, 50, 25, 60, 500, 1]], [0])
        models['irr_encoders'] = None

    # --- 4. Compatibility Model ---
    compat_csv = os.path.join(data_dir, 'Soil-Climate-data.csv')
    if os.path.exists(compat_csv):
        df_compat = pd.read_csv(compat_csv)
        # Features needed to correctly match the farm setup
        req_cols = ['Crop_Type', 'Soil_Type', 'Temperature', 'Humidity', 'Rainfall', 'Soil_pH', 'Soil_Nitrogen']
        if all(col in df_compat.columns for col in req_cols + ['Compatible']):
            
            # Standardize capitalization for reliable encoding
            df_compat['Crop_Type'] = df_compat['Crop_Type'].astype(str).str.title()
            df_compat['Soil_Type'] = df_compat['Soil_Type'].astype(str).str.title()
            
            crop_encoder = LabelEncoder()
            soil_encoder = LabelEncoder()
            
            df_compat['Crop_Type'] = crop_encoder.fit_transform(df_compat['Crop_Type'])
            df_compat['Soil_Type'] = soil_encoder.fit_transform(df_compat['Soil_Type'])
            
            X_compat = df_compat[req_cols].values
            y_compat = df_compat['Compatible'].values
            
            rf_compat = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
            rf_compat.fit(X_compat, y_compat)
            
            models['compatibility_model'] = rf_compat
            models['compatibility_encoders'] = {'crop': crop_encoder, 'soil': soil_encoder}
            print(f"[AGRI_AI] Compatibility model trained on {len(X_compat)} samples")
        else:
            print("[AGRI_AI] WARNING: Soil-Climate-data.csv missing required columns")
            models['compatibility_model'] = None
    else:
        pass

    with open(MODEL_FILE, 'wb') as f:
        pickle.dump(models, f)
    print(f"[AGRI_AI] All models saved to {MODEL_FILE}")
    return models


def _load_models():
    """Thread-safe model loading with caching."""
    global _models
    if _models is not None:
        return _models
    
    with _models_lock:
        if _models is not None:
            return _models
        
        if not os.path.exists(MODEL_FILE):
            print("[AGRI_AI] Model file not found. Training fresh models...")
            _models = train_agri_models()
        else:
            try:
                with open(MODEL_FILE, 'rb') as f:
                    _models = pickle.load(f)
                # Validate model structure
                required_keys = ['crop', 'fertilizer', 'irrigation', 'compatibility_model', 'irr_encoders']
                if not all(k in _models for k in required_keys):
                    print("[AGRI_AI] Model file incomplete. Retraining...")
                    _models = train_agri_models()
            except Exception as e:
                print(f"[AGRI_AI] Model load error: {e}. Retraining...")
                _models = train_agri_models()
        return _models


# --- Soil Profile Mappings (Expert Data) ---
SOIL_PROFILES = {
    "Alluvial Soils": {"N": 80, "P": 40, "K": 50, "ph": 6.8},
    "Black": {"N": 60, "P": 50, "K": 70, "ph": 7.5},
    "Clay": {"N": 50, "P": 40, "K": 60, "ph": 6.5},
    "Red": {"N": 40, "P": 30, "K": 40, "ph": 5.5},
    "Sandy": {"N": 20, "P": 10, "K": 20, "ph": 6.0},
    "Loamy": {"N": 90, "P": 50, "K": 80, "ph": 6.7},
}

def get_recommendations(readings, user_soil="Alluvial Soils", rainfall=800.0, acres=5.0):
    """
    Generate all AI recommendations from sensor readings.
    Fuses real-time climate (Temp/Hum/Moist) with inferred soil chemistry (NPK/pH).
    """
    try:
        models = _load_models()
        
        # 0. Soil Profile Inference Layer
        # Use user-selected soil type to fetch NPK/pH if hardware isn't providing them
        profile = SOIL_PROFILES.get(str(user_soil).title(), SOIL_PROFILES["Alluvial Soils"])
        
        # Merge: Real-time Climate + Soil Inference
        n = float(readings.get('nitrogen', profile["N"]))
        p = float(readings.get('phosphorus', profile["P"]))
        k = float(readings.get('potassium', profile["K"]))
        ph_val = float(readings.get('ph', profile["ph"]))
        
        # Real-time Hardware Vitals (User's DHT11 + Soil Probe)
        t = float(readings.get('air_temperature', 25))
        h = float(readings.get('humidity', 60))
        m = float(readings.get('soil_moisture', 50))
        
        sal = float(readings.get('salinity', 1.0))
        
        # 1. Prediction for Irrigation Need (Liters)
        irr_status = "OFF"
        irr_label = "No Irrigation Needed"
        water_liters = 0
        
        if models.get('irr_encoders'):
            try:
                # Features: ['Soil_Type', 'Soil_pH', 'Soil_Moisture', 'Temperature_C', 'Humidity', 'Rainfall_mm', 'Crop_Type']
                s_enc = models['irr_encoders']['soil']
                c_enc = models['irr_encoders']['crop']
                l_enc = models['irr_encoders']['label']
                
                safe_soil = str(user_soil).title()
                safe_crop = str(readings.get('crop_type', 'Wheat')).title()
                
                if safe_soil in s_enc.classes_ and safe_crop in c_enc.classes_:
                    s_idx = s_enc.transform([safe_soil])[0]
                    c_idx = c_enc.transform([safe_crop])[0]
                    
                    irri_X = [[s_idx, ph_val, m, t, h, rainfall, c_idx]]
                    pred_idx = models['irrigation'].predict(irri_X)[0]
                    need_label = str(l_enc.inverse_transform([pred_idx])[0])
                    
                    irr_label = need_label
                    if need_label != "Low":
                        irr_status = "ON"
                        # Dynamic Liters Calculation (Daily Consumption Model)
                        # ~1500L/acre/day for Medium, ~4500L/acre/day for High
                        # ~2000L/acre/day for Medium, ~6000L/acre/day for High
                        mult = 2000 if need_label == "Medium" else 6000
                        water_liters = int(mult * acres)
                else:
                    # Generic Fallback
                    if m < 30:
                        irr_status = "ON"
                        irr_label = "Medium"
                        water_liters = int(2000 * acres)
            except Exception as ex:
                print(f"Irrigation eval error: {ex}")
        
        # 2. Fertilizer Prediction with Expert Logic Layer
        # Base ML prediction
        fert_pred = str(models['fertilizer'].predict([[t, h, m, n, k, p]])[0])
        
        # Expert Override: If Nitrogen is very high, Urea (mostly N) is almost certainly wrong
        if n > 80:
            if p < 50: fert_pred = "DAP (Diammonium Phosphate)"
            elif k < 40: fert_pred = "MOP (Muriate of Potash)"
            else: fert_pred = "Organic Compost / Slow Release"
        elif n < 20:
            fert_pred = "Urea / High Nitrogen Booster"
        
        # Expert advice string
        fert_advice = f"{fert_pred} recommended: "
        if n > 80: fert_advice += "Excess nitrogen detected, prioritizing phosphorus/potassium."
        elif n < 30: fert_advice += "Critical nitrogen deficiency detected."
        else: fert_advice += "Balanced nutrient profile maintains stability."

        # 3. Crop Recommendation with Multi-Factor Fusion (Primary Success Predictor)
        crop_probs = models['crop'].predict_proba([[n, p, k, t, h, ph_val, rainfall]])[0]
        top_indices = np.argsort(crop_probs)[-3:][::-1]
        top_crops = []
        
        best_overall_score = -1
        primary_match = None
        
        for idx in top_indices:
            crop_name = str(models['crop'].classes_[idx]).title()
            conf = round(float(crop_probs[idx]) * 100, 1)
            
            # Verify Biological Compatibility
            compat_score = 0
            if models.get('compatibility_model') and models.get('compatibility_encoders'):
                try:
                    c_enc_comp = models['compatibility_encoders']['crop']
                    s_enc_comp = models['compatibility_encoders']['soil']
                    
                    if crop_name in c_enc_comp.classes_ and str(user_soil).title() in s_enc_comp.classes_:
                        c_val = c_enc_comp.transform([crop_name])[0]
                        s_val = s_enc_comp.transform([str(user_soil).title()])[0]
                        compat_X = [[c_val, s_val, t, h, rainfall, ph_val, n]]
                        c_probs = models['compatibility_model'].predict_proba(compat_X)[0]
                        class_idx = np.where(models['compatibility_model'].classes_ == 1)[0]
                        if len(class_idx) > 0:
                            compat_score = round(float(c_probs[class_idx[0]]) * 100, 1)
                except Exception: pass
            
            # Fusion Score: Weighted Average (70% ML Confidence, 30% Soil Compatibility)
            fusion_score = (conf * 0.7) + (compat_score * 0.3) if compat_score > 0 else conf
            
            crop_obj = {
                "name": crop_name, 
                "confidence": conf, 
                "compatibility": compat_score if compat_score > 0 else "N/A",
                "fusion_score": round(fusion_score, 1)
            }
            
            if fusion_score > best_overall_score:
                best_overall_score = fusion_score
                primary_match = crop_obj
                
            top_crops.append(crop_obj)
        
        # Sort by fusion score
        top_crops = sorted(top_crops, key=lambda x: x['fusion_score'], reverse=True)
        top_crop_names = [c["name"] for c in top_crops]
        
        # 4. Health Score
        score = 100.0
        score -= abs(ph_val - 6.5) * 8
        if n < 20 or p < 20 or k < 20: score -= 15 # Nutrient deficiency
        health_score = max(5, min(100, int(score)))

        return {
            "top_crops": top_crop_names,
            "top_crops_detailed": top_crops,
            "primary_crop": primary_match or top_crops[0],
            "crop": top_crop_names[0] if top_crop_names else "Unknown",
            "fertilizer": fert_pred,
            "fertilizer_advice": fert_advice,
            "irrigation": irr_status,
            "irrigation_label": irr_label,
            "water_liters": water_liters,
            "health_score": health_score
        }
    except Exception as e:
        print(f"[AGRI_AI] Inference error: {e}")
        return {
            "top_crops": ["N/A"], 
            "top_crops_detailed": [{"name": "N/A", "confidence": 0, "compatibility": 0, "fusion_score": 0}],
            "primary_crop": {"name": "N/A", "confidence": 0, "compatibility": 0, "fusion_score": 0},
            "crop": "N/A", 
            "fertilizer": "Stable", 
            "fertilizer_advice": "Unable to calculate fertilizer data.",
            "irrigation": "OFF", 
            "irrigation_label": "Error",
            "water_liters": 0,
            "health_score": 50
        }



if __name__ == "__main__":
    print("[AGRI_AI] Training models from scratch...")
    train_agri_models()
    
    # Test inference
    test_readings = {
        "nitrogen": 90, "phosphorus": 42, "potassium": 43,
        "air_temperature": 25, "humidity": 80, "ph": 6.5,
        "soil_moisture": 45, "salinity": 1.2
    }
    result = get_recommendations(test_readings)
    print(f"\nTest Results:")
    for k, v in result.items():
        print(f"  {k}: {v}")
