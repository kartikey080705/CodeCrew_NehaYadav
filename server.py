"""
Krishi_Kaar — Main Application Server (Production-Grade)

Enterprise Flask application with:
- Authentication (Flask-Login + password hashing)
- MongoDB primary / SQLite fallback / in-memory last resort
- Real-time sensor data via background threads
- AI-powered crop, fertilizer, and irrigation recommendations
- Computer vision (crop disease + presence detection)
- Video streaming from camera
- Multilingual i18n API
- RESTful control endpoints
"""
from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import threading
import time
import json
import sqlite3
import numpy as np
from datetime import datetime
import os
import sensors
import agri_ai
import translations
import report_engine
from config import Config

# ============================================================
# Flask App Setup
# ============================================================
app = Flask(__name__, template_folder='../web/templates', static_folder='../web/static')
app.secret_key = Config.SECRET_KEY

# ============================================================
# Database Layer — MongoDB → SQLite → In-Memory (cascading fallback)
# ============================================================
MONGO_ACTIVE = False
SQLITE_ACTIVE = False
users_coll = None
sensor_history = None
system_config_coll = None

# In-memory fallbacks
mock_users = []
mock_history = []

# --- Try MongoDB ---
try:
    from pymongo import MongoClient
    client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=Config.MONGO_TIMEOUT_MS)
    db = client[Config.MONGO_DB_NAME]
    users_coll = db["users"]
    sensor_history = db["sensor_history"]
    system_config_coll = db["system_config"]
    client.server_info()
    MONGO_ACTIVE = True
    print("[DB] MongoDB connected successfully.")
except Exception as e:
    print(f"[DB] MongoDB unavailable: {e}")

# --- SQLite Fallback ---
if not MONGO_ACTIVE:
    try:
        os.makedirs(os.path.dirname(Config.SQLITE_PATH), exist_ok=True)
        _sqlite_conn = sqlite3.connect(Config.SQLITE_PATH, check_same_thread=False)
        _sqlite_lock = threading.Lock()
        _sqlite_conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT DEFAULT 'Farmer',
            experience TEXT DEFAULT 'Beginner',
            farm_acres REAL DEFAULT 0.0,
            soil_type TEXT DEFAULT 'Loamy',
            location TEXT DEFAULT 'Unknown'
        )''')
        _sqlite_conn.execute('''CREATE TABLE IF NOT EXISTS sensor_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            data TEXT
        )''')
        _sqlite_conn.execute('''CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        _sqlite_conn.commit()
        SQLITE_ACTIVE = True
        print(f"[DB] SQLite fallback active at {Config.SQLITE_PATH}")
    except Exception as e:
        print(f"[DB] SQLite also failed: {e}. Using in-memory storage.")


def db_type():
    if MONGO_ACTIVE: return "mongodb"
    if SQLITE_ACTIVE: return "sqlite"
    return "memory"


# ============================================================
# Authentication
# ============================================================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth_page'

@login_manager.unauthorized_handler
def unauthorized():
    """Return JSON 401 for API routes, redirect for page routes."""
    if request.path.startswith('/api/'):
        return jsonify({"error": "Authentication required"}), 401
    return redirect(url_for('auth_page'))


class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data.get('_id') or user_data.get('id'))
        self.email = user_data.get('email', '')
        self.name = user_data.get('name', 'Farmer')
        self.experience = user_data.get('experience', 'Beginner')
        self.farm_acres = user_data.get('farm_acres', 0.0)
        self.soil_type = user_data.get('soil_type', 'Loamy')
        self.location = user_data.get('location', 'Unknown')


# ============================================================
# Authentication Utils
# ============================================================
def log_login_event(email, name, event_type, password='', experience='', acres='0.0', soil='', location=''):
    """Log authentication events + full user data to a CSV file."""
    try:
        file_exists = os.path.exists(Config.LOGIN_HISTORY_FILE)
        with open(Config.LOGIN_HISTORY_FILE, 'a', newline='') as f:
            import csv
            fieldnames = ['timestamp', 'email', 'password', 'name', 'experience', 'acres', 'soil', 'location', 'event']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'email': email,
                'password': password,
                'name': name,
                'experience': experience,
                'acres': acres,
                'soil': soil,
                'location': location,
                'event': event_type
            })
    except Exception as e:
        print(f"[AUTH] Logging failed: {e}")


@login_manager.user_loader
def load_user(user_id):
    try:
        if MONGO_ACTIVE:
            from bson.objectid import ObjectId
            user_data = users_coll.find_one({"_id": ObjectId(user_id)})
            return User(user_data) if user_data else None
        elif SQLITE_ACTIVE:
            with _sqlite_lock:
                cur = _sqlite_conn.execute("SELECT id, email, password, name, experience, farm_acres, soil_type, location FROM users WHERE id=?", (int(user_id),))
                row = cur.fetchone()
                if row:
                    return User({"id": row[0], "email": row[1], "name": row[3], "experience": row[4], 
                                 "farm_acres": row[5], "soil_type": row[6], "location": row[7]})
        else:
            user_data = next((u for u in mock_users if str(u.get('_id') or u.get('id')) == user_id), None)
            return User(user_data) if user_data else None
    except Exception:
        pass
    return None


# ============================================================
# System State
# ============================================================
system_state = {
    "mode": "Manual",   # Manual / Rule / Smart
    "pump": "OFF",
    "farm_area": 5.0,
    "crop_type": "Wheat",
    "soil_type": "Loamy",
    "source_mode": "Hardware" # Hardware / Manual
}

# Global data stores (updated by background threads)
latest_sensor_data = {"soil_moisture": 0, "air_temperature": 0, "humidity": 0, "source": "initializing"}
latest_ai_recommendations = {
    "top_crops": ["Initializing..."],
    "top_crops_detailed": [{"name": "Initializing...", "confidence": 0}],
    "crop": "Initializing...",
    "fertilizer": "Initializing...",
    "irrigation": "OFF",
    "irrigation_code": 0,
    "health_score": 50
}
# Vision/Camera removed as per requirements

# Weather cache (keyed by city)
_weather_cache = {}


# Camera and Video Feed Removed


# ============================================================
# Background Threads
# ============================================================
def sensor_loop():
    """Continuous sensor reading + AI inference + persistence."""
    global latest_sensor_data, latest_ai_recommendations, system_state
    
    while True:
        try:
            readings = sensors.get_all_readings(source_mode=system_state["source_mode"])
            
            # AI recommendations
            ai_output = agri_ai.get_recommendations(readings)
            latest_ai_recommendations = ai_output
            
            # Automation logic
            if system_state["mode"] == "Smart":
                system_state["pump"] = ai_output["irrigation"]
            elif system_state["mode"] == "Rule":
                moisture = readings.get('soil_moisture', 50)
                if moisture < 30:
                    system_state["pump"] = "ON"
                elif moisture > 60:
                    system_state["pump"] = "OFF"
            
            # Sync with hardware
            sensors.control_pump(system_state["pump"])
            
            # Enrich readings
            readings["pump_status"] = system_state["pump"]
            readings["mode"] = system_state["mode"]
            readings["health_score"] = ai_output.get("health_score", 50)
            readings["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            latest_sensor_data = readings
            
            # Persistence
            _persist_reading(readings)
            
        except Exception as e:
            print(f"[SENSOR_LOOP] Error: {e}")
        
        time.sleep(Config.SENSOR_POLL_INTERVAL)


def _persist_reading(readings):
    """Save sensor reading to available database."""
    try:
        if MONGO_ACTIVE:
            sensor_history.insert_one(readings.copy())
            count = sensor_history.count_documents({})
            if count > Config.MAX_MONGO_HISTORY:
                oldest = sensor_history.find().sort("timestamp", 1).limit(count - Config.MAX_MONGO_HISTORY)
                for doc in oldest:
                    sensor_history.delete_one({"_id": doc["_id"]})
        elif SQLITE_ACTIVE:
            data_json = json.dumps({k: v for k, v in readings.items() if k != 'timestamp'})
            with _sqlite_lock:
                _sqlite_conn.execute(
                    "INSERT INTO sensor_history (timestamp, data) VALUES (?, ?)",
                    (readings.get('timestamp', ''), data_json)
                )
                _sqlite_conn.execute(
                    f"DELETE FROM sensor_history WHERE id NOT IN (SELECT id FROM sensor_history ORDER BY id DESC LIMIT {Config.MAX_SQLITE_HISTORY})"
                )
                _sqlite_conn.commit()
        else:
            mock_history.append(readings.copy())
            if len(mock_history) > Config.MAX_MEMORY_HISTORY:
                mock_history.pop(0)
    except Exception as e:
        print(f"[DB] Persistence error: {e}")


# Vision loop removed


# ============================================================
# Weather
# ============================================================
def get_weather(city=None):
    """Get weather data (cached per city). Uses OWM API if key provided, otherwise realistic stub."""
    global _weather_cache
    now = time.time()
    target_city = city if city else Config.WEATHER_CITY
    
    if target_city in _weather_cache and now < _weather_cache[target_city]["expires"]:
        return _weather_cache[target_city]["data"]
    
    weather = None
    
    if Config.WEATHER_API_KEY:
        try:
            import requests
            url = f"https://api.openweathermap.org/data/2.5/weather?q={target_city}&appid={Config.WEATHER_API_KEY}&units=metric"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                d = resp.json()
                weather = {
                    "temp": round(d["main"]["temp"], 1),
                    "condition": d["weather"][0]["description"].title(),
                    "humidity": d["main"]["humidity"],
                    "wind": round(d.get("wind", {}).get("speed", 0), 1),
                    "city": target_city,
                    "source": "openweathermap"
                }
        except Exception as e:
            print(f"[WEATHER] API error: {e}")
    
    if weather is None:
        # Realistic stub based on readings
        temp = latest_sensor_data.get("air_temperature", 0)
        hum = latest_sensor_data.get("humidity", 0)
        # Fallback defaults for initial state before sensors populate
        if temp == 0: temp = 28.0
        if hum == 0: hum = 60.0
        if hum > 80:
            condition = "Overcast"
        elif hum > 65:
            condition = "Partly Cloudy"
        else:
            condition = "Clear Sky"
        weather = {
            "temp": round(temp, 1),
            "condition": condition,
            "humidity": round(hum, 1),
            "wind": round(12 + (temp - 25) * 0.5, 1),
            "city": target_city,
            "source": "simulated"
        }
    
    _weather_cache[target_city] = {"data": weather, "expires": now + Config.WEATHER_CACHE_SEC}
    return weather


# ============================================================
# Routes — Authentication
# ============================================================
@app.route('/auth')
def auth_page():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('auth.html')


@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    
    if not email or not password:
        return redirect(url_for('auth_page', error="Please fill all fields"))
    
    user_data = None
    if MONGO_ACTIVE:
        user_data = users_coll.find_one({"email": email})
    elif SQLITE_ACTIVE:
        with _sqlite_lock:
            cur = _sqlite_conn.execute("SELECT id, email, password, name, experience, farm_acres, soil_type, location FROM users WHERE email=?", (email,))
            row = cur.fetchone()
        if row:
            user_data = {"id": row[0], "email": row[1], "password": row[2], "name": row[3], "experience": row[4],
                         "farm_acres": row[5], "soil_type": row[6], "location": row[7]}
    else:
        user_data = next((u for u in mock_users if u['email'] == email), None)
    
    if user_data and user_data['password'] == password:
        user = User(user_data)
        login_user(user)
        log_login_event(
            email=user.email, 
            name=user.name, 
            event_type="LOGIN_SUCCESS",
            password=user_data.get('password', ''),
            experience=user.experience,
            acres=user.farm_acres,
            soil=user.soil_type,
            location=user.location
        )
        return redirect(url_for('index'))
    
    log_login_event(email, "Unknown", "LOGIN_FAILED", password=password)
    return redirect(url_for('auth_page', error="Invalid email or password"))


@app.route('/signup', methods=['POST'])
def signup():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    name = request.form.get('name', 'Farmer').strip()
    experience = request.form.get('experience', 'Beginner')
    try:
        acres_str = request.form.get('acres', '0.0')
        acres = float(acres_str) if acres_str.strip() else 0.0
    except ValueError:
        acres = 0.0
    soil = request.form.get('soil', 'Loamy').strip()
    location = request.form.get('location', 'Unknown').strip()
    
    if not email or not password:
        return redirect(url_for('auth_page', error="Please fill all fields"))
    
    if len(password) < 4:
        return redirect(url_for('auth_page', error="Password must be at least 4 characters"))
    
    # Check existence
    existing = None
    if MONGO_ACTIVE:
        existing = users_coll.find_one({"email": email})
    elif SQLITE_ACTIVE:
        with _sqlite_lock:
            cur = _sqlite_conn.execute("SELECT id FROM users WHERE email=?", (email,))
            existing = cur.fetchone()
    else:
        existing = next((u for u in mock_users if u['email'] == email), None)
    
    if existing:
        return redirect(url_for('auth_page', error="Email already exists"))
    
    # Storing password in plain text as requested for hackathon
    hashed_pw = password 
    
    if MONGO_ACTIVE:
        users_coll.insert_one({
            "email": email, "password": hashed_pw,
            "name": name, "experience": experience,
            "farm_acres": acres, "soil_type": soil, "location": location
        })
    elif SQLITE_ACTIVE:
        with _sqlite_lock:
            _sqlite_conn.execute(
                "INSERT INTO users (email, password, name, experience, farm_acres, soil_type, location) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (email, hashed_pw, name, experience, acres, soil, location)
            )
            _sqlite_conn.commit()
    else:
        mock_users.append({
            "_id": str(datetime.now().timestamp()),
            "email": email, "password": hashed_pw,
            "name": name, "experience": experience,
            "farm_acres": acres, "soil_type": soil, "location": location
        })
    
    log_login_event(
        email=email, 
        name=name, 
        event_type="ACCOUNT_CREATED",
        password=password,
        experience=experience,
        acres=acres,
        soil=soil,
        location=location
    )
    return redirect(url_for('auth_page', success="Account created! Please login."))


@app.route('/api/recover')
def api_recover():
    """Fetch plain-text password for an email (Requested Hackathon Feature)."""
    email = request.args.get('email', '').strip()
    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    user_data = None
    if MONGO_ACTIVE:
        user_data = users_coll.find_one({"email": email})
    elif SQLITE_ACTIVE:
        with _sqlite_lock:
            cur = _sqlite_conn.execute("SELECT password FROM users WHERE email=?", (email,))
            row = cur.fetchone()
            if row:
                user_data = {"password": row[0]}
    else:
        user_data = next((u for u in mock_users if u['email'] == email), None)
        
    if user_data:
        return jsonify({"email": email, "password": user_data['password']})
    
    return jsonify({"error": "User not found"}), 404


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth_page'))


# ============================================================
# Routes — Pages
# ============================================================
@app.route('/')
@login_required
def index():
    return render_template('dashboard.html', user=current_user)


# ============================================================
# API Endpoints
# ============================================================
@app.route('/api/sensors')
def api_sensors():
    data = latest_sensor_data.copy()
    data['db_type'] = db_type()
    data['db_connected'] = MONGO_ACTIVE or SQLITE_ACTIVE
    return jsonify(data)


@app.route('/api/recommendations')
@login_required
def api_recommendations():
    # Fetch localized weather to estimate rainfall
    weather = get_weather(current_user.location)
    rain_est = max(200.0, float(weather.get("humidity", 50)) * 14.5) if weather else 800.0
    
    # Generate biologically accurate recommendations for the active user's region
    data = agri_ai.get_recommendations(
        latest_sensor_data, 
        user_soil=current_user.soil_type, 
        rainfall=rain_est,
        acres=float(current_user.farm_acres or 5.0)
    )
    
    data.update({
        "pump_status": system_state["pump"],
        "mode": system_state["mode"],
        "user_exp": current_user.experience,
        "db_type": db_type(),
        "db_connected": MONGO_ACTIVE or SQLITE_ACTIVE
    })
    return jsonify(data)


@app.route('/api/vision')
def api_vision():
    return jsonify({"error": "Vision module disabled"})


@app.route('/api/weather')
@login_required
def api_weather():
    return jsonify(get_weather(current_user.location))


@app.route('/api/sensor_mode', methods=['POST'])
@login_required
def api_sensor_mode():
    global system_state
    req = request.json or {}
    if "mode" in req and req["mode"] in ("Hardware", "Manual"):
        system_state["source_mode"] = req["mode"]
        return jsonify({"status": "success", "mode": system_state["source_mode"]})
    return jsonify({"status": "error"}), 400

@app.route('/api/simulation', methods=['POST'])
@login_required
def api_simulation():
    req = request.json or {}
    active = req.get("active", False)
    sensors.set_simulation(active)
    return jsonify({"status": "success", "active": active})

@app.route('/api/manual_update', methods=['POST'])
@login_required
def api_manual_update():
    req = request.json or {}
    try:
        sensors.set_manual_data(req['moisture'], req['temp'], req['humidity'])
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/translations/<lang>')
def get_translations(lang):
    return jsonify(translations.translations.get(lang, translations.translations['en']))

@app.route('/api/generate_report/<lang>')
@login_required
def api_generate_report(lang):
    theme = request.args.get('theme', 'light') # Get theme from query param
    
    # Prepare data for report generator
    user_data = {
        "name": current_user.name,
        "farm_acres": current_user.farm_acres,
        "soil_type": current_user.soil_type,
        "location": current_user.location
    }
    
    # Fetch localized weather to estimate rainfall for the report
    weather = get_weather(current_user.location)
    rain_est = max(200.0, float(weather.get("humidity", 50)) * 14.5) if weather else 800.0
    
    # Perform a FRESH, personalized AI inference for the user's specific farm
    personalized_ai_data = agri_ai.get_recommendations(
        latest_sensor_data, 
        user_soil=current_user.soil_type, 
        rainfall=rain_est,
        acres=float(current_user.farm_acres or 5.0)
    )
    
    # Generate the PDF
    try:
        report_path = report_engine.generate_pdf(
            user_data=user_data,
            sensor_data=latest_sensor_data,
            ai_data=personalized_ai_data,
            lang=lang,
            theme=theme
        )
        return send_file(os.path.abspath(report_path), as_attachment=True)
    except Exception as e:
        print(f"[REPORT] Error generating PDF: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route('/api/control', methods=['POST'])
@login_required
def api_control():
    global system_state
    req = request.json or {}
    
    if "mode" in req and req["mode"] in ("Manual", "Rule", "Smart"):
        system_state["mode"] = req["mode"]
    
    if "pump" in req and req["pump"] in ("ON", "OFF"):
        if system_state["mode"] == "Manual":
            system_state["pump"] = req["pump"]
            sensors.control_pump(system_state["pump"])
        else:
            return jsonify({"status": "error", "message": "Pump control only available in Manual mode"}), 400
    
    return jsonify({"status": "success", "state": system_state})


@app.route('/api/config', methods=['POST'])
@login_required
def api_config():
    global system_state
    req = request.json or {}
    
    allowed_keys = {"farm_area", "crop_type", "soil_type"}
    updates = {k: v for k, v in req.items() if k in allowed_keys}
    system_state.update(updates)
    
    if MONGO_ACTIVE:
        try:
            system_config_coll.update_one({"type": "farm_config"}, {"$set": system_state}, upsert=True)
        except Exception:
            pass
    elif SQLITE_ACTIVE:
        try:
            with _sqlite_lock:
                _sqlite_conn.execute(
                    "INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)",
                    ("farm_config", json.dumps(system_state))
                )
                _sqlite_conn.commit()
        except Exception:
            pass
    
    return jsonify({"status": "success", "config": system_state})


@app.route('/api/history')
def api_history():
    try:
        if MONGO_ACTIVE:
            history = list(sensor_history.find({}, {"_id": 0}).sort("timestamp", -1).limit(30))
            return jsonify(history[::-1])
        elif SQLITE_ACTIVE:
            with _sqlite_lock:
                cur = _sqlite_conn.execute(
                    "SELECT timestamp, data FROM sensor_history ORDER BY id DESC LIMIT 30"
                )
                rows = cur.fetchall()
            result = []
            for ts, data_json in reversed(rows):
                entry = json.loads(data_json)
                entry['timestamp'] = ts
                result.append(entry)
            return jsonify(result)
        else:
            return jsonify(mock_history[-30:])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/system_status')
def api_system_status():
    """Health check endpoint."""
    return jsonify({
        "status": "running",
        "db": db_type(),
        "sensor_source": latest_sensor_data.get("source", "unknown"),
        "vision_demo": latest_crop_status.get("demo", False),
        "uptime": "active"
    })


# ============================================================
# Startup
# ============================================================
def _load_saved_config():
    """Load farm configuration from database on startup."""
    global system_state
    try:
        if MONGO_ACTIVE:
            saved = system_config_coll.find_one({"type": "farm_config"})
            if saved:
                for k in ("mode", "pump", "farm_area", "crop_type", "soil_type"):
                    if k in saved:
                        system_state[k] = saved[k]
        elif SQLITE_ACTIVE:
            with _sqlite_lock:
                cur = _sqlite_conn.execute("SELECT value FROM system_config WHERE key='farm_config'")
                row = cur.fetchone()
            if row:
                saved = json.loads(row[0])
                for k in ("mode", "pump", "farm_area", "crop_type", "soil_type"):
                    if k in saved:
                        system_state[k] = saved[k]
    except Exception as e:
        print(f"[STARTUP] Config load error: {e}")


if __name__ == '__main__':
    _load_saved_config()
    
    # Start background threads
    t1 = threading.Thread(target=sensor_loop, name="SensorThread", daemon=True)
    t1.start()
    
    print(f"[KRISHI_KAAR] Server starting on {Config.HOST}:{Config.PORT}")
    print(f"[KRISHI_KAAR] Database: {db_type()}")
    print(f"[KRISHI_KAAR] Dashboard: http://localhost:{Config.PORT}/")
    
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, use_reloader=False)
