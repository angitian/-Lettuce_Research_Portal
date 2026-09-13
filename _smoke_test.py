"""Smoke test for the Streamlit app using AppTest (headless, no browser needed)."""
import traceback
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app.py", default_timeout=120)
at.run()

# 1. Check for exceptions
if at.exception:
    print("=== EXCEPTIONS FOUND ===")
    for e in at.exception:
        print(e.value)
        traceback.print_exception(e)
    raise SystemExit(1)

print("=== NO EXCEPTIONS - app runs OK ===")
print(f"tabs: {len(at.tabs)}")
print(f"buttons: {len(at.button)}")
print(f"multiselects: {len(at.multiselect)}")
print(f"selectboxes: {len(at.selectbox)}")
print(f"toggles: {len(at.toggle)}")
print(f"expanders: {len(at.expander)}")

# 2. Verify Tab 4 multiselect widgets exist
ms_labels = [m.label for m in at.multiselect]
assert any("Select Parameters" in l for l in ms_labels), f"Tab4 metric multiselect missing: {ms_labels}"
assert any("Pearson Correlation" in l for l in ms_labels), f"Correlation multiselect missing: {ms_labels}"
print("=== Tab 4 multiselect widgets verified ===")

# 3. Verify per-metric expanders exist
exp_labels = [e.label for e in at.expander]
assert len(exp_labels) >= 3, f"Expected per-metric expanders, got: {exp_labels}"
print("=== Per-metric collapsible expanders verified ===")

# 4. Verify Sidebar clear-data + confirm flow buttons exist
btn_labels = [b.label for b in at.button]
assert any("ล้างข้อมูลทั้งหมด" in l for l in btn_labels), "Clear-data button missing"
print("=== Sidebar clear button verified ===")

# 5. Verify no old manual save buttons remain
save_btn = [l for l in btn_labels if "บันทึก" in l and "ล้าง" not in l and "ยืนยัน" not in l]
print(f"manual save buttons remaining: {save_btn}")
assert all("บันทึก" not in l for l in btn_labels if "ล้าง" not in l and "ใช่" not in l), f"Manual save buttons still present: {save_btn}"
print("=== Auto-save cleanup verified (no manual save buttons) ===")

print("=== SMOKE TEST PASSED ===")

# =============================================================================
# 6. Unit tests — Pigment Concentration (mg/L) parser & merge
# =============================================================================
import os
import pandas as pd
import numpy as np
import modules.storage as storage

CONC_FILE = os.path.join(os.path.dirname(__file__), "concentration Control-GM.xlsx")
assert os.path.exists(CONC_FILE), f"Concentration test file missing: {CONC_FILE}"

with open(CONC_FILE, "rb") as f:
    conc_bytes = f.read()

# Simulate empty session_state for the week-fallback path
import streamlit as st
class _FakeSS:
    def __init__(self): self._d = {}
    def get(self, k, default=None): return self._d.get(k, default)
    def __contains__(self, k): return k in self._d
    def __getitem__(self, k): return self._d[k]
    def __setitem__(self, k, v): self._d[k] = v
_orig_ss = st.session_state
st.session_state = _FakeSS()

parsed, parse_msg = storage.parse_concentration_excel(conc_bytes, "concentration Control-GM.xlsx")
st.session_state = _orig_ss

# --- Regression test: experiment_data already populated (real-app scenario).
# This path previously raised UnboundLocalError: 'week_no' because the branch
# where record_date exists did not assign week_no.
class _FakeSS2:
    def __init__(self, d): self._d = d
    def get(self, k, default=None): return self._d.get(k, default)
    def __contains__(self, k): return k in self._d
    def __getitem__(self, k): return self._d[k]
    def __setitem__(self, k, v): self._d[k] = v

exp_with_data = pd.DataFrame({
    "week_no": [3, 4, 4],
    "record_date": ["2026-08-24", "2026-08-31", "2026-08-31"],
    "treatment": ["Control_GM", "Control_GM", "LED_GM"],
    "plant_id": ["A2", "A5", "A2"],
})
st.session_state = _FakeSS2({"experiment_data": exp_with_data})
parsed_with_data, parse_msg2 = storage.parse_concentration_excel(conc_bytes, "concentration Control-GM.xlsx")
st.session_state = _orig_ss

assert not parsed_with_data.empty, f"Parser failed with populated experiment_data: {parse_msg2}"
assert len(parsed_with_data) == 15, f"Expected 15 rows with populated experiment_data, got {len(parsed_with_data)}"
# Date fallback: latest harvest date in experiment_data = 2026-08-31
assert parsed_with_data["record_date"].iloc[0] == "2026-08-31", (
    f"Expected record_date 2026-08-31 (latest in experiment_data), got {parsed_with_data['record_date'].iloc[0]}"
)
# Week computed from date via _week_from_date: (2026-08-31 - 2026-08-04).days=27 -> round(27/7)+1 = 5
assert parsed_with_data["week_no"].iloc[0] == 5, (
    f"Expected week_no = 5 (computed from 2026-08-31), got {parsed_with_data['week_no'].iloc[0]}"
)
print("=== Regression: parser with populated experiment_data verified (date=2026-08-31, week=5, no UnboundLocalError) ===")

# 6a. Parser: 15 replicate rows, treatment = Control_GM
assert not parsed.empty, f"Parser returned empty df: {parse_msg}"
assert len(parsed) == 15, f"Expected 15 replicate rows, got {len(parsed)}"
assert parsed["treatment"].nunique() == 1, f"Expected 1 treatment, got {parsed['treatment'].nunique()}"
assert parsed["treatment"].iloc[0] == "Control_GM", f"Expected Control_GM, got {parsed['treatment'].iloc[0]}"
print(f"=== Parser verified: {len(parsed)} rows, treatment={parsed['treatment'].iloc[0]} ===")

# 6b. Mean ± SD of A5 matches Sheet1 (Chl_a ≈ 61.44 ± 22.05)
a5 = parsed[parsed["plant_id"] == "A5"]
a5_mean = a5["chl_a_mgL"].mean()
a5_std = a5["chl_a_mgL"].std()
assert abs(a5_mean - 61.44) < 0.5, f"A5 Chl_a mean {a5_mean} != 61.44"
assert abs(a5_std - 22.05) < 0.5, f"A5 Chl_a SD {a5_std} != 22.05"
print(f"=== A5 mean+/-SD verified: Chl_a = {a5_mean:.2f} +/- {a5_std:.2f} (expected 61.44 +/- 22.05) ===")

# 6c. Merge: overwrite on key match
row_old = pd.DataFrame([{
    "record_date": "2026-09-12", "week_no": 7, "treatment": "Control_GM",
    "variety": "Green Moon", "lighting": "Control", "plant_id": "A5",
    "replicate": "R1", "weight_g": 0.45, "chl_a_mgL": 80.0, "chl_b_mgL": 32.0,
    "total_chl_mgL": 114.0, "carotenoid_mgL": 6.4,
}])
row_new = pd.DataFrame([{
    "record_date": "2026-09-12", "week_no": 7, "treatment": "Control_GM",
    "variety": "Green Moon", "lighting": "Control", "plant_id": "A5",
    "replicate": "R1", "weight_g": 0.46, "chl_a_mgL": 99.0, "chl_b_mgL": 33.0,
    "total_chl_mgL": 132.0, "carotenoid_mgL": 7.0,
}])
merged_overwrite = storage.merge_concentration_data(row_old, row_new)
assert len(merged_overwrite) == 1, f"Overwrite merge should keep 1 row, got {len(merged_overwrite)}"
assert merged_overwrite.iloc[0]["chl_a_mgL"] == 99.0, "Overwrite did not take latest value"
print("=== Merge overwrite-on-match verified ===")

# 6d. Merge: append new treatment
row_other = pd.DataFrame([{
    "record_date": "2026-09-12", "week_no": 7, "treatment": "LED_GM",
    "variety": "Green Moon", "lighting": "LED", "plant_id": "A2",
    "replicate": "R1", "weight_g": 0.40, "chl_a_mgL": 70.0, "chl_b_mgL": 25.0,
    "total_chl_mgL": 95.0, "carotenoid_mgL": 5.0,
}])
merged_append = storage.merge_concentration_data(row_old, row_other)
assert len(merged_append) == 2, f"Append merge should yield 2 rows, got {len(merged_append)}"
assert set(merged_append["treatment"]) == {"Control_GM", "LED_GM"}, "Append merge treatments mismatch"
print("=== Merge append-new-treatment verified ===")

# 6e. apply_concentration_means_to_experiment
exp = pd.DataFrame([{
    "treatment": "Control_GM", "plant_id": "A5", "week_no": 7,
    "chl_a_mgL": np.nan, "chl_b_mgL": np.nan, "total_chl_mgL": np.nan, "carotenoid_mgL": np.nan,
}])
conc_means = pd.DataFrame([
    {"treatment": "Control_GM", "plant_id": "A5", "week_no": 7, "chl_a_mgL": 80.0, "chl_b_mgL": 32.0, "total_chl_mgL": 114.0, "carotenoid_mgL": 6.4},
    {"treatment": "Control_GM", "plant_id": "A5", "week_no": 7, "chl_a_mgL": 40.0, "chl_b_mgL": 10.0, "total_chl_mgL": 50.0, "carotenoid_mgL": 4.0},
])
exp_out = storage.apply_concentration_means_to_experiment(exp, conc_means)
assert exp_out.iloc[0]["chl_a_mgL"] == 60.0, f"Expected mean 60.0, got {exp_out.iloc[0]['chl_a_mgL']}"
assert exp_out.iloc[0]["total_chl_mgL"] == 82.0, f"Expected mean 82.0, got {exp_out.iloc[0]['total_chl_mgL']}"
print("=== apply_concentration_means_to_experiment verified ===")

# 6f. read_concentration_excel: returns ALL rows with original headers
raw_df, raw_msg = storage.read_concentration_excel(conc_bytes)
assert not raw_df.empty, f"read_concentration_excel returned empty: {raw_msg}"
assert len(raw_df) == 15, f"Expected 15 raw rows, got {len(raw_df)}"
assert "Sample_ID" in raw_df.columns, f"Should preserve original headers, got {list(raw_df.columns)}"
assert "Replicate" in raw_df.columns
print(f"=== read_concentration_excel verified: {len(raw_df)} rows, original headers preserved ===")

# 6g. parse_concentration_rows: maps + stamps treatment/date/week on selected rows
st.session_state = _FakeSS()
parsed_rows, rows_msg = storage.parse_concentration_rows(
    raw_df, "Control_GM", date="2026-08-31",
)
assert len(parsed_rows) == 15, f"Expected 15 parsed rows, got {len(parsed_rows)}"
assert parsed_rows["treatment"].iloc[0] == "Control_GM"
assert parsed_rows["record_date"].iloc[0] == "2026-08-31"
assert parsed_rows["week_no"].iloc[0] == 5, f"Expected week 5, got {parsed_rows['week_no'].iloc[0]}"
print("=== parse_concentration_rows (all rows) verified: 15 rows, treatment=Control_GM, date=2026-08-31, week=5 ===")

# 6h. parse_concentration_rows with subset (first 3 rows = A5 R1-R3)
parsed_sub, sub_msg = storage.parse_concentration_rows(
    raw_df.iloc[:3], "LED_GM", date="2026-08-31",
)
assert len(parsed_sub) == 3, f"Expected 3 parsed rows from subset, got {len(parsed_sub)}"
assert parsed_sub["treatment"].iloc[0] == "LED_GM"
assert parsed_sub["plant_id"].iloc[0] == "A5"
print(f"=== parse_concentration_rows (subset 3 rows) verified ===")

# 6i. Backward-compat wrapper still works
st.session_state = _FakeSS()
df_w, msg_w = storage.parse_concentration_excel(conc_bytes, "concentration Control-GM.xlsx")
assert len(df_w) == 15, f"Wrapper should still work, got {len(df_w)} rows"
assert df_w["treatment"].iloc[0] == "Control_GM"
print(f"=== parse_concentration_excel wrapper verified: {len(df_w)} rows, treatment={df_w['treatment'].iloc[0]} ===")

print("=== ALL CONCENTRATION UNIT TESTS PASSED ===")

# =============================================================================
# 7. delete_treatment_week_data — removes rows for (treatment, week) from
#    both experiment_data (float week) and concentration_data (int week).
#    Verifies int/float week mismatch is handled and other rows are untouched.
# =============================================================================
exp_del = pd.DataFrame({
    "treatment": ["Control_GM", "Control_GM", "Control_GM", "Control_GM", "LED_GM", "LED_GM"],
    "plant_id":   ["A2",         "A5",         "A2",         "A5",         "A2",     "A2"],
    "week_no":    [1.0,          1.0,          2.0,          2.0,          1.0,      2.0],
    "chl_a_mgL":  [10,           20,           30,           40,           50,       60],
})
conc_del = pd.DataFrame({
    "treatment": ["Control_GM", "Control_GM", "Control_GM", "LED_GM"],
    "plant_id":  ["A2",         "A2",         "A5",         "A2"],
    "replicate": ["R1",         "R2",         "R1",         "R1"],
    "week_no":   [1,            1,            2,            1],  # int
    "chl_a_mgL": [10,           11,           30,           50],
})

exp_out, conc_out = storage.delete_treatment_week_data(exp_del, conc_del, "Control_GM", 1)
assert len(exp_out) == 4, f"Expected 4 exp rows after delete, got {len(exp_out)}"
assert len(conc_out) == 2, f"Expected 2 conc rows after delete, got {len(conc_out)}"
# Control_GM week 1 gone, Control_GM week 2 stays, LED_GM both weeks stay
assert set(exp_out["treatment"]) == {"Control_GM", "LED_GM"}
assert set(conc_out["treatment"]) == {"Control_GM", "LED_GM"}
cg_exp = exp_out[exp_out["treatment"] == "Control_GM"]
assert set(cg_exp["week_no"]) == {2.0}, f"Expected Control_GM only week 2, got {set(cg_exp['week_no'])}"
lg_conc = conc_out[conc_out["treatment"] == "LED_GM"]
assert len(lg_conc) == 1 and lg_conc["week_no"].iloc[0] == 1
print("=== delete_treatment_week_data verified: (Control_GM, week 1) removed, others untouched ===")

# =============================================================================
# 8. clear_tab3_section_data — clears only the section's columns for a
#    treatment (NaN, rows preserved). Other tabs' columns untouched.
# =============================================================================
exp_t3 = pd.DataFrame({
    "treatment": ["Control_GM", "Control_GM", "LED_GM", "LED_GM"],
    "plant_id":   ["A2",         "A5",         "A2",     "A5"],
    "week_no":    [1.0,          1.0,          1.0,      1.0],
    "canopy_width": [30, 35, 28, 32],  # tab2 — must NOT be touched
    "fresh_weight": [100, 120, 90, 110],
    "root_length": [10, 12, 9, 11],
    "sample_weight_g": [0.5, 0.6, 0.4, 0.55],
    "OD663": [0.1, 0.2, 0.15, 0.18],
    "chl_a": [5, 6, 4, 5.5],
    "chl_a_mgL": [50, 55, 45, 52],
})
conc_t3 = pd.DataFrame({
    "treatment": ["Control_GM", "Control_GM", "LED_GM"],
    "plant_id": ["A2", "A5", "A2"],
    "replicate": ["R1", "R1", "R1"],
    "week_no": [1, 1, 1],
    "chl_a_mgL": [50, 55, 45],
})

# 8a. harvest: clear fresh_weight/root_length, keep canopy + uvvis + LED_GM
e_h, _ = storage.clear_tab3_section_data(exp_t3, conc_t3, "Control_GM", "harvest")
cg_h = e_h[e_h["treatment"] == "Control_GM"]
assert cg_h["fresh_weight"].isna().all(), "harvest: fresh_weight should be NaN"
assert cg_h["root_length"].isna().all(), "harvest: root_length should be NaN"
assert cg_h["canopy_width"].notna().all(), "harvest: canopy_width must stay"
assert cg_h["sample_weight_g"].notna().all(), "harvest: uvvis cols must stay"
lg_h = e_h[e_h["treatment"] == "LED_GM"]
assert lg_h["fresh_weight"].notna().all(), "harvest: LED_GM untouched"
print("=== clear_tab3_section_data (harvest) verified: cols cleared, canopy+uvvis+other treatment untouched ===")

# 8b. uvvis: clear OD/sample_weight/chl_a, keep harvest + canopy
e_u, _ = storage.clear_tab3_section_data(exp_t3, conc_t3, "Control_GM", "uvvis")
cg_u = e_u[e_u["treatment"] == "Control_GM"]
assert cg_u["sample_weight_g"].isna().all(), "uvvis: sample_weight_g should be NaN"
assert cg_u["OD663"].isna().all(), "uvvis: OD663 should be NaN"
assert cg_u["chl_a"].isna().all(), "uvvis: chl_a should be NaN"
assert cg_u["fresh_weight"].notna().all(), "uvvis: harvest cols must stay"
assert cg_u["canopy_width"].notna().all(), "uvvis: canopy must stay"
print("=== clear_tab3_section_data (uvvis) verified: OD+calculated cleared, harvest+canopy stay ===")

# 8c. pigment: remove conc rows + clear mgL means in exp, keep harvest+canopy
e_p, c_p = storage.clear_tab3_section_data(exp_t3, conc_t3, "Control_GM", "pigment")
cg_p = e_p[e_p["treatment"] == "Control_GM"]
assert cg_p["chl_a_mgL"].isna().all(), "pigment: mgL should be NaN"
assert cg_p["fresh_weight"].notna().all(), "pigment: harvest must stay"
assert cg_p["canopy_width"].notna().all(), "pigment: canopy must stay"
assert len(c_p[c_p["treatment"] == "Control_GM"]) == 0, "pigment: conc rows removed"
assert len(c_p[c_p["treatment"] == "LED_GM"]) == 1, "pigment: LED_GM conc stays"
print("=== clear_tab3_section_data (pigment) verified: conc rows removed + mgL cleared, harvest+canopy stay ===")

# =============================================================================
# 9. Regression: upload concentration file → dialog opens without TypeError
#    (st.dataframe in Streamlit 1.58 uses on_select + selection_mode, NOT selection)
# =============================================================================
at2 = AppTest.from_file("app.py", default_timeout=120)
at2.run()
assert not at2.exception, f"App failed on initial render: {at2.exception[0].value if at2.exception else ''}"
# Main uploader is the one labeled "Upload XLSX / CSV Data" (index 2: PPFD=0, Temp=1, Main=2)
at2.file_uploader[2].set_value([
    ("concentration Control-GM.xlsx", conc_bytes,
     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
])
at2.run()
assert not at2.exception, (
    f"Dialog TypeError still present after upload: {at2.exception[0].value if at2.exception else ''}"
)
print("=== Regression: concentration upload dialog opens without TypeError ===")

print("=== ALL TESTS PASSED ===")
