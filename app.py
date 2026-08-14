"""
Streamlit Web Application:
Influence of LED Supplemental Lighting and Soil Chemical Properties on
Phytochemical Accumulation in Head Lettuce.

Senior Python Developer & Plant Science Researcher Implementation.
"""

import datetime
import importlib
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Config & Theme Imports (Force reload to bypass sys.modules cache)
import config.settings as settings
importlib.reload(settings)

APP_TITLE = getattr(settings, "APP_TITLE", "Lettuce Phytochemical & LED Research Portal")
APP_SUBTITLE = getattr(settings, "APP_SUBTITLE", "Influence of LED Supplemental Lighting & Soil Chemical Properties on Phytochemical Accumulation in Head Lettuce")
CUSTOM_TABLET_CSS = getattr(settings, "CUSTOM_TABLET_CSS", "")
COLOR_PALETTE = getattr(settings, "COLOR_PALETTE", {})
START_DATE = getattr(settings, "START_DATE", datetime.date(2026, 8, 4))

# Custom Module Imports (Safe getattr pattern for hot-reloading resilience)
import modules.data_schema as data_schema
importlib.reload(data_schema)

TREATMENTS = getattr(data_schema, "TREATMENTS", ["Control_GM", "LED_GM", "Control_F", "LED_F (1)", "LED_F (2)"])
PLANT_IDS = getattr(data_schema, "PLANT_IDS", ["A2", "A5", "A7", "B3", "B5", "B6", "B8", "C4", "C6", "C9"])
WEEKLY_METRICS = getattr(data_schema, "WEEKLY_METRICS", {})
HARVEST_METRICS = getattr(data_schema, "HARVEST_METRICS", {})
PHYTOCHEMICAL_METRICS = getattr(data_schema, "PHYTOCHEMICAL_METRICS", {})
SOIL_ENV_METRICS = getattr(data_schema, "SOIL_ENV_METRICS", {})
ALL_ANALYSIS_METRICS = getattr(data_schema, "ALL_ANALYSIS_METRICS", {})
METRIC_TOOLTIPS = getattr(data_schema, "METRIC_TOOLTIPS", {})

import modules.storage as storage
importlib.reload(storage)

initialize_session_state = getattr(storage, "initialize_session_state")
parse_uploaded_excel = getattr(storage, "parse_uploaded_excel")
render_indexeddb_component = getattr(storage, "render_indexeddb_component")
generate_empty_dataset = getattr(storage, "generate_empty_dataset")
generate_empty_environment_data = getattr(storage, "generate_empty_environment_data")
generate_env_template = getattr(storage, "generate_env_template")
save_experiment_data_to_disk = getattr(storage, "save_experiment_data_to_disk")
save_env_data_to_disk = getattr(storage, "save_env_data_to_disk")
clear_disk_storage = getattr(storage, "clear_disk_storage")

import modules.logger_processing as logger_processing
importlib.reload(logger_processing)

from modules.phytochemical import apply_phytochemical_calculations
from modules.stats_analytics import (
    calculate_descriptive_stats, run_two_way_anova, 
    run_tukey_hsd, compute_pearson_correlation
)
from modules.visualizations import (
    plot_treatment_bar_chart, plot_plant_boxplot, 
    plot_growth_trajectory, plot_correlation_heatmap
)
from modules.export_manager import generate_csv_export, generate_multisheet_excel

# -----------------------------------------------------------------------------
# 1. Page Configuration & Custom CSS (Tablet & Touch-Friendly Theme)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🥬",
    layout="wide",
    initial_sidebar_state="expanded"
)

if CUSTOM_TABLET_CSS:
    st.markdown(CUSTOM_TABLET_CSS, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Session State Initialization
# -----------------------------------------------------------------------------
initialize_session_state()

if "selected_date" not in st.session_state:
    st.session_state.selected_date = START_DATE

# -----------------------------------------------------------------------------
# 3. Sidebar: File Operations & Data Management
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/lettuce.png", width=64)
    st.title("🥬 Lettuce Research Portal")
    st.markdown("---")
    
    st.subheader("📂 Import Operations")
    uploaded_file = st.file_uploader(
        "Upload XLSX / CSV Data",
        type=["xlsx", "xls", "csv"],
        help="อัปโหลดไฟล์ Excel (.xlsx) ที่มีโครงสร้าง 5 Sheet (Control_GM, LED_GM, Control_F, LED_F1, LED_F2) หรือไฟล์ CSV ข้อมูลงานวิจัย"
    )
    
    if uploaded_file is not None:
        if uploaded_file.name.endswith((".xlsx", ".xls")):
            new_df, msg = parse_uploaded_excel(uploaded_file.getvalue())
            if not new_df.empty:
                st.session_state.experiment_data = new_df
                save_experiment_data_to_disk(new_df)
                st.success(msg)
            else:
                st.error(msg)
        elif uploaded_file.name.endswith(".csv"):
            try:
                new_df = pd.read_csv(uploaded_file)
                new_df = apply_phytochemical_calculations(new_df)
                st.session_state.experiment_data = new_df
                save_experiment_data_to_disk(new_df)
                st.success("Successfully imported CSV dataset!")
            except Exception as e:
                st.error(f"Failed to read CSV: {str(e)}")
                
    st.markdown("---")
    st.subheader("💾 Export Operations")
    
    # Download CSV
    csv_bytes = generate_csv_export(st.session_state.experiment_data)
    st.download_button(
        label="📄 Download CSV Data",
        data=csv_bytes,
        file_name="lettuce_experiment_data.csv",
        mime="text/csv",
        use_container_width=True,
        help="ดาวน์โหลดข้อมูลวิจัยทั้งหมดในรูปแบบไฟล์ CSV"
    )
    
    # Download Full Multi-sheet Excel
    excel_bytes = generate_multisheet_excel(
        st.session_state.experiment_data, 
        st.session_state.env_data
    )
    st.download_button(
        label="📊 Download Multi-Sheet Excel Report (.xlsx)",
        data=excel_bytes,
        file_name="lettuce_research_full_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        help="ดาวน์โหลดรายงานสมบูรณ์แบบหลาย Sheet (.xlsx) ประกอบด้วย Raw Data, Weekly Summary, Phytochemical Analysis และ Environmental Loggers"
    )
    
    st.markdown("---")
    st.subheader("🗑️ Data Management")
    
    if st.button("🗑️ ล้างข้อมูลทั้งหมด", use_container_width=True, help="ล้างข้อมูลทั้งหมดออก เพื่อเริ่มบันทึกข้อมูลงานวิจัยจริงจากตารางว่าง"):
        clear_disk_storage()
        st.session_state.experiment_data = generate_empty_dataset()
        st.session_state.env_data = generate_empty_environment_data()
        st.session_state.logger_ppfd = pd.DataFrame()
        st.session_state.logger_temp = pd.DataFrame()
        st.session_state.ppfd_channel_mapping = {}
        st.session_state.selected_date = START_DATE
        st.success("ล้างข้อมูลทั้งหมดเรียบร้อยแล้ว!")
        st.rerun()
        
    st.markdown("<br>", unsafe_allow_html=True)
    render_indexeddb_component()

# -----------------------------------------------------------------------------
# 4. Main Tab Navigation
# -----------------------------------------------------------------------------
tab_dash, tab1, tab2, tab3, tab4 = st.tabs([
    "🏠 Executive Dashboard",
    "📝 Weekly Data Entry",
    "🌡️ Environment & Loggers",
    "🔬 Harvest & Lab Results",
    "📊 Statistical Analytics & Graphs"
])

# =============================================================================
# TAB 0: EXECUTIVE DASHBOARD
# =============================================================================
with tab_dash:
    st.subheader("🏠 Research Overview & Key Performance Dashboard")
    st.markdown("Executive summary of experimental metrics, plant growth trajectories, and phytochemical accumulation.")
    
    df_exp = st.session_state.experiment_data.copy()
    env_df = st.session_state.env_data.copy()
    
    # Top KPI Metrics Cards with Explicit Clear Thai Captions
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    total_records = len(df_exp.dropna(subset=["canopy_width"], how="all")) if not df_exp.empty else 0
    total_plants = df_exp["plant_id"].nunique() * df_exp["treatment"].nunique() if not df_exp.empty else 50
    
    # Calculate LED boost vs Control
    valid_cw = df_exp.dropna(subset=["canopy_width"]) if not df_exp.empty else pd.DataFrame()
    if not valid_cw.empty and "canopy_width" in valid_cw.columns:
        led_w = valid_cw[valid_cw["lighting"] != "Control"]["canopy_width"].mean()
        ctrl_w = valid_cw[valid_cw["lighting"] == "Control"]["canopy_width"].mean()
        boost_pct = round(((led_w - ctrl_w) / ctrl_w) * 100, 1) if ctrl_w > 0 else 0.0
    else:
        boost_pct = 0.0
        
    mean_chl = round(df_exp["total_chl"].dropna().mean(), 2) if not df_exp.empty and "total_chl" in df_exp.columns and not df_exp["total_chl"].dropna().empty else 0.0
    mean_phen = round(df_exp["total_phenolics"].dropna().mean(), 2) if not df_exp.empty and "total_phenolics" in df_exp.columns and not df_exp["total_phenolics"].dropna().empty else 0.0
    
    with kpi1:
        st.metric("🌱 Total Sample Plants", f"{total_plants} Plants", f"{total_records} Records Logged", help="จำนวนต้นพืชตัวอย่างและจำนวนเรคคอร์ดข้อมูลที่บันทึกไว้ในระบบทั้งหมด")
        st.caption("📌 **คำอธิบาย**: จำนวนต้นพืชตัวอย่างและเรคคอร์ดทั้งหมด")
    with kpi2:
        st.metric("💡 LED Growth Boost", f"+{boost_pct}%", "vs Natural Light Control", help="เปอร์เซ็นต์ความกว้างทรงพุ่มที่เพิ่มขึ้นเฉลี่ยจากการเสริมแสง LED เทียบกับกลุ่มควบคุมแสงธรรมชาติ")
        st.caption("📌 **คำอธิบาย**: % ความกว้างทรงพุ่มที่เพิ่มขึ้นจากแสงเสริม LED")
    with kpi3:
        st.metric("🧪 Mean Total Chlorophyll", f"{mean_chl} mg/g", "FW Normalized", help="ปริมาณคลอโรฟิลล์รวมเฉลี่ย (mg/g น้ำหนักสด) ปรับมาตรฐานตามน้ำหนักตัวอย่างพืช")
        st.caption("📌 **คำอธิบาย**: คลอโรฟิลล์รวมเฉลี่ย (mg/g น้ำหนักสด)")
    with kpi4:
        st.metric("🌿 Mean Total Phenolics", f"{mean_phen} mg GAE/g", "Folin-Ciocalteu Assay", help="ปริมาณสารประกอบฟีนอลิกรวมเฉลี่ย (mg GAE/g น้ำหนักสด) วิเคราะห์ด้วยวิธี Folin-Ciocalteu")
        st.caption("📌 **คำอธิบาย**: สารประกอบฟีนอลิกรวมเฉลี่ย (mg GAE/g)")
        
    st.markdown("---")
    
    d_col1, d_col2 = st.columns(2)
    
    with d_col1:
        st.markdown("#### 📈 Canopy Width Trajectory Across Weeks")
        fig_dash_line = plot_growth_trajectory(df_exp, "canopy_width", "Canopy Width (cm)")
        st.plotly_chart(fig_dash_line, use_container_width=True, key="dash_growth_line_chart")
        
    with d_col2:
        st.markdown("#### 🧪 Phytochemical Accumulation Comparison")
        fig_dash_bar = plot_treatment_bar_chart(df_exp, "total_chl", "Total Chlorophyll (mg/g FW)")
        st.plotly_chart(fig_dash_bar, use_container_width=True, key="dash_phytochem_bar_chart")
        
    st.markdown("---")
    
    st.markdown("#### 📋 Latest Biometric Summary by Treatment")
    latest_week = df_exp["week_no"].max() if not df_exp.empty else 1
    latest_df = df_exp[df_exp["week_no"] == latest_week] if not df_exp.empty else pd.DataFrame()
    
    full_trt_df = pd.DataFrame({"treatment": TREATMENTS})
    full_trt_df["Variety"] = full_trt_df["treatment"].map(data_schema.VARIETY_MAP)
    full_trt_df["Lighting"] = full_trt_df["treatment"].map(data_schema.LIGHTING_MAP)
    
    if not latest_df.empty:
        agg_tbl = latest_df.groupby("treatment").agg(
            Canopy_Width_cm=("canopy_width", "mean"),
            Canopy_Height_cm=("canopy_height", "mean"),
            Leaf_Count=("leaf_count", "mean"),
            Total_Chl_mgg=("total_chl", "mean")
        ).reset_index()
        summary_tbl = full_trt_df.merge(agg_tbl, on="treatment", how="left").round(2)
    else:
        summary_tbl = full_trt_df
        for col in ["Canopy_Width_cm", "Canopy_Height_cm", "Leaf_Count", "Total_Chl_mgg"]:
            summary_tbl[col] = np.nan
            
    st.dataframe(summary_tbl, use_container_width=True)

# =============================================================================
# TAB 1: WEEKLY DATA ENTRY (Date Picker formatted as DD/MM/YYYY, Auto-Save)
# =============================================================================
with tab1:
    st.subheader("📝 บันทึกข้อมูลการเจริญเติบโตประจำวัน (Auto-Save & Save Button)")
    st.markdown("ระบบจะ **บันทึกข้อมูลให้อัตโนมัติทันที** เมื่อกรอกตัวเลขในตาราง และสามารถกดปุ่ม `💾 บันทึกข้อมูล` เพื่อยืนยันการบันทึกได้ตลอดเวลา")
    
    col_w, col_info = st.columns([2, 3])
    with col_w:
        selected_date = st.date_input(
            "📅 เลือกวันที่บันทึกข้อมูล (Measurement Date)",
            value=st.session_state.get("selected_date", START_DATE),
            format="DD/MM/YYYY",
            key="measurement_date_picker",
            help="เลือกวันที่ทำการวัดค่าวัดทรงพุ่มและจำนวนใบของผักกาดหอมในแปลงทดลอง (รูปแบบ dd/mm/yyyy)"
        )
        st.session_state.selected_date = selected_date
        
        days_diff = (selected_date - START_DATE).days
        calculated_week = max(1, (days_diff // 7) + 1)
        st.session_state.current_week = calculated_week
        
    with col_info:
        date_formatted = selected_date.strftime("%d/%m/%Y")
        st.info(f"📌 **วันที่เลือก**: `{date_formatted}` | **สัปดาห์ที่**: `Week {calculated_week}` | ⚡ **สถานะ**: `บันทึกข้อมูลอัตโนมัติคงทน (Persistent Auto-Save Active)`")
        
    date_str = selected_date.strftime("%Y-%m-%d")
    df_current = st.session_state.experiment_data.copy()
    
    sub_tabs = st.tabs(TREATMENTS)
    
    for idx, trt_name in enumerate(TREATMENTS):
        with sub_tabs[idx]:
            st.markdown(f"#### แปลงทดลอง: **{trt_name}** | วันที่: `{date_formatted}` (Week {calculated_week})")
            
            if "record_date" in df_current.columns:
                mask = (df_current["record_date"] == date_str) & (df_current["treatment"] == trt_name)
            else:
                mask = (df_current["week_no"] == calculated_week) & (df_current["treatment"] == trt_name)
                
            sub_df = df_current[mask].copy()
            
            existing_pids = set(sub_df["plant_id"].tolist()) if not sub_df.empty else set()
            missing_pids = [pid for pid in PLANT_IDS if pid not in existing_pids]
            
            if missing_pids:
                new_rows = []
                for pid in missing_pids:
                    new_rows.append({
                        "record_date": date_str,
                        "week_no": calculated_week,
                        "variety": data_schema.VARIETY_MAP.get(trt_name, "Green Moon"),
                        "lighting": data_schema.LIGHTING_MAP.get(trt_name, "Control"),
                        "treatment": trt_name,
                        "plant_id": pid,
                        "canopy_width": np.nan,
                        "canopy_length": np.nan,
                        "canopy_height": np.nan,
                        "leaf_count": np.nan,
                        "hue_angle": np.nan
                    })
                sub_df = pd.concat([sub_df, pd.DataFrame(new_rows)], ignore_index=True)
                
            sub_df["pid_order"] = pd.Categorical(sub_df["plant_id"], categories=PLANT_IDS, ordered=True)
            sub_df = sub_df.sort_values("pid_order").drop(columns=["pid_order"])
            
            display_cols = ["plant_id", "canopy_width", "canopy_length", "canopy_height", "leaf_count", "hue_angle"]
            for col in display_cols:
                if col not in sub_df.columns:
                    sub_df[col] = np.nan
                    
            edited_df = st.data_editor(
                sub_df[display_cols],
                key=f"editor_{trt_name}_{date_str}",
                column_config={
                    "plant_id": st.column_config.TextColumn("Plant ID (ต้นที่กำหนด - ค่าคงที่)", disabled=True, help="รหัสต้นพืชคงที่ 10 ต้นเดิมที่ทำการเก็บข้อมูลซ้ำทุกครั้ง"),
                    "canopy_width": st.column_config.NumberColumn("Canopy Width (cm)", min_value=0.0, max_value=200.0, step=0.1, format="%.1f", help=METRIC_TOOLTIPS.get("canopy_width", "")),
                    "canopy_length": st.column_config.NumberColumn("Canopy Length (cm)", min_value=0.0, max_value=200.0, step=0.1, format="%.1f", help=METRIC_TOOLTIPS.get("canopy_length", "")),
                    "canopy_height": st.column_config.NumberColumn("Canopy Height (cm)", min_value=0.0, max_value=200.0, step=0.1, format="%.1f", help=METRIC_TOOLTIPS.get("canopy_height", "")),
                    "leaf_count": st.column_config.NumberColumn("Leaf Count", min_value=0, max_value=500, step=1, help=METRIC_TOOLTIPS.get("leaf_count", "")),
                    "hue_angle": st.column_config.NumberColumn("Hue Angle (°)", min_value=0.0, max_value=360.0, step=0.1, format="%.1f", help=METRIC_TOOLTIPS.get("hue_angle", ""))
                },
                use_container_width=True,
                num_rows="fixed"
            )
            
            # AUTOMATIC REAL-TIME SAVE TO SESSION & PERSISTENT DISK
            edited_df["record_date"] = date_str
            edited_df["week_no"] = calculated_week
            edited_df["treatment"] = trt_name
            edited_df["variety"] = data_schema.VARIETY_MAP.get(trt_name, "Green Moon")
            edited_df["lighting"] = data_schema.LIGHTING_MAP.get(trt_name, "Control")
            
            main_df = st.session_state.experiment_data
            if "record_date" in main_df.columns:
                main_df = main_df[~((main_df["record_date"] == date_str) & (main_df["treatment"] == trt_name))]
            else:
                main_df = main_df[~((main_df["week_no"] == calculated_week) & (main_df["treatment"] == trt_name))]
                
            st.session_state.experiment_data = pd.concat([main_df, edited_df], ignore_index=True)
            save_experiment_data_to_disk(st.session_state.experiment_data)
            
            save_c1, save_c2 = st.columns([1, 4])
            with save_c1:
                if st.button(f"💾 บันทึกข้อมูล ({trt_name})", key=f"btn_save_{trt_name}_{date_str}", use_container_width=True):
                    save_experiment_data_to_disk(st.session_state.experiment_data)
                    st.success(f"✅ บันทึกข้อมูลแปลง {trt_name} ประจำวันที่ {date_formatted} สำเร็จแล้ว!")
            with save_c2:
                st.caption(f"⚡ **Auto-Save Active**: ข้อมูลวันที่ {date_formatted} ({trt_name}) ถูกบันทึกถาวรเรียบร้อยแล้ว (รีเฟรช F5 ข้อมูลไม่หาย)")

# =============================================================================
# TAB 2: ENVIRONMENT & HIGH-FREQUENCY LOGGER ANALYTICS
# =============================================================================
with tab2:
    st.subheader("🌡️ High-Frequency Environmental Loggers & DLI Analytics")
    st.markdown("Upload PPFD (.csv) and Temp/Humidity (.xls/.xlsx/.csv) logger files with accumulative multi-upload support, custom plot naming, hourly aggregation, and Daily Light Integral (DLI) analysis.")
    
    t_log_import, t_log_hourly, t_log_dli, t_soil = st.tabs([
        "📂 Import Loggers & Channel Mapping", 
        "📈 Hourly Temperature & PPFD Graphs", 
        "☀️ Daily Light Integral (DLI) Analytics",
        "🌱 Soil Chemical Properties"
    ])
    
    # -------------------------------------------------------------------------
    # Sub-tab 1: Import Loggers & Custom Channel Mapping
    # -------------------------------------------------------------------------
    with t_log_import:
        st.markdown("#### 📂 Upload Environmental Logger Data Files")
        st.info("💡 **Accumulative Multi-Upload Supported**: รองรับการอัปโหลดไฟล์ Logger หลายครั้งติดต่อกัน ระบบจะสะสมและตัดข้อมูลซ้ำตามวันที่และเวลาให้อัตโนมัติ")
        
        up_col1, up_col2 = st.columns(2)
        
        with up_col1:
            st.markdown("##### ☀️ 1. PPFD Light Logger (.csv)")
            ppfd_file = st.file_uploader(
                "Upload HOBO PPFD CSV File", 
                type=["csv"], 
                key="ppfd_logger_uploader",
                help="อัปโหลดไฟล์ PPFD CSV จากเครื่อง HOBO Logger (เช่น 2026-07-10 ppfd.csv)"
            )
            if ppfd_file is not None:
                new_ppfd_df, par_cols = logger_processing.parse_ppfd_csv(ppfd_file, downsample_hourly=True)
                if not new_ppfd_df.empty:
                    st.session_state.logger_ppfd = logger_processing.merge_accumulative_logger_data(
                        st.session_state.get("logger_ppfd", pd.DataFrame()), 
                        new_ppfd_df
                    )
                    logger_processing.save_logger_storage_disk(st.session_state.logger_ppfd, st.session_state.logger_temp)
                    st.success(f"✅ เพิ่มข้อมูล PPFD เรียบร้อยแล้ว! รวมทั้งหมด {len(st.session_state.logger_ppfd):,} เรคคอร์ดรายชั่วโมง")
                else:
                    st.error("ไม่สามารถอ่านโครงสร้างไฟล์ PPFD CSV ได้")
                    
        with up_col2:
            st.markdown("##### 🌡️ 2. Temperature / Humidity Logger (.xls / .xlsx / .csv)")
            temp_file = st.file_uploader(
                "Upload Temperature Logger XLS/CSV File", 
                type=["xls", "xlsx", "csv"], 
                key="temp_logger_uploader",
                help="อัปโหลดไฟล์อุณหภูมิ (.xls, .xlsx, .csv) จากเครื่อง Logger (เช่น 2026-07-20 T หอมห่อ.xls)"
            )
            if temp_file is not None:
                new_temp_df, temp_cols = logger_processing.parse_temp_excel_or_csv(temp_file.getvalue(), temp_file.name, downsample_hourly=True)
                if not new_temp_df.empty:
                    st.session_state.logger_temp = logger_processing.merge_accumulative_logger_data(
                        st.session_state.get("logger_temp", pd.DataFrame()), 
                        new_temp_df
                    )
                    logger_processing.save_logger_storage_disk(st.session_state.logger_ppfd, st.session_state.logger_temp)
                    st.success(f"✅ เพิ่มข้อมูลอุณหภูมิเรียบร้อยแล้ว! รวมทั้งหมด {len(st.session_state.logger_temp):,} เรคคอร์ดรายชั่วโมง")
                else:
                    st.error("ไม่สามารถอ่านโครงสร้างไฟล์อุณหภูมิได้")
                    
        st.markdown("---")
        
        # Display Current Logger Status (Formatted as dd/mm/yyyy)
        st.markdown("#### 📊 Accumulative Logger Status Summary")
        stat_c1, stat_c2, stat_c3, stat_c4 = st.columns(4)
        
        df_ppfd_curr = st.session_state.get("logger_ppfd", pd.DataFrame())
        df_temp_curr = st.session_state.get("logger_temp", pd.DataFrame())
        
        with stat_c1:
            ppfd_count = len(df_ppfd_curr) if not df_ppfd_curr.empty else 0
            st.metric("☀️ Total PPFD Records", f"{ppfd_count:,} Rows", "Hourly Aggregated")
        with stat_c2:
            temp_count = len(df_temp_curr) if not df_temp_curr.empty else 0
            st.metric("🌡️ Total Temp Records", f"{temp_count:,} Rows", "Hourly Aggregated")
        with stat_c3:
            if not df_ppfd_curr.empty and 'datetime' in df_ppfd_curr.columns:
                p_start = pd.to_datetime(df_ppfd_curr['datetime']).min().strftime('%d/%m/%Y')
                p_end = pd.to_datetime(df_ppfd_curr['datetime']).max().strftime('%d/%m/%Y')
                st.metric("📅 PPFD Date Range", f"{p_start} to {p_end}")
            else:
                st.metric("📅 PPFD Date Range", "No Data")
        with stat_c4:
            if not df_temp_curr.empty and 'datetime' in df_temp_curr.columns:
                t_start = pd.to_datetime(df_temp_curr['datetime']).min().strftime('%d/%m/%Y')
                t_end = pd.to_datetime(df_temp_curr['datetime']).max().strftime('%d/%m/%Y')
                st.metric("📅 Temp Date Range", f"{t_start} to {t_end}")
            else:
                st.metric("📅 Temp Date Range", "No Data")
                
        st.markdown("---")
        
        # Custom Channel / Plot Naming Section
        st.markdown("#### 🏷️ ตั้งชื่อแปลงทดลอง / เซนเซอร์ PPFD (Custom Channel Mapping)")
        st.markdown("กำหนดชื่อแปลงทดลองของแต่ละเซนเซอร์ PPFD เพื่อนำไปใช้แสดงผลในกราฟรายชั่วโมงและตาราง DLI")
        
        par_cols_detected = [c for c in df_ppfd_curr.columns if c != 'datetime'] if not df_ppfd_curr.empty else [
            "PAR, µmol/m²/s (Channel 1)", "PAR, µmol/m²/s (Channel 2)", 
            "PAR, µmol/m²/s (Channel 3)", "PAR, µmol/m²/s (Channel 4)"
        ]
        
        curr_map = st.session_state.get("ppfd_channel_mapping", {})
        default_names = TREATMENTS[:len(par_cols_detected)]
        
        new_mapping = {}
        map_cols = st.columns(len(par_cols_detected))
        for idx, col_name in enumerate(par_cols_detected):
            with map_cols[idx % len(map_cols)]:
                default_label = curr_map.get(col_name, default_names[idx] if idx < len(default_names) else f"Plot {idx+1}")
                user_label = st.text_input(
                    f"Channel {idx+1}", 
                    value=default_label,
                    key=f"chan_map_{idx}",
                    help=f"ชื่อคอลัมน์เดิม: {col_name}"
                )
                new_mapping[col_name] = user_label
                
        st.session_state.ppfd_channel_mapping = new_mapping
        st.caption("📌 **สถานะ**: ชื่อแปลงทดลองจะถูกนำไปใช้อัตโนมัติในการสร้างกราฟรายชั่วโมงและการคำนวณค่า DLI")

    # -------------------------------------------------------------------------
    # Sub-tab 2: Hourly Temperature & PPFD Graphs (Formatted dd/mm/yyyy)
    # -------------------------------------------------------------------------
    with t_log_hourly:
        st.markdown("#### 📈 Hourly Environmental & PPFD Analytics")
        st.markdown("สรุปข้อมูลสภาพแวดล้อมและค่าความเข้มแสง PPFD เป็นรายชั่วโมง (Hourly Means)")
        
        df_ppfd_curr = st.session_state.get("logger_ppfd", pd.DataFrame())
        df_temp_curr = st.session_state.get("logger_temp", pd.DataFrame())
        
        if df_ppfd_curr.empty and df_temp_curr.empty:
            st.info("📌 ยังไม่มีข้อมูลจากไฟล์ Logger กรุณาอัปโหลดไฟล์ PPFD CSV หรือ Temp XLS ในแท็บ 'Import Loggers & Channel Mapping'")
        else:
            # Dynamic Date Range Filter Selector (format DD/MM/YYYY)
            all_log_dates = []
            if not df_ppfd_curr.empty and 'datetime' in df_ppfd_curr.columns:
                all_log_dates.extend(pd.to_datetime(df_ppfd_curr['datetime']).dt.date.dropna().tolist())
            if not df_temp_curr.empty and 'datetime' in df_temp_curr.columns:
                all_log_dates.extend(pd.to_datetime(df_temp_curr['datetime']).dt.date.dropna().tolist())
                
            if all_log_dates:
                min_log_d = min(all_log_dates)
                max_log_d = max(all_log_dates)
                
                c_filter, c_blank = st.columns([2, 1])
                with c_filter:
                    sel_log_range = st.date_input(
                        "📅 เลือกช่วงวันที่ต้องการแสดงผลกราฟ (Date Range Filter)",
                        value=(min_log_d, max_log_d),
                        min_value=min_log_d,
                        max_value=max_log_d,
                        format="DD/MM/YYYY",
                        key="hourly_date_range_filter",
                        help="เลือกช่วงวันที่เริ่มต้นและสิ้นสุดเพื่อกรองแสดงผลกราฟเส้นอุณหภูมิและ PPFD รายชั่วโมง (รูปแบบ dd/mm/yyyy)"
                    )
                st.markdown("---")
            else:
                sel_log_range = None

            # 1. Hourly Temperature Chart
            if not df_temp_curr.empty and 'datetime' in df_temp_curr.columns:
                temp_val_cols = [c for c in df_temp_curr.columns if c != 'datetime']
                hourly_t = logger_processing.compute_hourly_logger_aggregates(df_temp_curr, temp_val_cols)
                
                if sel_log_range and isinstance(sel_log_range, (tuple, list)) and len(sel_log_range) == 2:
                    s_d, e_d = sel_log_range[0], sel_log_range[1]
                    hourly_t['date_only'] = pd.to_datetime(hourly_t['datetime']).dt.date
                    hourly_t = hourly_t[(hourly_t['date_only'] >= s_d) & (hourly_t['date_only'] <= e_d)].drop(columns=['date_only'])
                
                if not hourly_t.empty:
                    st.markdown("##### 🌡️ Hourly Mean Temperature (°C)")
                    fig_temp = px.line(
                        hourly_t, 
                        x='datetime', 
                        y=temp_val_cols, 
                        title="Hourly Greenhouse Temperature Trajectory",
                        labels={"datetime": "Date & Time", "value": "Temperature (°C)", "variable": "Sensor Channel"},
                        template="plotly_white"
                    )
                    fig_temp.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1))
                    fig_temp.update_xaxes(tickformat="%d/%m/%Y %H:%M")
                    st.plotly_chart(fig_temp, use_container_width=True, key="hourly_temp_chart")
                    
            st.markdown("---")
            
            # 2. Hourly PPFD Chart
            if not df_ppfd_curr.empty and 'datetime' in df_ppfd_curr.columns:
                par_val_cols = [c for c in df_ppfd_curr.columns if c != 'datetime']
                hourly_p = logger_processing.compute_hourly_logger_aggregates(df_ppfd_curr, par_val_cols)
                
                if sel_log_range and isinstance(sel_log_range, (tuple, list)) and len(sel_log_range) == 2:
                    s_d, e_d = sel_log_range[0], sel_log_range[1]
                    hourly_p['date_only'] = pd.to_datetime(hourly_p['datetime']).dt.date
                    hourly_p = hourly_p[(hourly_p['date_only'] >= s_d) & (hourly_p['date_only'] <= e_d)].drop(columns=['date_only'])
                
                if not hourly_p.empty:
                    st.markdown("##### ☀️ Hourly Mean PPFD (μmol/m²/s) by Plot")
                    
                    # Rename columns to user custom mapping
                    rename_dict = st.session_state.get("ppfd_channel_mapping", {})
                    hourly_p_mapped = hourly_p.rename(columns=rename_dict)
                    mapped_cols = [rename_dict.get(c, c) for c in par_val_cols]
                    
                    fig_ppfd = px.line(
                        hourly_p_mapped, 
                        x='datetime', 
                        y=mapped_cols, 
                        title="Hourly Photosynthetic Photon Flux Density (PPFD) Trajectory",
                        labels={"datetime": "Date & Time", "value": "PPFD (μmol/m²/s)", "variable": "Experimental Plot"},
                        template="plotly_white",
                        color_discrete_map=COLOR_PALETTE
                    )
                    fig_ppfd.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1))
                    fig_ppfd.update_xaxes(tickformat="%d/%m/%Y %H:%M")
                    st.plotly_chart(fig_ppfd, use_container_width=True, key="hourly_ppfd_chart")

    # -------------------------------------------------------------------------
    # Sub-tab 3: Daily Light Integral (DLI) Analytics (Formatted dd/mm/yyyy)
    # -------------------------------------------------------------------------
    with t_log_dli:
        st.markdown("#### ☀️ Daily Light Integral (DLI) Analytics")
        st.markdown("คำนวณปริมาณแสงสะสมรายวัน (Daily Light Integral: DLI) ในหน่วย **mol/m²/day** สำหรับแต่ละแปลงทดลอง")
        
        df_ppfd_curr = st.session_state.get("logger_ppfd", pd.DataFrame())
        
        if df_ppfd_curr.empty:
            st.info("📌 ยังไม่มีข้อมูล PPFD Logger กรุณาอัปโหลดไฟล์ PPFD CSV ในแท็บ 'Import Loggers & Channel Mapping'")
        else:
            mapping = st.session_state.get("ppfd_channel_mapping", {})
            dli_df = logger_processing.compute_daily_dli(df_ppfd_curr, mapping)
            
            if not dli_df.empty:
                # Date Range Filter for DLI (Format DD/MM/YYYY)
                dli_dates = pd.to_datetime(dli_df['Date'], format='%d/%m/%Y', errors='coerce').dt.date.dropna().tolist()
                if dli_dates:
                    min_dli_d, max_dli_d = min(dli_dates), max(dli_dates)
                    c_dli_f, _ = st.columns([2, 1])
                    with c_dli_f:
                        sel_dli_range = st.date_input(
                            "📅 เลือกช่วงวันที่ต้องการแสดงผล DLI (DLI Date Range Filter)",
                            value=(min_dli_d, max_dli_d),
                            min_value=min_dli_d,
                            max_value=max_dli_d,
                            format="DD/MM/YYYY",
                            key="dli_date_range_filter",
                            help="เลือกช่วงวันที่เริ่มต้นและสิ้นสุดเพื่อกรองแสดงผล DLI (รูปแบบ dd/mm/yyyy)"
                        )
                    st.markdown("---")
                    
                    if isinstance(sel_dli_range, (tuple, list)) and len(sel_dli_range) == 2:
                        s_dli, e_dli = sel_dli_range[0], sel_dli_range[1]
                        dli_df['date_obj'] = pd.to_datetime(dli_df['Date'], format='%d/%m/%Y', errors='coerce').dt.date
                        dli_df = dli_df[(dli_df['date_obj'] >= s_dli) & (dli_df['date_obj'] <= e_dli)].drop(columns=['date_obj'])

                # Top DLI Metrics
                st.markdown("##### 📊 Mean Daily Light Integral Summary")
                dli_cols = [c for c in dli_df.columns if c != 'Date']
                
                m_cols = st.columns(len(dli_cols)) if dli_cols else [st.container()]
                for idx, col in enumerate(dli_cols):
                    mean_val = round(dli_df[col].dropna().mean(), 2) if not dli_df[col].dropna().empty else 0.0
                    max_val = round(dli_df[col].dropna().max(), 2) if not dli_df[col].dropna().empty else 0.0
                    with m_cols[idx % len(m_cols)]:
                        st.metric(f"☀️ DLI {col}", f"{mean_val} mol/m²/d", f"Peak: {max_val} mol/m²/d")
                        
                st.markdown("---")
                
                # Interactive DLI Chart
                st.markdown("##### 📈 Daily Light Integral (DLI) Comparison Bar & Line Chart")
                fig_dli = px.bar(
                    dli_df,
                    x='Date',
                    y=dli_cols,
                    barmode='group',
                    title="Daily Light Integral (DLI) Across Experimental Plots (mol/m²/day)",
                    labels={"Date": "Measurement Date (dd/mm/yyyy)", "value": "DLI (mol/m²/day)", "variable": "Experimental Plot"},
                    template="plotly_white",
                    color_discrete_map=COLOR_PALETTE
                )
                fig_dli.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig_dli, use_container_width=True, key="daily_dli_chart")
                
                st.markdown("---")
                st.markdown("##### 📋 Daily DLI Summary Data Table")
                st.dataframe(dli_df, use_container_width=True)
                
                # CSV Export button for DLI Data
                dli_csv = dli_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📄 Download Daily DLI Dataset (.csv)",
                    data=dli_csv,
                    file_name="daily_dli_summary.csv",
                    mime="text/csv"
                )

    # -------------------------------------------------------------------------
    # Sub-tab 4: Soil Chemical Properties & Manual Environmental Entry
    # -------------------------------------------------------------------------
    with t_soil:
        st.markdown("#### 🌱 Soil Chemical Properties & Greenhouse Loggers")
        st.markdown("Record greenhouse weekly averages and soil chemical properties.")
        
        env_df = st.session_state.env_data.copy()
        soil_cols = ["week_no", "soil_ph", "soil_ec", "soil_om", "soil_total_n", "soil_avail_p", "soil_avail_k", "soil_texture"]
        
        if env_df.empty:
            st.info("ยังไม่มีข้อมูลสภาพแวดล้อม กรุณาโหลดแม่แบบเพื่อเริ่มกรอกข้อมูล")
            if st.button("โหลดแม่แบบ 4 สัปดาห์", key="btn_load_env_template"):
                st.session_state.env_data = generate_env_template()
                save_env_data_to_disk(st.session_state.env_data)
                st.success("โหลดแม่แบบสภาพแวดล้อมเรียบร้อยแล้ว")
                st.rerun()
        else:
            edited_soil_df = st.data_editor(
                env_df[soil_cols],
                key="soil_data_editor",
                column_config={
                    "week_no": st.column_config.NumberColumn("Week", disabled=True),
                    "soil_ph": st.column_config.NumberColumn("Soil pH", min_value=1.0, max_value=14.0, step=0.1, format="%.1f", help=METRIC_TOOLTIPS.get("soil_ph", "")),
                    "soil_ec": st.column_config.NumberColumn("Soil EC (dS/m)", min_value=0.0, max_value=10.0, step=0.01, format="%.2f", help=METRIC_TOOLTIPS.get("soil_ec", "")),
                    "soil_om": st.column_config.NumberColumn("Organic Matter (%)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f", help=METRIC_TOOLTIPS.get("soil_om", "")),
                    "soil_total_n": st.column_config.NumberColumn("Total Nitrogen (%)", min_value=0.0, max_value=10.0, step=0.01, format="%.2f", help=METRIC_TOOLTIPS.get("soil_total_n", "")),
                    "soil_avail_p": st.column_config.NumberColumn("Avail. P (mg/kg)", min_value=0.0, max_value=500.0, step=0.1, format="%.1f", help=METRIC_TOOLTIPS.get("soil_avail_p", "")),
                    "soil_avail_k": st.column_config.NumberColumn("Avail. K (mg/kg)", min_value=0.0, max_value=1000.0, step=0.1, format="%.1f", help=METRIC_TOOLTIPS.get("soil_avail_k", "")),
                    "soil_texture": st.column_config.SelectboxColumn("Soil Texture", options=["Sandy Loam", "Loam", "Clay Loam", "Silt Loam"], help="ลักษณะเนื้อดินปลูกในแปลงทดลอง")
                },
                use_container_width=True,
                num_rows="fixed"
            )
            for col in ["soil_ph", "soil_ec", "soil_om", "soil_total_n", "soil_avail_p", "soil_avail_k", "soil_texture"]:
                st.session_state.env_data[col] = edited_soil_df[col]
            save_env_data_to_disk(st.session_state.env_data)
            
            if st.button("💾 บันทึกข้อมูลเคมีดิน", key="btn_save_soil"):
                save_env_data_to_disk(st.session_state.env_data)
                st.success("✅ บันทึกข้อมูลเคมีดินเรียบร้อยแล้ว!")

# =============================================================================
# TAB 3: HARVEST & LAB RESULTS ENTRY (Separated by Treatment Sub-Tabs)
# =============================================================================
with tab3:
    st.subheader("🔬 Harvest Yield & Spectrophotometric Lab Entry")
    st.markdown("Input harvest metrics and UV-Vis OD absorbances organized cleanly by Treatment Sub-Tabs (Auto-Save & Save Button).")
    
    t_harvest, t_phytochem = st.tabs(["🌾 Harvest Yield Measurements", "🧪 UV-Vis Spectrophotometer Absorbance"])
    
    with t_harvest:
        st.markdown("#### 🌾 Harvest Yield Entry by Treatment")
        st.info("⚡ **Persistent Auto-Save Active**: ข้อมูลผลผลิตถูกบันทึกลงดิสก์ถาวรอัตโนมัติทันทีที่กรอก และสามารถกดปุ่มบันทึกเพื่อยืนยันได้ตลอดเวลา")
        
        sub_h_tabs = st.tabs(TREATMENTS)
        df_exp_h = st.session_state.experiment_data.copy()
        
        for idx, trt_name in enumerate(TREATMENTS):
            with sub_h_tabs[idx]:
                st.markdown(f"#### แปลงทดลอง: **{trt_name}** (Harvest Yield Data)")
                sub_h_df = df_exp_h[df_exp_h["treatment"] == trt_name].copy()
                
                existing_pids = set(sub_h_df["plant_id"].tolist()) if not sub_h_df.empty else set()
                missing_pids = [pid for pid in PLANT_IDS if pid not in existing_pids]
                
                if missing_pids:
                    new_rows = []
                    for pid in missing_pids:
                        new_rows.append({
                            "week_no": 4,
                            "variety": data_schema.VARIETY_MAP.get(trt_name, "Green Moon"),
                            "lighting": data_schema.LIGHTING_MAP.get(trt_name, "Control"),
                            "treatment": trt_name,
                            "plant_id": pid,
                            "fresh_weight": np.nan,
                            "root_length": np.nan,
                            "core_length": np.nan,
                            "head_diameter": np.nan,
                            "head_firmness": np.nan
                        })
                    sub_h_df = pd.concat([sub_h_df, pd.DataFrame(new_rows)], ignore_index=True)
                    
                sub_h_df["pid_order"] = pd.Categorical(sub_h_df["plant_id"], categories=PLANT_IDS, ordered=True)
                sub_h_df = sub_h_df.sort_values("pid_order").drop(columns=["pid_order"])
                
                display_cols = ["plant_id", "fresh_weight", "root_length", "core_length", "head_diameter", "head_firmness"]
                for col in display_cols:
                    if col not in sub_h_df.columns:
                        sub_h_df[col] = np.nan
                        
                edited_h_df = st.data_editor(
                    sub_h_df[display_cols],
                    key=f"editor_harvest_{trt_name}",
                    column_config={
                        "plant_id": st.column_config.TextColumn("Plant ID (ต้นที่กำหนด - ค่าคงที่)", disabled=True, help="รหัสต้นพืชคงที่ 10 ต้นเดิมที่ทำการเก็บเกี่ยว"),
                        "fresh_weight": st.column_config.NumberColumn("Fresh Weight (g)", min_value=0.0, max_value=1000.0, step=0.1, format="%.1f", help=METRIC_TOOLTIPS.get("fresh_weight", "")),
                        "root_length": st.column_config.NumberColumn("Root Length (cm)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f", help=METRIC_TOOLTIPS.get("root_length", "")),
                        "core_length": st.column_config.NumberColumn("Core Length (cm)", min_value=0.0, max_value=50.0, step=0.1, format="%.1f", help=METRIC_TOOLTIPS.get("core_length", "")),
                        "head_diameter": st.column_config.NumberColumn("Head Diameter (cm)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f", help=METRIC_TOOLTIPS.get("head_diameter", "")),
                        "head_firmness": st.column_config.NumberColumn("Head Firmness Index", min_value=1.0, max_value=5.0, step=0.1, format="%.1f", help=METRIC_TOOLTIPS.get("head_firmness", ""))
                    },
                    use_container_width=True,
                    num_rows="fixed"
                )
                
                # Auto-save logic
                edited_h_df["treatment"] = trt_name
                edited_h_df["variety"] = data_schema.VARIETY_MAP.get(trt_name, "Green Moon")
                edited_h_df["lighting"] = data_schema.LIGHTING_MAP.get(trt_name, "Control")
                
                main_df = st.session_state.experiment_data
                for _, row in edited_h_df.iterrows():
                    pid = row["plant_id"]
                    mask = (main_df["treatment"] == trt_name) & (main_df["plant_id"] == pid)
                    if mask.any():
                        for col in ["fresh_weight", "root_length", "core_length", "head_diameter", "head_firmness"]:
                            main_df.loc[mask, col] = row[col]
                    else:
                        main_df = pd.concat([main_df, pd.DataFrame([row])], ignore_index=True)
                        
                st.session_state.experiment_data = main_df
                save_experiment_data_to_disk(main_df)
                
                save_c1, save_c2 = st.columns([1, 4])
                with save_c1:
                    if st.button(f"💾 บันทึกผลเก็บเกี่ยว ({trt_name})", key=f"btn_save_harvest_{trt_name}", use_container_width=True):
                        save_experiment_data_to_disk(st.session_state.experiment_data)
                        st.success(f"✅ บันทึกข้อมูลผลผลิตเก็บเกี่ยวแปลง {trt_name} สำเร็จแล้ว!")
                with save_c2:
                    st.caption(f"⚡ **Auto-Save Active**: ข้อมูลผลผลิต ({trt_name}) ถูกบันทึกถาวรเรียบร้อยแล้ว (รีเฟรช F5 ข้อมูลไม่หาย)")

    with t_phytochem:
        st.markdown("#### 🧪 UV-Vis Spectrophotometer Absorbance by Treatment")
        st.info("💡 **Gratani Equations Active**: คำนวณปริมาณสารสำคัญพฤกษเคมีอัตโนมัติคงทนตามน้ำหนักตัวอย่าง (`sample_weight_g`)")
        
        sub_p_tabs = st.tabs(TREATMENTS)
        df_exp_p = st.session_state.experiment_data.copy()
        
        for idx, trt_name in enumerate(TREATMENTS):
            with sub_p_tabs[idx]:
                st.markdown(f"#### แปลงทดลอง: **{trt_name}** (Lab OD Absorbance Data)")
                sub_p_df = df_exp_p[df_exp_p["treatment"] == trt_name].copy()
                
                existing_pids = set(sub_p_df["plant_id"].tolist()) if not sub_p_df.empty else set()
                missing_pids = [pid for pid in PLANT_IDS if pid not in existing_pids]
                
                if missing_pids:
                    new_rows = []
                    for pid in missing_pids:
                        new_rows.append({
                            "week_no": 4,
                            "variety": data_schema.VARIETY_MAP.get(trt_name, "Green Moon"),
                            "lighting": data_schema.LIGHTING_MAP.get(trt_name, "Control"),
                            "treatment": trt_name,
                            "plant_id": pid,
                            "sample_weight_g": np.nan,
                            "OD663": np.nan,
                            "OD645": np.nan,
                            "OD470": np.nan,
                            "OD765": np.nan
                        })
                    sub_p_df = pd.concat([sub_p_df, pd.DataFrame(new_rows)], ignore_index=True)
                    
                sub_p_df["pid_order"] = pd.Categorical(sub_p_df["plant_id"], categories=PLANT_IDS, ordered=True)
                sub_p_df = sub_p_df.sort_values("pid_order").drop(columns=["pid_order"])
                
                display_cols = ["plant_id", "sample_weight_g", "OD663", "OD645", "OD470", "OD765"]
                for col in display_cols:
                    if col not in sub_p_df.columns:
                        sub_p_df[col] = np.nan
                        
                edited_p_df = st.data_editor(
                    sub_p_df[display_cols],
                    key=f"editor_phytochem_{trt_name}",
                    column_config={
                        "plant_id": st.column_config.TextColumn("Plant ID (ต้นที่กำหนด - ค่าคงที่)", disabled=True, help="รหัสต้นพืชคงที่ 10 ต้นเดิม"),
                        "sample_weight_g": st.column_config.NumberColumn("Sample Weight (g)", min_value=0.01, max_value=10.0, step=0.01, format="%.3f", help="น้ำหนักสดตัวอย่างใบผักกาดหอม (กรัม)"),
                        "OD663": st.column_config.NumberColumn("OD 663 nm", min_value=0.0, max_value=3.0, step=0.001, format="%.3f", help="ค่าความหนาแน่นเชิงแสง 663 nm (Chl a)"),
                        "OD645": st.column_config.NumberColumn("OD 645 nm", min_value=0.0, max_value=3.0, step=0.001, format="%.3f", help="ค่าความหนาแน่นเชิงแสง 645 nm (Chl b)"),
                        "OD470": st.column_config.NumberColumn("OD 470 nm", min_value=0.0, max_value=3.0, step=0.001, format="%.3f", help="ค่าความหนาแน่นเชิงแสง 470 nm (Carotenoids)"),
                        "OD765": st.column_config.NumberColumn("OD 765 nm", min_value=0.0, max_value=3.0, step=0.001, format="%.3f", help="ค่าความหนาแน่นเชิงแสง 765 nm (Total Phenolics)")
                    },
                    use_container_width=True,
                    num_rows="fixed"
                )
                
                # Auto-save & calculate
                edited_p_df["treatment"] = trt_name
                edited_p_df["variety"] = data_schema.VARIETY_MAP.get(trt_name, "Green Moon")
                edited_p_df["lighting"] = data_schema.LIGHTING_MAP.get(trt_name, "Control")
                
                main_df = st.session_state.experiment_data
                for _, row in edited_p_df.iterrows():
                    pid = row["plant_id"]
                    mask = (main_df["treatment"] == trt_name) & (main_df["plant_id"] == pid)
                    if mask.any():
                        for col in ["sample_weight_g", "OD663", "OD645", "OD470", "OD765"]:
                            main_df.loc[mask, col] = row[col]
                    else:
                        main_df = pd.concat([main_df, pd.DataFrame([row])], ignore_index=True)
                        
                main_df = apply_phytochemical_calculations(main_df)
                st.session_state.experiment_data = main_df
                save_experiment_data_to_disk(main_df)
                
                save_c1, save_c2 = st.columns([1, 4])
                with save_c1:
                    if st.button(f"💾 บันทึกแล็บ OD ({trt_name})", key=f"btn_save_phyto_{trt_name}", use_container_width=True):
                        save_experiment_data_to_disk(st.session_state.experiment_data)
                        st.success(f"✅ บันทึกข้อมูลและคำนวณผลแล็บแปลง {trt_name} สำเร็จแล้ว!")
                with save_c2:
                    st.caption(f"⚡ **Auto-Save Active**: ข้อมูลสเปกโตรโฟโตมิเตอร์ ({trt_name}) ถูกบันทึกและคำนวณผลเรียบร้อยแล้ว")
            
        st.markdown("---")
        st.markdown("#### 🌿 Calculated Phytochemical Summary")
        phyto_display_cols = ["week_no", "treatment", "plant_id", "sample_weight_g", "chl_a", "chl_b", "total_chl", "carotenoids", "total_phenolics"]
        st.dataframe(
            st.session_state.experiment_data[phyto_display_cols].dropna(subset=["chl_a"]),
            use_container_width=True
        )

# =============================================================================
# TAB 4: STATISTICAL ANALYTICS & RESEARCH GRAPHS
# =============================================================================
with tab4:
    st.subheader("📊 Statistical Analytics & Research Charts")
    
    df_exp = st.session_state.experiment_data.copy()
    valid_df = df_exp.dropna(subset=["canopy_width", "fresh_weight", "total_chl"], how="all") if not df_exp.empty else pd.DataFrame()
    
    if valid_df.empty:
        st.info("📌 ยังไม่มีข้อมูลตัวเลขสำหรับการวิเคราะห์ทางสถิติ กรุณากรอกข้อมูลตัวเลขในตารางบันทึก หรืออัปโหลดไฟล์ Excel/CSV ข้อมูลวิจัยจริง")
    else:
        c_sel1, c_sel2 = st.columns([2, 1])
        with c_sel1:
            selected_metric_key = st.selectbox(
                "Select Parameter for Statistical Analysis",
                options=list(ALL_ANALYSIS_METRICS.keys()),
                format_func=lambda k: ALL_ANALYSIS_METRICS[k],
                help="เลือกตัวแปรพฤกษศาสตร์/เคมีที่ต้องการนำมาวิเคราะห์ทางสถิติ"
            )
            selected_metric_label = ALL_ANALYSIS_METRICS[selected_metric_key]
            
        with c_sel2:
            all_weeks = sorted(df_exp["week_no"].unique().tolist())
            selected_analysis_week = st.selectbox(
                "Filter by Week (or All Weeks)",
                options=["All Weeks"] + all_weeks,
                index=len(all_weeks) if all_weeks else 0,
                help="กรองวิเคราะห์ข้อมูลเฉพาะสัปดาห์การวัดที่ต้องการ หรือเลือก All Weeks เพื่อวิเคราะห์รวมทุกสัปดาห์"
            )
            
        filtered_df = df_exp.copy()
        if selected_analysis_week != "All Weeks":
            filtered_df = filtered_df[filtered_df["week_no"] == selected_analysis_week]
            
        st.markdown("---")
        
        # 1. Descriptive Summary Table
        st.markdown(f"### 📋 Descriptive Statistics: {selected_metric_label}")
        desc_df = calculate_descriptive_stats(filtered_df, selected_metric_key, group_by="treatment")
        if not desc_df.empty:
            st.dataframe(desc_df[["treatment", "Count", "Mean_±_SD", "Min", "Max"]], use_container_width=True)
        else:
            st.info("No numerical observations found for the selected parameter.")
            
        st.markdown("---")
        
        # 2. Two-Way ANOVA & Post-Hoc Test
        st.markdown(f"### 🧪 Two-Way ANOVA (Variety × Lighting)")
        anova_res = run_two_way_anova(filtered_df, selected_metric_key)
        
        if "error" in anova_res:
            st.info(anova_res["error"])
        else:
            a_col1, a_col2, a_col3 = st.columns(3)
            with a_col1:
                p_var = anova_res["p_variety"]
                st.metric(
                    "Factor 1: Variety Effect", 
                    f"p = {p_var:.4f}", 
                    "Significant (p < 0.05)" if p_var < 0.05 else "Not Significant",
                    help="วิเคราะห์อิทธิพลของปัจจัยสายพันธุ์ผักกาดหอม (Green Moon vs Fame) ว่าส่งผลต่อตัวแปรค่าวัดอย่างมีนัยสำคัญทางสถิติหรือไม่ (p < 0.05)"
                )
                st.caption("📌 อิทธิพลของปัจจัยสายพันธุ์ผักกาดหอม")
            with a_col2:
                p_light = anova_res["p_lighting"]
                st.metric(
                    "Factor 2: Lighting Effect", 
                    f"p = {p_light:.4f}", 
                    "Significant (p < 0.05)" if p_light < 0.05 else "Not Significant",
                    help="วิเคราะห์อิทธิพลของปัจจัยแสงเสริม LED เทียบกับแสงธรรมชาติ (p < 0.05 หมายถึงแสงเสริมส่งผลต่อค่าวัดอย่างมีนัยสำคัญ)"
                )
                st.caption("📌 อิทธิพลของปัจจัยแสงเสริม LED")
            with a_col3:
                p_int = anova_res["p_interaction"]
                st.metric(
                    "Interaction: Variety × Lighting", 
                    f"p = {p_int:.4f}", 
                    "Significant (p < 0.05)" if p_int < 0.05 else "Not Significant",
                    help="วิเคราะห์ผลร่วม (Interaction Effect) ระหว่างสายพันธุ์และแสงเสริม LED ว่าส่งผลร่วมกันอย่างมีนัยสำคัญทางสถิติหรือไม่"
                )
                st.caption("📌 ผลร่วม (Interaction) สายพันธุ์ × แสงเสริม")
                
            with st.expander("📄 Detailed ANOVA Table & Model Summary"):
                st.caption("💡 **ตาราง Two-Way ANOVA**: แสดงค่า Sum of Squares (SS), Degrees of Freedom (df), F-statistic และ p-value")
                st.dataframe(anova_res["anova_table"], use_container_width=True)
                
            # Post-Hoc Tukey HSD
            tukey_res = run_tukey_hsd(filtered_df, selected_metric_key)
            if tukey_res is not None and not tukey_res.empty:
                with st.expander("🔍 Tukey HSD Post-Hoc Pairwise Comparisons"):
                    st.caption("💡 **ตาราง Tukey HSD**: เปรียบเทียบพหุคูณรายคู่เพื่อดูว่ากลุ่มการทดลองใดแตกต่างกันอย่างมีนัยสำคัญทางสถิติ (p < 0.05)")
                    st.dataframe(tukey_res, use_container_width=True)

        st.markdown("---")
        
        # 3. Interactive Plotly Charts
        st.markdown("### 📈 Interactive Research Visualizations")
        chart_t1, chart_t2, chart_t3, chart_t4 = st.tabs([
            "📊 Error Bar Chart", 
            "📦 Plant Boxplot", 
            "📈 Growth Trajectory", 
            "🔥 Pearson Correlation"
        ])
        
        with chart_t1:
            fig_bar = plot_treatment_bar_chart(
                df_exp, 
                selected_metric_key, 
                selected_metric_label,
                week_no=selected_analysis_week if selected_analysis_week != "All Weeks" else None
            )
            st.plotly_chart(fig_bar, use_container_width=True, key="analytics_bar_chart")
            
        with chart_t2:
            fig_box = plot_plant_boxplot(
                df_exp, 
                selected_metric_key, 
                selected_metric_label,
                week_no=selected_analysis_week if selected_analysis_week != "All Weeks" else None
            )
            st.plotly_chart(fig_box, use_container_width=True, key="analytics_box_chart")
            
        with chart_t3:
            fig_line = plot_growth_trajectory(df_exp, selected_metric_key, selected_metric_label)
            st.plotly_chart(fig_line, use_container_width=True, key="analytics_line_chart")
            
        with chart_t4:
            joined_df = df_exp.merge(st.session_state.env_data, on="week_no", how="left")
            num_cols = ["canopy_width", "canopy_length", "canopy_height", "leaf_count", "fresh_weight", "total_chl", "carotenoids", "total_phenolics", "temp_c", "ppfd_led_gm", "soil_ph", "soil_ec", "soil_om"]
            corr_df, p_df = compute_pearson_correlation(joined_df, num_cols)
            fig_heat = plot_correlation_heatmap(corr_df, p_df)
            st.plotly_chart(fig_heat, use_container_width=True, key="analytics_heatmap_chart")
