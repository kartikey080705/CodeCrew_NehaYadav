import os
import sys

# Mocking config and translations to test report_engine
class MockConfig:
    DATA_DIR = "c:\\Users\\KARTIKEY\\OneDrive\\Desktop\\Krishi_Kaar\\data"
    SENSOR_POLL_INTERVAL = 5

sys.modules['config'] = type('obj', (object,), {'Config': MockConfig})

import translations
import report_engine

user_data = {
    "name": "Kartikey Tiwari",
    "farm_acres": 12.5,
    "soil_type": "Black Soil",
    "location": "Lucknow, India"
}

sensor_data = {
    "soil_moisture": 45,
    "air_temperature": 32,
    "humidity": 60,
    "nitrogen": 80,
    "phosphorus": 40,
    "potassium": 50,
    "ph": 6.8,
    "tds": 250
}

ai_data = {
    "top_crops": ["Sugarcane", "Wheat", "Cotton"],
    "compatibility": {"Sugarcane": 94, "Wheat": 88, "Cotton": 82},
    "fertilizer": "Use NPK 19:19:19 for balanced growth.",
    "irrigation": "ON",
    "water_liters": 15000,
    "irr_advice": "Recommended watering at dusk to minimize evaporation. Total volume calculated for 12.5 acres."
}

try:
    path = report_engine.generate_pdf(user_data, sensor_data, ai_data, lang='en')
    print(f"SUCCESS: PDF generated at {path}")
except Exception as e:
    print(f"FAILURE: {e}")
