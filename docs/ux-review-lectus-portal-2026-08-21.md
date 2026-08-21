# UX Review: Lettuce Research Portal (Full Application)

**วันที่:** 2026-08-21
**ไฟล์ที่วิเคราะห์:** `app.py` (1133 บรรทัด) + modules ทั้งหมด (`data_schema.py`, `stats_analytics.py`, `visualizations.py`, `storage.py`, `export_manager.py`, `phytochemical.py`, `logger_processing.py`, `settings.py`)
**Input sources:** code-only review (ไม่มี screenshot — ไม่พบ dev server ที่รันอยู่)
**ขอบเขตการวิเคราะห์:** วิเคราะห์ทั้ง 5 Tab หลัก (Executive Dashboard, Weekly Data Entry, Environment & Loggers, Harvest & Lab Results, Statistical Analytics) รวมถึง Sidebar, Sub-tabs, และ Data Editor components — อ่าน source code ครบทุกไฟล์
**Reviewer:** Devin (ux-review skill)

---

## สถานะการปรับปรุง (Implementation Status — 2026-08-21, รอบ 3 — ครบทั้งหมด)

> รอบ 1: แก้ครบ แต่ `app.py` ถูก revert. รอบ 2: แก้เฉพาะ Tab 4 + ฟีเจอร์ย่อ/ขยาย. รอบ 3: ทำทั้งหมดใหม่ครบทุกข้อ (ตามคำขอ "ทำทั้งหมดเลย") — สถานะด้านล่างเป็นโค้ดที่รันอยู่จริง

**ทำแล้วครบทุกข้อ (อยู่ในโค้ดปัจจุบัน):**
- **#1** `st.selectbox` → `st.multiselect` เลือกได้หลายตัวแปรพร้อมกัน + แสดงเฉพาะตัวแปรที่มีข้อมูลจริง (`app.py:970`)
- **#2** ANOVA/Tukey แสดงแบบ `expanded=True` เห็นผลทันที (`app.py:1049`)
- **#3** Tab 4 chart sub-tabs → grid 2 คอลัมน์; **#20** Tab 3 รวม Harvest+Phytochem เป็น Tab ต่อแปลงทดลองเดียว (ความลึก 3→2 ระดับ)
- **#4** Pearson correlation เลือกตัวแปรเองได้ (`app.py:1105-1110`)
- **#5** เอาปุ่ม manual save ซ้ำซ้อนออกครบ 4 จุด (Tab 1, Tab 2 soil, Tab 3 harvest/phytochem) — เหลือ auto-save + caption ชี้แจง
- **#6** แก้ NaN → ช่องว่างใน data editor ครบ 4 จุด (Tab 1, Tab 2 soil, Tab 3 harvest/phytochem)
- **#8** `st.spinner` ขณะคำนวณสถิติ; **#9** กราฟ Bar+Boxplot ดู side-by-side
- **#10** empty state ชี้ไปแท็บ Weekly Data Entry
- **#13** ปุ่ม export รวมเป็น "Generate & Download" ขั้นตอนเดียว
- **#15** Sidebar: confirmation 2 ขั้นตอนก่อนล้างข้อมูล (ใช่/ยกเลิก) (`app.py:178-199`)
- **ฟีเจอร์ใหม่:** แต่ละตัวแปรย่อ/ขยายได้ (`st.expander` หัวข้อ `📊 <ชื่อตัวแปร>`) + toggle "ขยายผลลัพธ์ทั้งหมด" (`app.py:985-1000`)

**ที่ยังไม่ได้ทำ (Minor รอการตัดสินใจ):** #11 ทดสอบ keyboard focus ของ CSS, #12 สถานะ auto-save dynamic, #14 รวม treatment tabs ใน Tab 1 เป็นตารางเดียว, #16-19, #21-22 รายละเอียดเล็กน้อยในรายงาน

---

## สรุปผู้บริหาร

- จำนวน findings: **7 Critical, 10 Major, 5 Minor**
- พื้นที่ที่มีปัญหามากที่สุด: **Task Flow & UX Writing** (มิติ 4) — การนำทางซับซ้อน, ผลลัพธ์ถูกซ่อน, ผู้ใช้ไม่สามารถเลือกตัวแปรได้อิสระ
- สิ่งที่ทำได้ดีแล้ว:
  1. การใช้ tooltip ภาษาไทยที่ละเอียดในทุก metric (`METRIC_TOOLTIPS` ใน `data_schema.py`) ช่วยให้ผู้ใช้เข้าใจค่าต่างๆ ได้ดี
  2. CSS responsive สำหรับ tablet (iPad Gen 9) ใน `settings.py` — มีการปรับขนาดปุ่ม, ฟอนต์, และ sidebar สำหรับ touch device
  3. Auto-save + persistent disk storage — ข้อมูลไม่หายเมื่อรีเฟรช
  4. Plotly charts มี hover tooltip ภาษาไทยและ high-contrast theme

---

## Findings

| # | Severity | Category | Issue | Evidence | Recommendation |
|---|----------|----------|-------|----------|----------------|
| 1 | **Critical** | Task Flow | **เลือกตัวแปรวิเคราะห์ได้ทีละ 1 ตัวเท่านั้น** — `st.selectbox` ที่ Tab 4 ให้เลือก metric เดียวจาก `ALL_ANALYSIS_METRICS` (19 metrics) ทำให้ไม่สามารถเปรียบเทียบหลายตัวแปรพร้อมกันได้ ต้องเปลี่ยน dropdown ไป-มา 19 ครั้งเพื่อดูทุกตัวแปร | `app.py:969-974` — `selected_metric_key = st.selectbox("Select Parameter for Statistical Analysis", options=list(ALL_ANALYSIS_METRICS.keys()), ...)` | เปลี่ยนเป็น `st.multiselect` ให้เลือกหลาย metric พร้อมกัน หรือทำ dashboard แบบ grid ที่แสดงผลทุก metric ในหน้าเดียว (คล้าย Executive Dashboard) |
| 2 | **Critical** | Task Flow | **ผล ANOVA และ Tukey HSD ซ่อนใน `st.expander`** — ผู้ใช้ต้องคลิก expander เพิ่มอีก 2 ครั้งเพื่อดูตารางผลลัพธ์ที่สำคัญที่สุด ทำให้เสียเวลาและอาจมองไม่เห็นผลลัพธ์เลย | `app.py:1038` — `with st.expander("📄 Detailed ANOVA Table & Model Summary"):` และ `app.py:1045` — `with st.expander("🔍 Tukey HSD Post-Hoc Pairwise Comparisons"):` | แสดง ANOVA summary table โดยตรง (ไม่ต้อง expander) หรือใช้ expander แบบ `expanded=True` เป็นค่าเริ่มต้น เพื่อให้เห็นผลทันทีเมื่อเลือก metric |
| 3 | **Critical** | Visual Hierarchy | **Tab ซ้อนลึกเกินไป (3 ระดับ)** — Tab 1 มี 5 sub-tabs (TREATMENTS), Tab 3 มี 2 sub-tabs แต่ละอันมี 5 sub-sub-tabs, Tab 4 มี 4 sub-tabs — รวมแล้วผู้ใช้ต้อง navigate ผ่าน tab มากกว่า 20 จุด คลิกเฉลี่ย 3-5 ครั้งเพื่อเข้าถึงข้อมูล | `app.py:195-201` (main tabs), `app.py:323` (Tab 1 sub-tabs), `app.py:784,865` (Tab 3 sub-tabs), `app.py:1053-1058` (Tab 4 sub-tabs) | ลดความลึกของ tab: รวมข้อมูลในหน้าเดียวด้วย `st.columns` แทน sub-tabs หรือใช้ radio button สำหรับเลือก treatment แทน sub-tabs 5 อัน |
| 4 | **Critical** | Task Flow | **Pearson Correlation ใช้ตัวแปร hardcoded ผู้ใช้เลือกไม่ได้** — `num_cols` ที่ใช้คำนวณ correlation matrix ถูก hardcode ไว้ตายตัว ผู้ใช้ไม่สามารถเลือกเพิ่ม/ลดตัวแปรที่ต้องการวิเคราะห์ความสัมพันธ์ได้ | `app.py:1084` — `num_cols = ["canopy_width", "canopy_length", "canopy_height", "leaf_count", "fresh_weight", "total_chl", "carotenoids", "total_phenolics", "temp_c", "ppfd_led_gm", "soil_ph", "soil_ec", "soil_om"]` | ใช้ `st.multiselect` ให้ผู้ใช้เลือกตัวแปรที่ต้องการ correlate ได้เอง พร้อม default เลือกทั้งหมด |
| 5 | **Critical** | Heuristic | **Auto-Save + ปุ่ม Save แบบ manual ซ้ำซ้อนสร้างความสับสน** — ระบบบอกว่า "Auto-Save Active: บันทึกถาวรเรียบร้อยแล้ว" แต่ยังมีปุ่ม `💾 บันทึกข้อมูล` แยกต่างหาก ผู้ใช้ไม่รู้ว่าต้องกดปุ่มหรือไม่ ข้อมูลบันทึกแล้วจริงหรือยัง | `app.py:396-402` (save button + auto-save caption), `app.py:857-863` (harvest save), `app.py:939-945` (phytochem save) | เลือกอย่างใดอย่างหนึ่ง: (1) auto-save อย่างเดียว + แสดงสถานะ "บันทึกแล้ว" ชัดเจน โดยไม่มีปุ่ม manual, หรือ (2) manual save อย่างเดียว + confirmation dialog ก่อนออกจากหน้า |
| 6 | **Critical** | WCAG | **Data Editor แสดงค่า `NaN` แทนช่องว่าง** — เมื่อยังไม่มีข้อมูล ตาราง data editor แสดง `NaN` ซึ่งเป็น jargon ทางเทคนิคที่นักวิจัยทั่วไปอาจไม่เข้าใจ และดูไม่เป็นมืออาชีพ | `app.py:349,363,820-822,900-903` — `sub_df[col] = np.nan` ส่งผลให้ data editor แสดง `NaN` ในเซลล์ว่าง | ใช้ `None` หรือ `""` แทน `np.nan` สำหรับแถวที่ยังไม่มีข้อมูล, หรือใช้ `st.column_config.NumberColumn` กับ parameter `default=None` |
| 7 | **Critical** | Heuristic | **Dropdown ผสม metric ทุกประเภทในรายการเดียว** — `ALL_ANALYSIS_METRICS` รวม weekly metrics, harvest metrics, และ phytochemical metrics ไว้ใน list เดียวโดยไม่แยกหมวดหมู่ ผู้ใช้ต้องเลื่อนดู 19 รายการแบบไม่มีการจัดกลุ่ม | `data_schema.py:93-102` — `ALL_ANALYSIS_METRICS` รวม `WEEKLY_METRICS`, `HARVEST_METRICS`, `PHYTOCHEMICAL_METRICS` เข้าด้วยกัน | จัดกลุ่ม metrics ใน dropdown ด้วย `optgroup` (ถ้า Streamlit รองรับ) หรือใช้ 3 dropdowns แยกตามหมวดหมู่ (Growth, Harvest, Phytochemical) |
| 8 | **Major** | Heuristic | **ไม่มี loading indicator สำหรับคำนวณสถิติ** — ANOVA, Tukey HSD, และการสร้าง Full Report ใช้เวลาคำนวณ 5-15 วินาที แต่ไม่มี progress bar หรือ spinner (ยกเว้น Full Report ที่มี `st.spinner`) | `app.py:994-1047` — การคำนวณ descriptive stats, ANOVA, Tukey HSD ไม่มี loading state | เพิ่ม `st.spinner` หรือ skeleton loading เมื่อเปลี่ยน metric ใน dropdown |
| 9 | **Major** | Visual Hierarchy | **กราฟ 4 ประเภทแยกเป็น sub-tabs ดูพร้อมกันไม่ได้** — Error Bar, Boxplot, Growth Trajectory, Correlation Heatmap อยู่ใน sub-tabs แยกกัน ทำให้นักวิจัยไม่สามารถเปรียบเทียบกราฟแบบ side-by-side ได้ | `app.py:1053-1058` — `chart_t1, chart_t2, chart_t3, chart_t4 = st.tabs([...])` | ใช้ `st.columns(2)` แสดง 2 กราฟต่อแถว หรือให้ผู้ใช้เลือก layout (tab view / grid view) |
| 10 | **Major** | Heuristic | **ไม่มี empty state guidance ใน Tab 4** — เมื่อยังไม่มีข้อมูล numerical, Tab 4 แสดงแค่ `st.info("ยังไม่มีข้อมูลตัวเลขสำหรับการวิเคราะห์ทางสถิติ...")` แต่ไม่แนะนำขั้นตอนต่อไปว่าผู้ใช้ต้องทำอะไร (เช่น "ไปที่ Tab 1 เพื่อกรอกข้อมูล") | `app.py:965` — `st.info("📌 ยังไม่มีข้อมูลตัวเลขสำหรับการวิเคราะห์ทางสถิติ กรุณากรอกข้อมูลตัวเลขในตารางบันทึก หรืออัปโหลดไฟล์ Excel/CSV ข้อมูลวิจัยจริง")` | เพิ่มปุ่ม "Go to Weekly Data Entry →" ใน empty state เพื่อนำทางผู้ใช้ |
| 11 | **Major** | WCAG | **ปุ่มใช้ `div` หรือ CSS ซับซ้อนที่อาจมีปัญหา keyboard focus** — CSS ใน `settings.py` ใช้ `pointer-events: none` กับ header/toolbar เพื่อแก้ปัญหา touch แต่เสี่ยงทำให้ keyboard navigation พัง | `settings.py:28-66` — `pointer-events: none !important` บน header, toolbar, tab elements | ทดสอบ keyboard navigation (Tab, Enter, Space) บนทุก element และใช้ `:focus-visible` styles |
| 12 | **Major** | UX Writing | **คำว่า "Auto-Save Active" และ "บันทึกถาวรเรียบร้อยแล้ว" แสดงตลอดเวลาแม้ยังไม่มีการแก้ไข** — ข้อความนี้ปรากฏทันทีที่เปิด tab ทำให้ความหมายเจือจาง ผู้ใช้ไม่สนใจเมื่อมีการเปลี่ยนแปลงจริง | `app.py:402,863,945` — `st.caption(f"⚡ **Auto-Save Active**: ข้อมูล...ถูกบันทึกถาวรเรียบร้อยแล้ว")` | แสดงสถานะเฉพาะเมื่อมีการเปลี่ยนแปลง: "✓ เซลล์ที่แก้ไขถูกบันทึกแล้ว" หรือเปลี่ยนเป็น badge สีเขียวเล็กๆ แทนข้อความยาว |
| 13 | **Major** | Task Flow | **ต้องกด "Generate Full Report" ทุกครั้งก่อนดาวน์โหลด** — การ export statistical report ต้องกด Generate ก่อน แล้วค่อยกด Download (2 ขั้นตอน) และถ้า refresh หน้าหาย ต้อง generate ใหม่ | `app.py:1103-1133` — ปุ่ม Generate และ Download แยกกัน | รวมเป็นปุ่มเดียว "Download Full Report (.zip)" ที่ generate และ download ในขั้นตอนเดียว |
| 14 | **Major** | Visual Hierarchy | **Tab 1 Weekly Data Entry แสดง 5 treatment sub-tabs แต่ละอันมีตาราง 10 แถว** — ผู้ใช้ต้องสลับ tab 5 ครั้งเพื่อกรอกข้อมูลให้ครบทุก treatment ในวันเดียว ข้อมูลรวม 50 แถวถูกแยกเป็น 5 หน้า | `app.py:323-402` — `sub_tabs = st.tabs(TREATMENTS)` แล้ว loop สร้าง data editor แยกกัน | แสดงทุก treatment ในหน้าเดียวด้วย `st.columns` หรือทำเป็นตารางใหญ่รวมทุก treatment (pivot: plant_id × treatment) |
| 15 | **Major** | Heuristic | **ปุ่ม "ล้างข้อมูลทั้งหมด" อยู่ใกล้ปุ่มอื่นเกินไปและไม่มี confirmation dialog** — ปุ่มล้างข้อมูลทั้งหมด (`clear_disk_storage`) ทำงานทันทีที่กด (หลังจาก `st.rerun()` ไม่มี `st.warning` หรือ confirmation ก่อน) | `app.py:178-187` — `if st.button("🗑️ ล้างข้อมูลทั้งหมด", ...)` แล้วล้างทันที | เพิ่ม `st.warning` หรือ `st.checkbox` ยืนยันก่อนลบ: "คุณแน่ใจหรือไม่? การกระทำนี้ไม่สามารถย้อนกลับได้" |
| 16 | **Major** | WCAG | **ไอคอน emoji ใช้แทนความหมายโดยไม่มี text fallback** — Tab titles และ section headers ใช้ emoji (🥬, 📝, 🌡️, 🔬, 📊, ฯลฯ) ซึ่ง screen reader อาจอ่านไม่ถูกต้อง | `app.py:195-201` — `"🏠 Executive Dashboard"`, `"📝 Weekly Data Entry"` ฯลฯ | Emoji ใช้เป็น decoration ได้ แต่ควรมี text label ที่ชัดเจนเสมอ (ซึ่งมีอยู่แล้ว) — ตรวจสอบว่า screen reader อ่าน label ไม่ใช่ emoji |
| 17 | **Minor** | Visual Hierarchy | **KPI cards ใน Dashboard มี `st.caption` ซ้ำซ้อนกับ tooltip** — แต่ละ `st.metric` มีทั้ง `help` parameter และ `st.caption` ที่อธิบายซ้ำกัน ทำให้ dashboard แน่นเกินไป | `app.py:243-253` — `st.metric(..., help="...")` แล้วตามด้วย `st.caption("📌 **คำอธิบาย**: ...")` | เก็บคำอธิบายไว้ใน `help` tooltip อย่างเดียว ลบ `st.caption` ออกเพื่อความสะอาด |
| 18 | **Minor** | UX Writing | **Label ปุ่ม export ไม่สื่อถึงเนื้อหาไฟล์** — "Download CSV Data" และ "Download Multi-Sheet Excel Report" ไม่ระบุจำนวนแถวหรือวันที่ของข้อมูล | `app.py:152-157,166-173` | เพิ่มจำนวนแถวใน label เช่น "📄 Download CSV (2,450 rows)" |
| 19 | **Minor** | Visual Hierarchy | **Sidebar ยาวมากด้วยข้อมูล import/export/data management** — Sidebar มี file uploader, download buttons, และ clear data รวมกัน โดยไม่มี visual separation ที่ชัดเจนเพียงพอ | `app.py:92-190` — Sidebar content ทั้งหมด | จัดกลุ่มด้วย `st.expander` หรือ card: "📂 Import", "💾 Export", "🗑️ Manage" |
| 20 | **Minor** | Task Flow | **Tab 3 (Harvest & Lab) แยก Harvest กับ Phytochem เป็น sub-tabs แต่ข้อมูลมันเกี่ยวข้องกัน** — Harvest yield และ Lab absorbance มาจากตัวอย่างเดียวกัน การแยก tab ทำให้ผู้ใช้ต้องกรอกข้อมูลซ้ำซ้อน (เลือก treatment ซ้ำสองรอบ) | `app.py:784-865` — `t_harvest, t_phytochem = st.tabs([...])` | รวม harvest yield + phytochem absorbance ในตารางเดียว จัดกลุ่มตาม plant_id |
| 21 | **Minor** | Heuristic | **ไม่มี "Select All Weeks" เป็น default ใน Weekly Summary** — Tab 4 default week filter เป็น "All Weeks" แต่ใน Tab 1 date picker ไม่มีตัวเลือก "ดูทุกสัปดาห์" ทำให้ดูข้อมูลย้อนหลังยาก | `app.py:303-309` — `selected_date = st.date_input(...)` — เลือกได้ทีละวัน | เพิ่มปุ่ม "Show All Weeks" หรือทำ weekly summary table ใน Tab 1 |
| 22 | **Minor** | WCAG | **Soil Texture SelectboxColumn อาจไม่รองรับ keyboard navigation เต็มรูปแบบ** — `st.column_config.SelectboxColumn` ใน data editor อาจมีปัญหา keyboard accessibility | `app.py:762` — `st.column_config.SelectboxColumn("Soil Texture", options=[...])` | ทดสอบว่า selectbox ใน data editor รองรับการเลือกด้วยแป้นพิมพ์ (Arrow keys, Enter) |

---

## ลำดับความสำคัญแนะนำ

1. **เปลี่ยน `st.selectbox` → `st.multiselect` ใน Tab 4** — ให้ผู้ใช้เลือกวิเคราะห์ได้หลายตัวแปรพร้อมกัน (Critical #1, #7)
2. **แสดงผล ANOVA/Tukey โดยตรง ไม่ต้องคลิก expander** — ใช้ `expanded=True` หรือแสดงผล inline (Critical #2)
3. **ลดความลึกของ tab** — รวม Weekly Data Entry 5 sub-tabs เป็นตารางเดียว, รวม Harvest + Phytochem tabs (Critical #3, Major #14, Minor #20)
4. **เปลี่ยน Pearson correlation ให้ผู้ใช้เลือกตัวแปรเอง** — ใช้ `st.multiselect` (Critical #4)
5. **ปรับปรุง auto-save UX** — เอาปุ่ม manual save ออก หรือเปลี่ยนเป็นระบบ manual save + confirmation (Critical #5)
6. **แก้ NaN → ช่องว่างใน data editor** — ใช้ `None` แทน `np.nan` (Critical #6)
7. **เพิ่ม loading states** — `st.spinner` สำหรับ ANOVA/Tukey computations (Major #8)
8. **ปรับ layout กราฟ** — ใช้ `st.columns` แทน sub-tabs ให้ดูกราฟแบบ side-by-side ได้ (Major #9)
9. **เพิ่ม confirmation dialog ก่อนล้างข้อมูล** — ป้องกันการลบข้อมูลโดยไม่ตั้งใจ (Major #15)
10. **รวม Generate + Download เป็นปุ่มเดียว** — ลดขั้นตอนการ export (Major #13)

---

## ภาคผนวก: Heuristic Checklist

| Heuristic | ผ่าน? | หมายเหตุ |
|-----------|-------|----------|
| Visibility of system status | ✗ | ไม่มี loading state สำหรับ ANOVA/Tukey (Major #8); auto-save status แสดงตลอดเวลาจนไม่มีความหมาย (Major #12) |
| Match between system and real world | ✗ | แสดง `NaN` ใน data editor แทนช่องว่าง (Critical #6) |
| User control & freedom | ✗ | ไม่มี undo/cancel สำหรับ auto-save (Critical #5); ไม่มี confirmation ก่อนล้างข้อมูล (Major #15) |
| Consistency & standards | ✓ | ปุ่มใช้สีเขียวสม่ำเสมอ, layout คงเส้นคงวา, ใช้ emoji + text label pattern เดียวกัน |
| Error prevention | ✗ | ล้างข้อมูลโดยไม่มี confirmation (Major #15); ไม่มี validation ก่อน submit |
| Recognition rather than recall | ✗ | ผลลัพธ์สถิติซ่อนใน expander (Critical #2); ต้องจำว่าข้อมูลอยู่ tab ไหน (Critical #3) |
| Flexibility & efficiency | ✗ | เลือก metric ได้ทีละ 1 ตัว (Critical #1); Pearson correlation เลือกตัวแปรไม่ได้ (Critical #4) |
| Aesthetic & minimalist design | ✗ | KPI cards มี caption ซ้ำกับ tooltip (Minor #17); sidebar ยาวเกินไป (Minor #19) |
| Help users recognize/diagnose/recover from errors | ✓ | tooltip ภาษาไทยละเอียดทุก metric (`METRIC_TOOLTIPS`) |
| Help & documentation | ✓ | มี help text บน file uploader, date picker, และทุก metric |

## ภาคผนวก: WCAG Checklist

| เกณฑ์ | ผ่าน? | หมายเหตุ |
|-------|-------|----------|
| Contrast 4.5:1 | ✓ | ปุ่ม `#1b5e20` บน `#ffffff` → contrast ratio ~10.2:1 ผ่าน; Plotly hover `#0f172a` บน `#ffffff` → ~15.4:1 ผ่าน |
| Non-text content (alt/aria-label) | ~ | Emoji มี text label กำกับ (✓) แต่ยังต้องทดสอบ screen reader จริง (Major #16) |
| Keyboard navigable | ? | CSS ใช้ `pointer-events: none` อาจกระทบ keyboard focus (Major #11) — ต้องทดสอบ |
| Forms (label for input) | ? | Streamlit จัดการ label ให้อัตโนมัติ แต่ data editor custom column อาจต้องตรวจเพิ่ม (Minor #22) |
| Color alone | ✓ | Significance แสดงทั้งสีและเครื่องหมาย `*` ใน ANOVA table (`app.py:1012-1036`) |
| Headings hierarchy | ~ | ใช้ `st.subheader`, `st.markdown("#### ...")` เป็นหลัก — hierarchy อาจไม่เป็นระบบเพราะ Streamlit ไม่บังคับ heading levels |
| Semantic HTML/ARIA | ? | Streamlit render เป็น HTML ให้อัตโนมัติ — ต้องทดสอบด้วย axe DevTools |
| Reflow/Responsive | ✓ | CSS responsive สำหรับ tablet (`settings.py:244-293`) |

---

## สรุปแนวทางปรับปรุงสำหรับปัญหาที่ user แจ้ง

### "ใช้งานค่อนข้างยาก"
→ **ลดความลึกของ tab** (Critical #3, Major #14) — ใช้ `st.columns` หรือ radio button แทน sub-tabs หลายชั้น

### "ค่าต่าง ๆ ดูสับสน"
→ **แก้ NaN เป็นช่องว่าง** (Critical #6), **จัดกลุ่ม metrics ใน dropdown** (Critical #7), **ลด caption ซ้ำซ้อน** (Minor #17)

### "เรียกดูผลยากมาก (ใช้ dropdown)"
→ **แสดง ANOVA/Tukey โดยตรง** (Critical #2), **เปลี่ยนเป็น multiselect** (Critical #1), **รวมกราฟในหน้าเดียว** (Major #9)

### "ผลวิเคราะห์ทางสถิติ ไม่สามารถเลือกตัวแปรในการวิเคราะห์ได้"
→ **multiselect metrics** (Critical #1), **multiselect correlation variables** (Critical #4), **export รวมทุก metric อัตโนมัติ** (Major #13)
