"""
Krishi_Kaar — Sensor Module (Production-Grade)

Supports two modes:
1. SIMULATION: Temporally-coherent mock data (gradual changes, correlated values)
2. ARDUINO: Live serial data from Arduino hardware

All sensors maintain state for realistic temporal progression.
"""
import random
import os
import time
import threading

# --- Attempt Arduino Serial Connection ---
import serial.tools.list_ports
_arduino = None
_arduino_lock = threading.Lock()

def auto_discover_port():
    """Automatically find the Arduino port if it isn't specified."""
    env_port = os.environ.get('ARDUINO_PORT', None)
    if env_port:
        return env_port
    
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        # Search for 'Arduino' in description or take first available COM port on Windows
        if "arduino" in p.description.lower() or "ch340" in p.description.lower():
            return p.device
            
    # Default to first available port if nothing else found
    if ports:
        return ports[0].device
    return None

ARDUINO_PORT = auto_discover_port()

if ARDUINO_PORT:
    try:
        import serial
        _arduino = serial.Serial(ARDUINO_PORT, 9600, timeout=0.5)
        time.sleep(2)
        print(f"[SENSORS] Plug-and-Play: Arduino connected on {ARDUINO_PORT}")
    except Exception as e:
        print(f"[SENSORS] Connection failed on {ARDUINO_PORT}: {e}")
        _arduino = None
else:
    print("[SENSORS] No hardware detected. Operating in Simulation/Manual mode.")


class SmoothedSensor:
    """Base sensor with temporal smoothing — values change gradually, not randomly."""
    def __init__(self, initial, min_val, max_val, max_delta, precision=2):
        self._value = initial
        self._min = min_val
        self._max = max_val
        self._delta = max_delta
        self._precision = precision

    def read(self):
        change = random.uniform(-self._delta, self._delta)
        # Slight mean-reversion to keep values centered
        center = (self._min + self._max) / 2
        reversion = (center - self._value) * 0.02
        self._value = max(self._min, min(self._max, self._value + change + reversion))
        return round(self._value, self._precision)

    def set(self, value):
        """Override with a real hardware reading."""
        self._value = max(self._min, min(self._max, value))


# --- Sensor Instances (Simulation Mode) ---
soil_moisture = SmoothedSensor(initial=55.0, min_val=15.0, max_val=95.0, max_delta=1.5)
soil_temperature = SmoothedSensor(initial=26.0, min_val=15.0, max_val=40.0, max_delta=0.3, precision=1)
air_temperature = SmoothedSensor(initial=28.0, min_val=12.0, max_val=48.0, max_delta=0.4, precision=1)
humidity = SmoothedSensor(initial=62.0, min_val=25.0, max_val=98.0, max_delta=1.0, precision=1)
tds = SmoothedSensor(initial=350.0, min_val=50.0, max_val=2500.0, max_delta=15.0, precision=1)
salinity = SmoothedSensor(initial=1.5, min_val=0.1, max_val=5.0, max_delta=0.08)
ultrasonic = SmoothedSensor(initial=250.0, min_val=5.0, max_val=400.0, max_delta=10.0)
ph = SmoothedSensor(initial=6.8, min_val=4.0, max_val=9.0, max_delta=0.1, precision=1)

# NPK sensors — correlated to each other (realistic soil nutrient profiles)
nitrogen = SmoothedSensor(initial=85.0, min_val=10.0, max_val=200.0, max_delta=2.0, precision=1)
phosphorus = SmoothedSensor(initial=45.0, min_val=5.0, max_val=150.0, max_delta=1.5, precision=1)
potassium = SmoothedSensor(initial=55.0, min_val=5.0, max_val=150.0, max_delta=1.5, precision=1)


def _read_arduino():
    """Attempt to read a line from Arduino: 'soil,temp,hum' format."""
    if _arduino is None:
        return None
    try:
        with _arduino_lock:
            # Flush old data, get latest
            while _arduino.in_waiting > 0:
                line = _arduino.readline().decode().strip()
            if not line:
                line = _arduino.readline().decode().strip()
            if line:
                parts = line.split(',')
                if len(parts) >= 4:
                    return {
                        'soil_raw': int(parts[0]),
                        'temperature': float(parts[1]),
                        'humidity': float(parts[2]),
                        'distance': float(parts[3])
                    }
    except Exception as e:
        print(f"[SENSORS] Arduino read error: {e}")
    return None


def control_pump(status):
    """Send control command to Arduino: '1' for ON, '0' for OFF."""
    global _arduino
    if _arduino is None:
        return False
    try:
        with _arduino_lock:
            cmd = b'1' if status == "ON" else b'0'
            _arduino.write(cmd)
            # Small delay to ensure command is processed
            time.sleep(0.1)
            return True
    except Exception as e:
        print(f"[SENSORS] Arduino control error: {e}")
        return False


# --- Operational State ---
use_simulation = False
manual_data = {
    "soil_moisture": 45.0,
    "air_temperature": 25.0,
    "humidity": 55.0
}

def set_simulation(active):
    global use_simulation
    use_simulation = active

def set_manual_data(moisture, temp, humidity_val):
    global manual_data
    manual_data["soil_moisture"] = float(moisture)
    manual_data["air_temperature"] = float(temp)
    manual_data["humidity"] = float(humidity_val)

def get_all_readings(source_mode="Hardware"):
    """
    Return a complete sensor reading dict. 
    source_mode: 'Hardware' or 'Manual'
    """
    
    # HW Path
    hw = _read_arduino()
    if hw:
        # Map Arduino soil value (0-1023) to percent
        soil_pct = round((1023 - hw['soil_raw']) / 1023 * 100, 2)
        soil_moisture.set(soil_pct)
        air_temperature.set(hw['temperature'])
        humidity.set(hw['humidity'])
        ultrasonic.set(hw['distance'])
    
    # Prepare result
    res = {
        "soil_moisture": soil_moisture.read() if use_simulation else (soil_moisture._value if hw else manual_data["soil_moisture"]),
        "air_temperature": air_temperature.read() if use_simulation else (air_temperature._value if hw else manual_data["air_temperature"]),
        "humidity": humidity.read() if use_simulation else (humidity._value if hw else manual_data["humidity"]),
        "soil_temperature": soil_temperature.read() if use_simulation else soil_temperature._value,
        "tds": tds.read() if use_simulation else tds._value,
        "salinity": salinity.read() if use_simulation else salinity._value,
        "distance": ultrasonic.read() if use_simulation else ultrasonic._value,
        "nitrogen": nitrogen.read() if use_simulation else nitrogen._value,
        "phosphorus": phosphorus.read() if use_simulation else phosphorus._value,
        "potassium": potassium.read() if use_simulation else potassium._value,
        "ph": ph.read() if use_simulation else ph._value,
    }
    
    if source_mode == "Manual":
        if not use_simulation:
            res["soil_moisture"] = manual_data["soil_moisture"]
            res["air_temperature"] = manual_data["air_temperature"]
            res["humidity"] = manual_data["humidity"]
        res["source"] = "simulation" if use_simulation else "manual"
    else:
        # Hardware mode
        if use_simulation:
            res["source"] = "simulation"
        elif hw:
            res["source"] = "arduino"
        else:
            res["source"] = "disconnected"
            
    return res
