import streamlit as st
import serial
import pickle
import pandas as pd
import time

# Use full screen layout
st.set_page_config(layout="wide")

# Title
st.title("🌱 Smart Agriculture AI System")

# Load models
crop_model = pickle.load(open("../models/crop_model.pkl","rb"))
fert_model = pickle.load(open("../models/fertilizer_model.pkl","rb"))

# Connect Arduino
arduino = serial.Serial('COM5',9600)
time.sleep(2)

# Graph data
soil_data = []
temp_data = []
hum_data = []

# Layout columns
col1, col2, col3 = st.columns(3)

soil_placeholder = col1.empty()
temp_placeholder = col2.empty()
hum_placeholder = col3.empty()

chart1 = st.line_chart()
chart2 = st.line_chart()
chart3 = st.line_chart()

recommendation_box = st.empty()

while True:

    try:
        data = arduino.readline().decode().strip()

        soil,temp,hum = data.split(",")

        soil = int(soil)
        temp = float(temp)
        hum = float(hum)

        moisture = round((1023 - soil)/1023 * 100,2)

        # Dummy NPK values
        N = 90
        P = 40
        K = 40
        ph = 6.5
        rainfall = 100

        # Crop prediction
        crop_input = pd.DataFrame({
            "N":[N],
            "P":[P],
            "K":[K],
            "temperature":[temp],
            "humidity":[hum],
            "ph":[ph],
            "rainfall":[rainfall]
        })

        crop = crop_model.predict(crop_input)[0]

        # Fertilizer prediction
        fert_input = pd.DataFrame({
            "Temparature":[temp],
            "Humidity":[hum],
            "Moisture":[moisture],
            "Soil Type":[1],
            "Crop Type":[1],
            "Nitrogen":[N],
            "Potassium":[K],
            "Phosphorous":[P]
        })

        fertilizer = fert_model.predict(fert_input)[0]

        # Irrigation logic
        if crop == "rice":
            threshold = 70
        elif crop == "wheat":
            threshold = 50
        elif crop == "maize":
            threshold = 50
        elif crop == "blackgram":
            threshold = 40
        else:
            threshold = 45

        if moisture < threshold:
            irrigation = "Irrigation Required"
        else:
            irrigation = "No Irrigation Needed"

        # Update metrics
        soil_placeholder.metric("Soil Moisture (%)", moisture)
        temp_placeholder.metric("Temperature (°C)", temp)
        hum_placeholder.metric("Humidity (%)", hum)

        # Recommendations
        recommendation_box.markdown(
        f"""
        ### 🌾 AI Recommendations

        **Recommended Crop:** {crop}

        **Recommended Fertilizer:** {fertilizer}

        **Irrigation Advice:** {irrigation}
        """
        )

        # Update graph data
        soil_data.append(moisture)
        temp_data.append(temp)
        hum_data.append(hum)

        chart1.add_rows(pd.DataFrame({"Soil Moisture": [moisture]}))
        chart2.add_rows(pd.DataFrame({"Temperature": [temp]}))
        chart3.add_rows(pd.DataFrame({"Humidity": [hum]}))

        time.sleep(2)

    except:
        pass