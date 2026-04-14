"""
Krishi_Kaar — Centralized Configuration
All system-wide settings in one place. Override via environment variables.
"""
import os
import secrets

class Config:
    # --- Flask ---
    SECRET_KEY = os.environ.get('KRISHI_SECRET_KEY', secrets.token_hex(32))
    
    # --- Database ---
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
    MONGO_DB_NAME = os.environ.get('MONGO_DB', 'krishi_kaar_db')
    MONGO_TIMEOUT_MS = 2000
    # Base paths relative to src root
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MODEL_DIR = os.path.join(BASE_DIR, 'models')
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    
    # SQLite fallback when MongoDB is unavailable
    SQLITE_PATH = os.path.join(DATA_DIR, 'user.db')
    LOGIN_HISTORY_FILE = os.path.join(DATA_DIR, 'login_history.csv')
    
    # --- Arduino / Sensors ---
    ARDUINO_PORT = os.environ.get('ARDUINO_PORT', None)  # e.g. 'COM5' or '/dev/ttyUSB0'
    ARDUINO_BAUD = int(os.environ.get('ARDUINO_BAUD', '9600'))
    SENSOR_POLL_INTERVAL = float(os.environ.get('SENSOR_POLL_SEC', '3'))
    VISION_POLL_INTERVAL = float(os.environ.get('VISION_POLL_SEC', '5'))
    
    # --- AI Models ---
    AGRI_MODEL_FILE = os.path.join(MODEL_DIR, 'agri_ai_model.pkl')
    WATER_MODEL_FILE = os.path.join(MODEL_DIR, 'water_model.pkl')
    CROP_CNN_FILE = os.path.join(MODEL_DIR, 'crop_cnn_model.h5')
    PRESENCE_CNN_FILE = os.path.join(MODEL_DIR, 'presence_cnn_model.h5')
    
    # --- Weather ---
    WEATHER_API_KEY = os.environ.get('OWM_API_KEY', None)
    WEATHER_CITY = os.environ.get('WEATHER_CITY', 'Bangalore')
    WEATHER_CACHE_SEC = 600  # 10 minute cache
    
    # --- Server ---
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', '5000'))
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    # --- Sensor History Limits ---
    MAX_MONGO_HISTORY = 1000
    MAX_MEMORY_HISTORY = 50
    MAX_SQLITE_HISTORY = 5000
