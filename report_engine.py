"""
Krishi_Kaar — V4 Multi-Theme Report Engine
Generates premium Dashboard-style PDF reports with Dark and Light modes.
"""
import os
from fpdf import FPDF
from datetime import datetime
from config import Config
import translations

class KrishiReport(FPDF):
    def __init__(self, theme='light', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.theme = theme
        # Theme Palette
        if self.theme == 'dark':
            self.bg_color = (15, 23, 42)    # Slate 900
            self.card_color = (30, 41, 59)  # Slate 800
            self.text_main = (248, 250, 252) # Slate 50
            self.text_dim = (148, 163, 184)  # Slate 400
            self.border_color = (51, 65, 85) # Slate 700
        else:
            self.bg_color = (255, 255, 255) # White
            self.card_color = (248, 250, 252)# Slate 50
            self.text_main = (15, 23, 42)   # Slate 900
            self.text_dim = (71, 85, 105)   # Slate 600
            self.border_color = (226, 232, 240)# Slate 200

        self.accent_color = (16, 185, 129) # Emerald 500
        self.blue_accent = (59, 130, 246)  # Blue 500

    def header(self):
        # Full page background for Dark Mode
        if self.theme == 'dark':
            self.set_fill_color(*self.bg_color)
            self.rect(0, 0, 210, 297, 'F')

        # Header Banner
        self.set_fill_color(*self.accent_color)
        self.rect(0, 0, 210, 35, 'F')
        
        self.set_y(8)
        self.set_font("NotoSans", "B", 24)
        self.set_text_color(255, 255, 255)
        self.cell(0, 12, "KRISHI KAAR", ln=True, align='C')
        
        self.set_font("NotoSans", "", 9)
        self.cell(0, 5, "NEXT-GEN PRECISION AGRICULTURE SYSTEM", ln=True, align='C')
        
        self.set_y(26)
        self.set_font("NotoSans", "I", 8)
        self.cell(0, 5, f"ANALYTICS GENERATED: {datetime.now().strftime('%Y-%m-%d | %H:%M:%S')}", ln=True, align='C')
        self.ln(12)

    def draw_card(self, x, y, w, h, title=""):
        # Card Background
        self.set_fill_color(*self.card_color)
        self.set_draw_color(*self.border_color)
        self.rect(x, y, w, h, 'FD')
        
        # Card Header
        if title:
            self.set_xy(x + 5, y + 3)
            self.set_font("NotoSans", "B", 8)
            self.set_text_color(*self.text_dim)
            self.cell(w-10, 5, title.upper(), ln=True)
            self.line(x + 5, y + 8, x + w - 5, y + 8)

    def footer(self):
        self.set_y(-15)
        self.set_font("NotoSans", "I", 8)
        self.set_text_color(*self.text_dim)
        self.cell(0, 10, f"Page {self.page_no()} | AI Verified Intelligence Report | Theme: {self.theme.upper()}", align='C')

def generate_pdf(user_data, sensor_data, ai_data, lang='en', theme='light'):
    t = translations.translations.get(lang, translations.translations['en'])
    pdf = KrishiReport(theme=theme)
    
    # Fonts
    font_path = os.path.join(Config.DATA_DIR, "NotoSans-Regular.ttf")
    if os.path.exists(font_path):
        pdf.add_font("NotoSans", "", font_path)
        pdf.add_font("NotoSans", "B", font_path)
        pdf.add_font("NotoSans", "I", font_path)
    else:
        pdf.add_font("NotoSans", "", "arial") 

    pdf.add_page()
    
    # --- 1. Farmer Context ---
    pdf.set_y(40)
    pdf.draw_card(10, pdf.get_y(), 190, 25, t.get('farm_config', 'System Context'))
    
    pdf.set_xy(15, pdf.get_y() + 10)
    pdf.set_font("NotoSans", "B", 10)
    pdf.set_text_color(*pdf.text_main)
    pdf.cell(30, 8, f"{t.get('lbl_name', 'Farmer')}:")
    pdf.set_font("NotoSans", "", 10)
    pdf.cell(60, 8, str(user_data.get('name', 'N/A')))
    
    pdf.set_font("NotoSans", "B", 10)
    pdf.cell(30, 8, f"{t.get('farm_size', 'Farm Size')}:")
    pdf.set_font("NotoSans", "", 10)
    pdf.cell(60, 8, f"{user_data.get('farm_acres', 0)} Acres", ln=True)
    
    pdf.set_x(15)
    pdf.set_font("NotoSans", "B", 10)
    pdf.cell(30, 8, f"{t.get('soil', 'Soil')}:")
    pdf.set_font("NotoSans", "", 10)
    pdf.cell(60, 8, str(user_data.get('soil_type', 'N/A')))
    
    # --- 2. Live Telemetry Matrix ---
    pdf.ln(12)
    start_y = pdf.get_y()
    
    vitals = [
        (t.get('moisture', 'Moisture'), f"{sensor_data['soil_moisture']}%"),
        (t.get('air_temp', 'Temperature'), f"{sensor_data['air_temperature']} C"),
        (t.get('humidity', 'Humidity'), f"{sensor_data['humidity']}%"),
        ("N-P-K Level", f"{sensor_data['nitrogen']}-{sensor_data['phosphorus']}-{sensor_data['potassium']}"),
        ("Soil pH", str(sensor_data['ph'])),
        ("TDS (Water)", f"{sensor_data['tds']} ppm")
    ]
    
    for i, (label, val) in enumerate(vitals):
        col, row = i % 2, i // 2
        x, y = 10 + (col * 98), start_y + (row * 18)
        pdf.draw_card(x, y, 92, 15)
        pdf.set_xy(x + 5, y + 2)
        pdf.set_font("NotoSans", "B", 8)
        pdf.set_text_color(*pdf.text_dim)
        pdf.cell(0, 5, label.upper(), ln=True)
        pdf.set_xy(x + 5, y + 7)
        pdf.set_font("NotoSans", "B", 11)
        pdf.set_text_color(*pdf.accent_color)
        pdf.cell(82, 6, str(val), align='L')
        
    pdf.set_y(start_y + 60)

    # --- 3. AI Insights Card ---
    pdf.draw_card(10, pdf.get_y(), 190, 85, t.get('ai_assistant', 'AI Recommendation Engine'))
    
    # Crop Match
    pdf.set_xy(15, pdf.get_y() + 8)
    pdf.set_font("NotoSans", "B", 10)
    pdf.set_text_color(*pdf.text_main)
    pdf.cell(0, 8, f"{t.get('top_crops', 'Recommended Biological Matches')}:")
    
    # Primary Match Banner
    primary = ai_data.get('primary_crop', {})
    if primary:
        pdf.set_xy(140, pdf.get_y())
        pdf.set_font("NotoSans", "B", 7)
        pdf.set_fill_color(*pdf.accent_color)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(50, 6, "HIGHLY RECOMMENDED", ln=True, align='C', fill=True)
    else:
        pdf.ln(8)
        
    pdf.set_x(15)
    pdf.set_font("NotoSans", "", 9)
    pdf.set_text_color(*pdf.text_main)
    
    detailed_crops = ai_data.get('top_crops_detailed', [])
    crop_str = "   |   ".join([f"{c['name']} (Score: {c['fusion_score']}%)" for c in detailed_crops[:3]])
    pdf.multi_cell(180, 8, crop_str, align='C')
    
    # Fertilizer Expert Advisory
    pdf.ln(2)
    pdf.set_x(15)
    pdf.set_font("NotoSans", "B", 10)
    pdf.set_text_color(*pdf.blue_accent)
    pdf.cell(0, 8, f"{t.get('fertilizer', 'Fertilizer Guide')}: {ai_data.get('fertilizer', 'N/A')}", ln=True)
    
    pdf.set_x(15)
    pdf.set_font("NotoSans", "I", 8)
    pdf.set_text_color(*pdf.text_dim)
    pdf.multi_cell(180, 5, ai_data.get('fertilizer_advice', 'Balanced profile maintained.'))
    
    # Irrigation Commands
    pdf.ln(5)
    pdf.set_x(15)
    pdf.set_draw_color(*pdf.blue_accent)
    pdf.set_fill_color(*(pdf.accent_color if ai_data.get('irrigation') == 'ON' else pdf.card_color))
    pdf.rect(15, pdf.get_y(), 180, 45, 'D')
    
    pdf.set_y(pdf.get_y() + 5)
    pdf.set_x(20)
    pdf.set_font("NotoSans", "B", 12)
    pdf.set_text_color(*pdf.blue_accent)
    pdf.cell(90, 10, f"SYSTEM COMMAND: {ai_data.get('irrigation', 'STANDBY')}")
    pdf.set_text_color(*pdf.text_main)
    pdf.cell(85, 10, f"TARGET: {ai_data.get('water_liters', 0):,} L", align='R', ln=True)
    
    pdf.set_x(20)
    pdf.set_font("NotoSans", "I", 10)
    pdf.set_text_color(*pdf.text_dim)
    pdf.multi_cell(170, 7, ai_data.get('irr_advice', 'System stabilized.'))

    # --- 4. The Engineering Team Signature Card ---
    pdf.set_y(pdf.get_y() + 25)
    # Slate background for credits
    pdf.set_fill_color(30, 41, 59)
    pdf.rect(10, pdf.get_y(), 190, 40, 'F')
    
    pdf.set_y(pdf.get_y() + 5)
    pdf.set_font("NotoSans", "B", 10)
    pdf.set_text_color(*pdf.accent_color)
    pdf.cell(0, 8, "EXECUTIVE PRODUCTION & ENGINEERING TEAM", ln=True, align='C')
    
    pdf.set_font("NotoSans", "B", 12)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "Kartikey Tiwari      |      Ujjwal Tiwari      |      Neha Yadav", align='C', ln=True)
    
    pdf.set_font("NotoSans", "I", 8)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 8, "Official Krishi Kaar Intelligence Suite v4.0.0 Alpha", align='C')

    # Save
    ts = datetime.now().strftime("%H%M%S")
    output_path = os.path.join(Config.DATA_DIR, f"report_{lang}_{theme}_{ts}.pdf")
    pdf.output(output_path)
    return output_path
