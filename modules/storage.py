"""
Data Persistence and Storage Module for Head Lettuce Research Application.
Handles Session State initialization, IndexedDB integration, Excel multi-sheet parsing,
CSV saving/loading, and high-frequency environmental logger persistence.
"""

import os
import io
import datetime
import pandas as pd
import numpy as np
import streamlit as st
import modules.data_schema as data_schema
import modules.phytochemical as phytochemical
import modules.logger_processing as logger_processing

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
EXP_STORAGE_PATH = os.path.join(DATA_DIR, "saved_experiment_data.csv")
ENV_STORAGE_PATH = os.path.join(DATA_DIR, "saved_env_data.csv")


def ensure_all_columns_exist(df):
    """
    Ensures all required biological, lab, and environmental schema columns exist
    in the dataframe to prevent KeyError issues.
    """
    if df is None or df.empty:
        return pd.DataFrame()
        
    df_copy = df.copy()
    
    # Required biological & phytochemical columns
    req_cols = [
        "record_date", "week_no", "variety", "lighting", "treatment", "plant_id",
        "canopy_width", "canopy_length", "canopy_height", "leaf_count", "hue_angle",
        "fresh_weight", "root_length", "core_length", "head_diameter", "head_firmness",
        "sample_weight_g", "OD663", "OD645", "OD470", "OD765",
        "chl_a", "chl_b", "total_chl", "carotenoids", "total_phenolics"
    ]
    
    for col in req_cols:
        if col not in df_copy.columns:
            df_copy[col] = np.nan
            
    return df_copy


def generate_empty_dataset():
    """Generates an empty dataframe structured with all schema columns."""
    empty_df = pd.DataFrame(columns=[
        "record_date", "week_no", "variety", "lighting", "treatment", "plant_id",
        "canopy_width", "canopy_length", "canopy_height", "leaf_count", "hue_angle",
        "fresh_weight", "root_length", "core_length", "head_diameter", "head_firmness",
        "sample_weight_g", "OD663", "OD645", "OD470", "OD765",
        "chl_a", "chl_b", "total_chl", "carotenoids", "total_phenolics"
    ])
    return empty_df


def generate_empty_environment_data():
    """Generates an empty dataframe for 4 weeks of greenhouse and soil logger data."""
    env_rows = []
    for w in range(1, 5):
        env_rows.append({
            "week_no": w,
            "temp_c": np.nan,
            "ppfd_control_gm": np.nan,
            "ppfd_led_gm": np.nan,
            "ppfd_control_f": np.nan,
            "ppfd_led_f1": np.nan,
            "ppfd_led_f2": np.nan,
            "soil_ph": np.nan,
            "soil_ec": np.nan,
            "soil_om": np.nan,
            "soil_total_n": np.nan,
            "soil_avail_p": np.nan,
            "soil_avail_k": np.nan,
            "soil_texture": "Sandy Loam"
        })
    return pd.DataFrame(env_rows)


def load_experiment_data_from_disk():
    """Loads persistent experiment dataset from local CSV storage if available."""
    if os.path.exists(EXP_STORAGE_PATH):
        try:
            df = pd.read_csv(EXP_STORAGE_PATH)
            df = ensure_all_columns_exist(df)
            df = phytochemical.apply_phytochemical_calculations(df)
            return df
        except Exception:
            pass
    return generate_empty_dataset()


def load_env_data_from_disk():
    """Loads persistent environmental logger dataset from local CSV storage if available."""
    if os.path.exists(ENV_STORAGE_PATH):
        try:
            df = pd.read_csv(ENV_STORAGE_PATH)
            return df
        except Exception:
            pass
    return generate_empty_environment_data()


def save_experiment_data_to_disk(df):
    """Saves the experiment dataset to local CSV storage."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if df is not None and not df.empty:
        df_to_save = ensure_all_columns_exist(df)
        df_to_save.to_csv(EXP_STORAGE_PATH, index=False)


def save_env_data_to_disk(df):
    """Saves the environmental logger dataset to local CSV storage."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if df is not None and not df.empty:
        df.to_csv(ENV_STORAGE_PATH, index=False)


def clear_disk_storage():
    """Clears local persistent storage files."""
    if os.path.exists(EXP_STORAGE_PATH):
        try:
            os.remove(EXP_STORAGE_PATH)
        except Exception:
            pass
    if os.path.exists(ENV_STORAGE_PATH):
        try:
            os.remove(ENV_STORAGE_PATH)
        except Exception:
            pass


def initialize_session_state():
    """Initializes Streamlit session state keys with disk fallback."""
    if "experiment_data" not in st.session_state or st.session_state.experiment_data.empty:
        st.session_state.experiment_data = load_experiment_data_from_disk()
    else:
        st.session_state.experiment_data = ensure_all_columns_exist(st.session_state.experiment_data)
        
    if "env_data" not in st.session_state or st.session_state.env_data.empty:
        st.session_state.env_data = load_env_data_from_disk()
        
    if "logger_ppfd" not in st.session_state or "logger_temp" not in st.session_state:
        df_ppfd, df_temp = logger_processing.load_logger_storage_disk()
        st.session_state.logger_ppfd = df_ppfd
        st.session_state.logger_temp = df_temp
        
    if "ppfd_channel_mapping" not in st.session_state:
        st.session_state.ppfd_channel_mapping = {}


def parse_uploaded_excel(file_bytes):
    """Parses uploaded multi-sheet Excel files into the research schema."""
    try:
        excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
        sheet_names = excel_file.sheet_names
        
        col_rename = {
            'หมายเลขต้น': 'plant_id',
            'ความกว้างทรงพุ่ม (ซม.)': 'canopy_width',
            'ความยาวทรงพุ่ม (ซม.)': 'canopy_length',
            'ความสูงทรงพุ่ม (ซม.)': 'canopy_height',
            'จำนวนใบ': 'leaf_count',
            'มุมสี': 'hue_angle'
        }
        
        parsed_rows = []
        for sheet in sheet_names:
            if sheet in data_schema.TREATMENTS:
                sheet_df = pd.read_excel(excel_file, sheet_name=sheet)
                sheet_df = sheet_df.rename(columns=col_rename)
                sheet_df["treatment"] = sheet
                sheet_df["variety"] = data_schema.VARIETY_MAP.get(sheet, "Green Moon")
                sheet_df["lighting"] = data_schema.LIGHTING_MAP.get(sheet, "Control")
                if "record_date" not in sheet_df.columns:
                    sheet_df["record_date"] = "2026-08-04"
                if "week_no" not in sheet_df.columns:
                    sheet_df["week_no"] = 1
                parsed_rows.append(sheet_df)
                
        if parsed_rows:
            combined_df = pd.concat(parsed_rows, ignore_index=True)
            combined_df = ensure_all_columns_exist(combined_df)
            combined_df = phytochemical.apply_phytochemical_calculations(combined_df)
            return combined_df, "Successfully loaded multi-sheet Excel dataset!"
        else:
            df = pd.read_excel(excel_file, sheet_name=0)
            df = df.rename(columns=col_rename)
            df = ensure_all_columns_exist(df)
            df = phytochemical.apply_phytochemical_calculations(df)
            return df, "Loaded primary worksheet dataset!"
    except Exception as e:
        return pd.DataFrame(), f"Error parsing Excel file: {str(e)}"


def render_indexeddb_component():
    """Renders a browser client-side storage component for redundancy."""
    st.markdown("""
    <script>
    if ('indexedDB' in window) {
        let request = window.indexedDB.open('LettuceResearchDB', 1);
        request.onupgradeneeded = function(e) {
            let db = e.target.result;
            if (!db.objectStoreNames.contains('experiment_store')) {
                db.createObjectStore('experiment_store', { keyPath: 'id', autoIncrement: true });
            }
        };
    }
    </script>
    """, unsafe_allow_html=True)
