"""
Data Schema and Configuration Module for Head Lettuce Research Project.
Defines experimental design, column mappings (Thai <-> English),
soil chemical parameters, data dictionaries, metric categories, and Thai tooltips.
"""

import datetime
from typing import List, Dict, Optional, Tuple

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

VARIETIES: List[str] = ["Green Moon", "Fame"]

# Treatments belonging to each (variety, lighting-condition) cell of the
# 2 (variety) x 2 (binary lighting) experimental design. Used by the
# comparison-mode helper below to map raw treatments to logical groups.
_TREATMENT_BY_VARIETY_LIGHT: Dict[Tuple[str, str], List[str]] = {
    ("Green Moon", "Control"): ["Control_GM"],
    ("Green Moon", "LED"):     ["LED_GM"],
    ("Fame", "Control"):       ["Control_F"],
    ("Fame", "LED"):           ["LED_F (1)", "LED_F (2)"],
}


def build_comparison_groups(
    mode: str,
    variety: Optional[str] = None,
    lighting_filter: Optional[str] = None,
    merge_led_f: bool = True,
) -> Dict[str, object]:
    """
    Build a logical comparison-group specification for the Statistical Analytics tab.

    Parameters
    ----------
    mode : str
        One of:
          - "all"     : use all 5 raw treatments (default behaviour, two-way ANOVA)
          - "within"  : compare Control vs LED within a single variety
          - "cross"   : compare varieties under a chosen lighting condition
    variety : str, optional
        Required when mode == "within". One of VARIETIES.
    lighting_filter : str, optional
        Required when mode == "cross". One of "All", "Control", "LED".
    merge_led_f : bool
        When True, the two Fame LED plots ("LED_F (1)", "LED_F (2)") are
        combined into a single logical "LED" group. When False, they are
        kept as separate groups (LED Plot 1 / LED Plot 2). Only relevant
        for Fame in "within" mode and for LED in "cross" mode.

    Returns
    -------
    dict with keys:
        - treatments: list of raw treatments included in the comparison
        - group_map : {raw_treatment -> logical_group_label}
        - group_col : column name to add to the analysis DataFrame
                      ("comparison_group")
        - group_label : Thai/English axis label for the group column
        - summary : human-readable description of the active comparison
        - test_kind : "two_way_anova" | "t_test" | "one_way_anova"
        - n_groups : number of distinct logical groups
    """
    if mode == "all":
        return {
            "treatments": list(TREATMENTS),
            "group_map": {t: t for t in TREATMENTS},
            "group_col": "treatment",
            "group_label": "กลุ่มการทดลอง (Treatment)",
            "summary": "เปรียบเทียบทุกแปลงทดลอง (5 แปลง) — Two-Way ANOVA (Variety × Lighting) + Tukey HSD",
            "test_kind": "two_way_anova",
            "n_groups": len(TREATMENTS),
        }

    if mode == "within":
        if variety not in VARIETIES:
            raise ValueError(f"variety must be one of {VARIETIES} for within-mode")
        ctrl_treatments = _TREATMENT_BY_VARIETY_LIGHT[(variety, "Control")]
        led_treatments = _TREATMENT_BY_VARIETY_LIGHT[(variety, "LED")]
        treatments = ctrl_treatments + led_treatments

        if variety == "Fame" and not merge_led_f:
            # Keep LED Plot 1 and LED Plot 2 separate -> 3 groups
            group_map = {
                "Control_F": "Control",
                "LED_F (1)": "LED Plot 1",
                "LED_F (2)": "LED Plot 2",
            }
            summary = (
                f"เปรียบเทียบภายในพันธุ์ {variety}: Control vs LED Plot 1 vs LED Plot 2 "
                "(3 กลุ่ม) — One-Way ANOVA + Tukey HSD"
            )
            test_kind = "one_way_anova"
        else:
            # Combine LED plots (or Green Moon has only one LED plot anyway)
            group_map = {t: "Control" for t in ctrl_treatments}
            group_map.update({t: "LED" for t in led_treatments})
            summary = (
                f"เปรียบเทียบภายในพันธุ์ {variety}: Control vs LED "
                f"(2 กลุ่ม) — Welch t-test + Cohen's d"
            )
            test_kind = "t_test"

        return {
            "treatments": treatments,
            "group_map": group_map,
            "group_col": "comparison_group",
            "group_label": f"สภาพแสง ({variety})",
            "summary": summary,
            "test_kind": test_kind,
            "n_groups": len(set(group_map.values())),
        }

    if mode == "cross":
        if lighting_filter not in ("All", "Control", "LED"):
            raise ValueError("lighting_filter must be 'All', 'Control' or 'LED' for cross-mode")

        if lighting_filter == "All":
            # Full 2x2 factorial -> two-way ANOVA on variety x binary lighting
            treatments = list(TREATMENTS)
            group_map = {t: t for t in TREATMENTS}
            return {
                "treatments": treatments,
                "group_map": group_map,
                "group_col": "treatment",
                "group_label": "กลุ่มการทดลอง (Treatment)",
                "summary": "เปรียบเทียบข้ามพันธุ์ทุกเงื่อนไขแสง (2×2) — Two-Way ANOVA (Variety × Lighting)",
                "test_kind": "two_way_anova",
                "n_groups": len(set(group_map.values())),
            }

        # Single lighting condition: compare Green Moon vs Fame
        gm_treatments = _TREATMENT_BY_VARIETY_LIGHT[("Green Moon", lighting_filter)]
        fame_treatments = _TREATMENT_BY_VARIETY_LIGHT[("Fame", lighting_filter)]
        treatments = gm_treatments + fame_treatments

        if lighting_filter == "LED" and not merge_led_f:
            # Keep Fame LED plots separate -> 3 groups (GM-LED, Fame-LED-1, Fame-LED-2)
            group_map = {
                "LED_GM": "Green Moon (LED)",
                "LED_F (1)": "Fame (LED Plot 1)",
                "LED_F (2)": "Fame (LED Plot 2)",
            }
            summary = (
                "เปรียบเทียบข้ามพันธุ์ภายใต้แสง LED: Green Moon vs Fame (Plot 1) vs Fame (Plot 2) "
                "(3 กลุ่ม) — One-Way ANOVA + Tukey HSD"
            )
            test_kind = "one_way_anova"
        else:
            group_map = {t: "Green Moon" for t in gm_treatments}
            group_map.update({t: "Fame" for t in fame_treatments})
            summary = (
                f"เปรียบเทียบข้ามพันธุ์ภายใต้แสง {lighting_filter}: Green Moon vs Fame "
                "(2 กลุ่ม) — Welch t-test + Cohen's d"
            )
            test_kind = "t_test"

        return {
            "treatments": treatments,
            "group_map": group_map,
            "group_col": "comparison_group",
            "group_label": f"สายพันธุ์ (แสง {lighting_filter})",
            "summary": summary,
            "test_kind": test_kind,
            "n_groups": len(set(group_map.values())),
        }

    raise ValueError(f"Unknown comparison mode: {mode!r}")

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
    # NOTE: SOIL_ENV_METRICS intentionally excluded — these columns live in the
    # separate env_data DataFrame and are not present in experiment_data, so
    # including them in the analytics dropdown produced empty results when
    # selected. They are still available in the Pearson correlation heatmap
    # (which joins env_data into experiment_data on week_no).
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
