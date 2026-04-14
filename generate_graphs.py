import matplotlib.pyplot as plt
import numpy as np

# Data Simulation
days = np.arange(1, 8)
soil_moisture = [45, 42, 40, 38, 60, 58, 55] # Dip then rain/water
temp = [28, 29, 30, 31, 27, 26, 28]

def generate_graphs():
    # 1. Soil Moisture vs Time
    plt.figure(figsize=(10, 5))
    plt.plot(days, soil_moisture, marker='o', color='green', linestyle='-', linewidth=2)
    plt.title('Weekly Soil Moisture Levels')
    plt.xlabel('Day')
    plt.ylabel('Moisture (%)')
    plt.grid(True)
    plt.savefig('graph_soil_moisture.png')
    print("Generated graph_soil_moisture.png")

    # 2. Temperature Trend
    plt.figure(figsize=(10, 5))
    plt.plot(days, temp, marker='s', color='orange', linestyle='--', linewidth=2)
    plt.title('Weekly Temperature Variation')
    plt.xlabel('Day')
    plt.ylabel('Temperature (°C)')
    plt.grid(True)
    plt.savefig('graph_temperature.png')
    print("Generated graph_temperature.png")

    # 3. Model Accuracy Comparison (Bar Chart)
    models = ['MobileNetV2', 'Decision Tree']
    accuracy = [92, 95]
    
    plt.figure(figsize=(6, 4))
    plt.bar(models, accuracy, color=['blue', 'cyan'])
    plt.ylim(80, 100)
    plt.title('ML Model Accuracy Comparison')
    plt.ylabel('Accuracy (%)')
    plt.savefig('graph_model_accuracy.png')
    print("Generated graph_model_accuracy.png")

if __name__ == "__main__":
    try:
        generate_graphs()
        print("All graphs generated successfully.")
    except ImportError:
        print("Matplotlib not installed. Please run: pip install matplotlib")
