import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'src'))
import agri_ai
from config import Config

# Mock Config if needed
Config.DATA_DIR = os.path.join(os.getcwd(), 'data')
Config.AGRI_MODEL_FILE = os.path.join(os.getcwd(), 'data', 'agri_models.pkl')

test_readings = {
    "nitrogen": 85,
    "phosphorus": 45,
    "potassium": 55,
    "air_temperature": 30.4,
    "humidity": 66.8,
    "ph": 6.8,
    "soil_moisture": 15
}

# Run inference
result = agri_ai.get_recommendations(test_readings, user_soil="Alluvial Soils", rainfall=800.0)

print("\n--- AI Accuracy Validation ---")
print(f"Inputs: {test_readings}")
print(f"Primary Recommendation: {result['primary_crop']['name']} (Confidence: {result['primary_crop']['confidence']}%, Fusion: {result['primary_crop']['fusion_score']}%)")
print(f"Top 3: {result['top_crops']}")
print(f"Fertilizer: {result['fertilizer']}")
print(f"Advice: {result['fertilizer_advice']}")
