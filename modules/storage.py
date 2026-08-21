"""
Data Persistence and Storage Module for Head Lettuce Research Application.
Handles Session State initialization, IndexedDB integration, Excel multi-sheet parsing,
CSV saving/loading, and high-frequency environmental logger persistence.
"""

import os
import io
import re
import datetime
import pandas as pd
import numpy as np
import streamlit as st
import modules.data_schema as data_schema
import modules.phytochemical as phytochemical
import modules.logger_processing as logger_processing


def _normalize_sheet_name(sheet_name):
    """
    Normalizes a sheet name from the uploaded Excel file so it can match
    a canonical treatment name in data_schema.TREATMENTS.

    Handles the case where files use hyphens ('Control-GM', 'LED-F (1)')
    while the schema uses underscores ('Control_GM', 'LED_F (1)').

    Returns the matched canonical treatment name, or None if no match.
    """
    if sheet_name is None:
        return None
    candidate = str(sheet_name).strip()
    # Direct match
    if candidate in data_schema.TREATMENTS:
        return candidate
    # Hyphen -> underscore variant
    underscore_variant = candidate.replace("-", "_")
    if underscore_variant in data_schema.TREATMENTS:
        return underscore_variant
    # Underscore -> hyphen variant (rare, for safety)
    hyphen_variant = candidate.replace("_", "-")
    for trt in data_schema.TREATMENTS:
        if trt.replace("_", "-") == candidate:
            return trt
    return None


def _extract_date_from_filename(filename):
    """
    Parses the measurement date from an uploaded Excel filename.

    Supported formats (preferred, per user spec):
      - DD-MM-YYYY (CE)        e.g. '04-08-2026.xlsx' -> ('2026-08-04', week_no)
      - DD-MM-YY               e.g. '04-08-69.xlsx'
          * YY > 43  -> interpreted as Buddhist Era short year (69 -> 2569 -> 2026)
          * YY <= 43 -> interpreted as CE short year (26 -> 2026)

    Returns (date_str 'YYYY-MM-DD', week_no). Falls back to today's date
    and week 1 if no date pattern can be parsed.

    Week number is computed by rounding (days / 7) to the nearest integer,
    so measurement dates that fall slightly short of a full 7-day interval
    (e.g. 13 days after START_DATE) still map to the correct week (3, not 2).
    """
    if filename is None:
        today = datetime.date.today()
        week_no = max(1, round((today - data_schema.START_DATE).days / 7) + 1)
        return today.strftime("%Y-%m-%d"), week_no

    name = os.path.basename(str(filename))
    # Strip extension
    name_no_ext = re.sub(r"\.(xlsx|xls|csv)$", "", name, flags=re.IGNORECASE)

    # Try DD-MM-YYYY (CE) first
    m = re.search(r"(\d{1,2})-(\d{1,2})-(\d{4})", name_no_ext)
    if m:
        try:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            parsed = datetime.date(y, mo, d)
            week_no = max(1, round((parsed - data_schema.START_DATE).days / 7) + 1)
            return parsed.strftime("%Y-%m-%d"), week_no
        except ValueError:
            pass

    # Try DD-MM-YY
    m = re.search(r"(\d{1,2})-(\d{1,2})-(\d{2})\b", name_no_ext)
    if m:
        try:
            d, mo, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
            # Heuristic: YY > 43 -> Buddhist Era short year (25xx -> CE = yy + 1957),
            # else CE short year (20xx -> 2000 + yy). Both 69 (BE 2569) and 26 (CE 2026)
            # resolve to 2026 in the project context.
            year = (yy + 1957) if yy > 43 else (2000 + yy)
            parsed = datetime.date(year, mo, d)
            week_no = max(1, round((parsed - data_schema.START_DATE).days / 7) + 1)
            return parsed.strftime("%Y-%m-%d"), week_no
        except ValueError:
            pass

    # Fallback: today
    today = datetime.date.today()
    week_no = max(1, round((today - data_schema.START_DATE).days / 7) + 1)
    return today.strftime("%Y-%m-%d"), week_no

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
EXP_STORAGE_PATH = os.path.join(DATA_DIR, "saved_experiment_data.csv")
ENV_STORAGE_PATH = os.path.join(DATA_DIR, "saved_env_data.csv")
PPFD_LOGGER_PATH = os.path.join(DATA_DIR, "accumulated_ppfd_logger.csv")
TEMP_LOGGER_PATH = os.path.join(DATA_DIR, "accumulated_temp_logger.csv")


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
    """Generates an empty environment dataframe with all required columns and 0 rows."""
    env_columns = [
        "week_no", "temp_c", "ppfd_control_gm", "ppfd_led_gm", "ppfd_control_f",
        "ppfd_led_f1", "ppfd_led_f2", "soil_ph", "soil_ec", "soil_om",
        "soil_total_n", "soil_avail_p", "soil_avail_k", "soil_texture"
    ]
    return pd.DataFrame(columns=env_columns)


def generate_env_template():
    """Generates a 4-week template for greenhouse and soil logger data entry."""
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
            "soil_texture": None
        })
    return pd.DataFrame(env_rows)


def _recalculate_week_no_from_record_date(df):
    """Recalculates week_no from record_date using the current rounding formula.

    Older data may carry week_no values computed with floor division (days // 7 + 1),
    which mapped measurement dates slightly short of a full 7-day interval to the
    wrong week (e.g. 13 days -> week 2 instead of 3). This migrates them on load.
    """
    if df is None or df.empty or "record_date" not in df.columns:
        return df
    df = df.copy()
    start = data_schema.START_DATE
    for idx, row in df.iterrows():
        rd = row.get("record_date")
        if pd.isna(rd):
            continue
        try:
            parsed = pd.to_datetime(rd).date()
            df.at[idx, "week_no"] = max(1, round((parsed - start).days / 7) + 1)
        except Exception:
            continue
    return df


def load_experiment_data_from_disk():
    """Loads persistent experiment dataset from local CSV storage if available."""
    if os.path.exists(EXP_STORAGE_PATH):
        try:
            df = pd.read_csv(EXP_STORAGE_PATH)
            df = ensure_all_columns_exist(df)
            df = _recalculate_week_no_from_record_date(df)
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
    """Clears local persistent storage files including accumulated logger data."""
    for p in [EXP_STORAGE_PATH, ENV_STORAGE_PATH, PPFD_LOGGER_PATH, TEMP_LOGGER_PATH]:
        if os.path.exists(p):
            try:
                os.remove(p)
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


def parse_uploaded_excel(file_bytes, filename=None):
    """
    Parses uploaded multi-sheet Excel files into the research schema.

    The `filename` is used to derive the measurement date and week number
    (see _extract_date_from_filename). Sheet names are normalized so that
    both underscore ('Control_GM') and hyphen ('Control-GM') variants match
    the canonical treatment names in data_schema.TREATMENTS.
    """
    try:
        excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
        sheet_names = excel_file.sheet_names

        # Derive measurement date / week from filename (fallback: today / week 1)
        record_date_str, week_no = _extract_date_from_filename(filename)

        col_rename = {
            'หมายเลขต้น': 'plant_id',
            'ความกว้างทรงพุ่ม (ซม.)': 'canopy_width',
            'ความยาวทรงพุ่ม (ซม.)': 'canopy_length',
            'ความสูงทรงพุ่ม (ซม.)': 'canopy_height',
            'จำนวนใบ': 'leaf_count',
            'มุมสี': 'hue_angle',
            'มุมสี (Hue Angle)': 'hue_angle',
            'Hue Angle': 'hue_angle'
        }

        parsed_rows = []
        matched_sheets = []
        for sheet in sheet_names:
            canonical = _normalize_sheet_name(sheet)
            if canonical is None:
                continue
            sheet_df = pd.read_excel(excel_file, sheet_name=sheet)
            sheet_df = sheet_df.rename(columns=col_rename)
            sheet_df["treatment"] = canonical
            sheet_df["variety"] = data_schema.VARIETY_MAP.get(canonical, "Green Moon")
            sheet_df["lighting"] = data_schema.LIGHTING_MAP.get(canonical, "Control")
            # Always stamp with the date derived from the filename so multiple
            # uploads on different days do not collide and overwrite each other.
            sheet_df["record_date"] = record_date_str
            sheet_df["week_no"] = week_no
            parsed_rows.append(sheet_df)
            matched_sheets.append(canonical)

        if parsed_rows:
            combined_df = pd.concat(parsed_rows, ignore_index=True)
            combined_df = ensure_all_columns_exist(combined_df)
            combined_df = phytochemical.apply_phytochemical_calculations(combined_df)
            return combined_df, (
                f"Successfully loaded multi-sheet Excel dataset "
                f"({len(matched_sheets)} plots, date={record_date_str}, week={week_no})!"
            )
        else:
            # Fallback: no sheet matched a treatment name; load the first sheet
            df = pd.read_excel(excel_file, sheet_name=0)
            df = df.rename(columns=col_rename)
            df["record_date"] = record_date_str
            df["week_no"] = week_no
            # NOTE: treatment/variety/lighting are NOT set here because no sheet
            # name matched a canonical treatment. Rows will not appear in any
            # treatment-filtered view (Weekly Data Entry, Harvest, Phytochem tabs).
            df = ensure_all_columns_exist(df)
            df = phytochemical.apply_phytochemical_calculations(df)
            expected = ", ".join(data_schema.TREATMENTS)
            return df, (
                f"⚠️ No treatment sheets matched (expected one of: {expected}). "
                f"Loaded the first worksheet WITHOUT treatment tags — rows will NOT "
                f"appear in treatment-filtered views. Please rename sheets to match "
                f"the canonical treatment names and re-upload. "
                f"(date={record_date_str}, week={week_no})"
            )
    except Exception as e:
        return pd.DataFrame(), f"Error parsing Excel file: {str(e)}"


def merge_accumulative_experiment_data(existing_df, new_df):
    """
    Merges newly uploaded experiment data into the existing accumulative
    dataframe. Deduplicates on (record_date, treatment, plant_id).

    For rows that share the same dedup key, NaN cells in the newly uploaded
    row do NOT overwrite non-NaN values already stored in the existing row
    (combine_first semantics). This prevents re-uploads of partial Excel
    files from silently erasing values that were entered manually in the
    data editor. Non-NaN values in the new row still win over the old row
    so legitimate corrections propagate.

    Mirrors the accumulative pattern used for logger data in
    modules.logger_processing.merge_accumulative_logger_data.
    """
    if existing_df is None or existing_df.empty:
        merged = new_df.copy() if new_df is not None and not new_df.empty else generate_empty_dataset()
    elif new_df is None or new_df.empty:
        merged = existing_df.copy()
    else:
        dedup_keys = ["record_date", "treatment", "plant_id"]
        sort_cols = [c for c in dedup_keys if c in new_df.columns and c in existing_df.columns]

        if all(k in new_df.columns for k in dedup_keys) and all(k in existing_df.columns for k in dedup_keys):
            # Combine_first on dedup keys: keep new non-NaN values, fall back to old for NaN cells.
            # Build a unified column set so combine_first handles every column.
            all_cols = list(dict.fromkeys(list(existing_df.columns) + list(new_df.columns)))
            existing_aligned = existing_df.reindex(columns=all_cols)
            new_aligned = new_df.reindex(columns=all_cols)

            existing_idxed = existing_aligned.set_index(dedup_keys)
            new_idxed = new_aligned.set_index(dedup_keys)

            # combine_first: values from new_idxed take priority; NaN in new falls back to existing.
            # We need new (latest) to win, so new_idxed.combine_first(existing_idxed).
            combined = new_idxed.combine_first(existing_idxed)

            # Rows that exist only in existing or only in new are preserved by combine_first.
            merged = combined.reset_index()
        else:
            # Fall back to whole-row dedup if dedup keys are missing.
            merged = pd.concat([existing_df, new_df], ignore_index=True)
            merged = merged.drop_duplicates(keep="last")

        if sort_cols:
            merged = merged.sort_values(sort_cols).reset_index(drop=True)

    merged = ensure_all_columns_exist(merged)
    merged = phytochemical.apply_phytochemical_calculations(merged)
    return merged


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
