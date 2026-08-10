"""
Data Schema and Configuration Module for Head Lettuce Research Project.
Defines experimental design, column mappings (Thai <-> English),
soil chemical parameters, data dictionaries, metric categories, and Thai tooltips.
"""

import datetime
from typing import List, Dict

START_DATE = datetime.date(2026, 8, 4)

TREATMENTS: List[str] = [
    "Control_GM",
    "LED_GM",
    "Control_F",
    "LED_F (1)",
    "LED_F (2)"
]

VARIETY_MAP: Dict[str, str] = {
    "Control_GM": "Green Moon",
    "LED_GM": "Green Moon",
    "Control_F": "Fame",
    "LED_F (1)": "Fame",
    "LED_F (2)": "Fame"
}

LIGHTING_MAP: Dict[str, str] = {
    "Control_GM": "Control",
    "LED_GM": "LED",
    "Control_F": "Control",
    "LED_F (1)": "LED Plot 1",
    "LED_F (2)": "LED Plot 2"
}

PLANT_IDS: List[str] = ["A2", "A5", "A7", "B3", "B5", "B6", "B8", "C4", "C6", "C9"]

# Bi-directional Mapping for Thai Excel Import/Export matching 04-08-69.xlsx
THAI_TO_ENG_COLUMNS: Dict[str, str] = {
    "หมายเลขต้น": "plant_id",
    "ความกว้างทรงพุ่ม (ซม.)": "canopy_width",
    "ความยาวทรงพุ่ม (ซม.)": "canopy_length",
    "ความสูงทรงพุ่ม (ซม.)": "canopy_height",
    "จำนวนใบ": "leaf_count",
    "มุมสี (Hue Angle)": "hue_angle",
    "Hue Angle": "hue_angle"
}

ENG_TO_THAI_COLUMNS: Dict[str, str] = {
    "plant_id": "หมายเลขต้น",
    "canopy_width": "ความกว้างทรงพุ่ม (ซม.)",
    "canopy_length": "ความยาวทรงพุ่ม (ซม.)",
    "canopy_height": "ความสูงทรงพุ่ม (ซม.)",
    "leaf_count": "จำนวนใบ",
    "hue_angle": "มุมสี (Hue Angle)"
}

WEEKLY_METRICS: Dict[str, str] = {
    "canopy_width": "Canopy Width (cm)",
    "canopy_length": "Canopy Length (cm)",
    "canopy_height": "Canopy Height (cm)",
    "leaf_count": "Leaf Count",
    "hue_angle": "Hue Angle (°)"
}

SOIL_ENV_METRICS: Dict[str, str] = {
    "temp_c": "Greenhouse Temp (°C)",
    "ppfd": "PPFD (μmol/m²/s)",
    "soil_ph": "Soil pH",
    "soil_ec": "Soil EC (dS/m)",
    "soil_om": "Soil Organic Matter (%)",
    "soil_total_n": "Soil Total Nitrogen (%)",
    "soil_avail_p": "Soil Avail. P (mg/kg)",
    "soil_avail_k": "Soil Avail. K (mg/kg)"
}

HARVEST_METRICS: Dict[str, str] = {
    "fresh_weight": "Fresh Weight (g)",
    "root_length": "Root Length (cm)",
    "core_length": "Core Length (cm)",
    "head_diameter": "Head Diameter (cm)",
    "head_firmness": "Head Firmness Index"
}

PHYTOCHEMICAL_METRICS: Dict[str, str] = {
    "chl_a": "Chlorophyll a (mg/g FW)",
    "chl_b": "Chlorophyll b (mg/g FW)",
    "total_chl": "Total Chlorophyll (mg/g FW)",
    "carotenoids": "Carotenoids (mg/g FW)",
    "total_phenolics": "Total Phenolics (mg GAE/g FW)"
}

ALL_ANALYSIS_METRICS: Dict[str, str] = {
    **WEEKLY_METRICS,
    **HARVEST_METRICS,
    **PHYTOCHEMICAL_METRICS,
    **SOIL_ENV_METRICS
}

# Detailed Thai Tooltips & Descriptions for Research Parameters
METRIC_TOOLTIPS: Dict[str, str] = {
    "canopy_width": "ความกว้างทรงพุ่ม (ซม.) - วัดระยะจากขอบใบที่กว้างที่สุดสองฝั่งของทรงพุ่มผักกาดหอม",
    "canopy_length": "ความยาวทรงพุ่ม (ซม.) - วัดแนวความยาวทรงพุ่มตั้งฉากกับความกว้าง",
    "canopy_height": "ความสูงทรงพุ่ม (ซม.) - วัดจากโคนต้นระดับผิวดินถึงยอดใบที่สูงที่สุด",
    "leaf_count": "จำนวนใบ (ใบ) - นับจำนวนใบจริงที่คลี่สมบูรณ์แล้ว",
    "hue_angle": "มุมสี Hue Angle (องศา) - ดัชนีวัดโทนสีของใบ (90°=เหลือง, 120°=เขียวสด)",
    "fresh_weight": "น้ำหนักสด (กรัม) - น้ำหนักสดของหัวผักกาดหอมหลังเก็บเกี่ยว",
    "root_length": "ความยาวราก (ซม.) - ความยาวจากโคนรากถึงปลายรากแก้วที่ยาวที่สุด",
    "core_length": "ความยาวแกนหัว (ซม.) - ความยาวของแกนลำต้นภายในหัวผักกาดหอม",
    "head_diameter": "เส้นผ่านศูนย์กลางหัว (ซม.) - ความกว้างของหัวผักกาดหอมที่เข้าหัวแล้ว",
    "head_firmness": "ดัชนีความแน่นหัว (1-5) - คะแนนประเมินระดับความแน่นอัดแน่นของหัวผักกาดหอม",
    "chl_a": "คลอโรฟิลล์ เอ (mg/g FW) - สารสีเขียวหลักในการสังเคราะห์แสง (คำนวณจาก OD663 & OD645)",
    "chl_b": "คลอโรฟิลล์ บี (mg/g FW) - สารสีเขียวช่วยรับพลังงานแสง (คำนวณจาก OD645 & OD663)",
    "total_chl": "คลอโรฟิลล์รวม (mg/g FW) - ผลรวมปริมาณคลอโรฟิลล์ เอ และ บี",
    "carotenoids": "แคโรทีนอยด์รวม (mg/g FW) - สารสีส้ม-เหลืองช่วยปกป้องแสงและต้านอนุมูลอิสระ",
    "total_phenolics": "สารประกอบฟีนอลิกรวม (mg GAE/g FW) - ปริมาณสารต้านอนุมูลอิสระที่วิเคราะห์ด้วย Folin-Ciocalteu",
    "temp_c": "อุณหภูมิโรงเรือน (°C) - ค่าอุณหภูมิอากาศเฉลี่ยภายในโรงเรือนปลูก",
    "ppfd": "ความเข้มแสงสังเคราะห์แสง PPFD (μmol/m²/s) - ปริมาณโฟตอนแสงช่วงสังเคราะห์แสง",
    "soil_ph": "ค่าความเป็นกรด-ด่างของดิน (pH) - ค่า pH ของดินปลูกผักกาดหอม",
    "soil_ec": "ค่าความนำไฟฟ้าของดิน EC (dS/m) - วัดปริมาณเกลือและธาตุอาหารละลายในดิน",
    "soil_om": "ปริมาณอินทรียวัตถุในดิน OM (%) - เปอร์เซ็นต์อินทรียวัตถุในดิน",
    "soil_total_n": "ไนโตรเจนรวมในดิน Total N (%) - ปริมาณธาตุอาหารไนโตรเจนในดิน",
    "soil_avail_p": "ฟอสฟอรัสที่เป็นประโยชน์ Avail. P (mg/kg) - ปริมาณฟอสฟอรัสที่พืชดูดซึมได้",
    "soil_avail_k": "โพแทสเซียมที่แลกเปลี่ยนได้ Avail. K (mg/kg) - ปริมาณโพแทสเซียมที่เป็นประโยชน์"
}
