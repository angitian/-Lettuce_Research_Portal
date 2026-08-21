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
