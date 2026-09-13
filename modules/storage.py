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
CONCENTRATION_STORAGE_PATH = os.path.join(DATA_DIR, "saved_concentration_data.csv")


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
        "chl_a", "chl_b", "total_chl", "carotenoids", "total_phenolics",
        # mg/L pigment concentrations (per-plant mean of replicate-level lab
        # extract values). Populated by apply_concentration_means_to_experiment.
        "chl_a_mgL", "chl_b_mgL", "total_chl_mgL", "carotenoid_mgL",
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
        "chl_a", "chl_b", "total_chl", "carotenoids", "total_phenolics",
        "chl_a_mgL", "chl_b_mgL", "total_chl_mgL", "carotenoid_mgL",
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


def _week_from_date(date_value):
    """
    Compute the canonical week_no from a measurement date using the project's
    rounding formula: max(1, round((date - START_DATE).days / 7) + 1).

    Accepts a string ('YYYY-MM-DD'), datetime.date, or pandas Timestamp.
    Returns None if the input cannot be parsed.
    """
    if date_value is None or (isinstance(date_value, float) and pd.isna(date_value)):
        return None
    try:
        parsed = pd.to_datetime(date_value).date()
    except Exception:
        return None
    return max(1, round((parsed - data_schema.START_DATE).days / 7) + 1)


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
    for p in [EXP_STORAGE_PATH, ENV_STORAGE_PATH, PPFD_LOGGER_PATH, TEMP_LOGGER_PATH, CONCENTRATION_STORAGE_PATH]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass


# -----------------------------------------------------------------------------
# Pigment Concentration (mg/L) — replicate-level lab extract data
# -----------------------------------------------------------------------------

def generate_empty_concentration_data():
    """Generates an empty concentration dataframe (replicate-level schema)."""
    return pd.DataFrame(columns=[
        "record_date", "week_no", "treatment", "variety", "lighting",
        "plant_id", "replicate", "weight_g",
        "chl_a_mgL", "chl_b_mgL", "total_chl_mgL", "carotenoid_mgL",
    ])


def load_concentration_data_from_disk():
    """Loads persistent concentration dataset (replicate-level) from CSV."""
    if os.path.exists(CONCENTRATION_STORAGE_PATH):
        try:
            df = pd.read_csv(CONCENTRATION_STORAGE_PATH)
            for col in ["record_date", "treatment", "variety", "lighting",
                        "plant_id", "replicate"]:
                if col not in df.columns:
                    df[col] = None
            for col in ["week_no", "weight_g", "chl_a_mgL", "chl_b_mgL",
                        "total_chl_mgL", "carotenoid_mgL"]:
                if col not in df.columns:
                    df[col] = np.nan
            return df
        except Exception:
            pass
    return generate_empty_concentration_data()


def save_concentration_data_to_disk(df):
    """Saves the replicate-level concentration dataset to local CSV storage."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if df is not None and not df.empty:
        df.to_csv(CONCENTRATION_STORAGE_PATH, index=False)


def _extract_treatment_from_concentration_filename(filename):
    """
    Derives the canonical treatment name from a concentration Excel filename.

    Examples:
      'concentration Control-GM.xlsx' -> 'Control_GM'
      'concentration LED-GM.xlsx'      -> 'LED_GM'
      'concentration Control-F.xlsx'  -> 'Control_F'
      'concentration LED-F (1).xlsx'   -> 'LED_F (1)'

    Returns None if no canonical treatment can be matched.
    """
    if filename is None:
        return None
    name = os.path.basename(str(filename))
    # Strip extension and the leading 'concentration ' prefix (case-insensitive)
    name_no_ext = re.sub(r"\.(xlsx|xls|csv)$", "", name, flags=re.IGNORECASE)
    name_no_ext = re.sub(r"^concentration\s+", "", name_no_ext, flags=re.IGNORECASE).strip()
    # Try direct / hyphen-underscore normalization against canonical treatments
    return _normalize_sheet_name(name_no_ext)


def read_concentration_excel(file_bytes):
    """
    Reads a pigment concentration Excel file (mg/L) and returns ALL rows from
    the replicate sheet, with original column headers preserved (no mapping,
    no filtering, no metadata stamping).

    Sheet selection:
      - The first sheet whose columns include a 'Replicate' column AND at
        least one '(mg/L)' value column.
      - Otherwise the first sheet.

    Returns (raw_df, message_str). raw_df is empty on failure.
    """
    try:
        excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
    except Exception as exc:
        return pd.DataFrame(), f"⚠️ ไม่สามารถเปิดไฟล์ Excel ได้: {exc}"

    replicate_df = None
    for sheet in excel_file.sheet_names:
        sdf = pd.read_excel(excel_file, sheet_name=sheet)
        cols_lower = {str(c).strip().lower() for c in sdf.columns}
        if "replicate" in cols_lower and any("(mg/l)" in c for c in cols_lower):
            replicate_df = sdf
            break
    if replicate_df is None:
        # Fallback: first sheet
        replicate_df = pd.read_excel(excel_file, sheet_name=excel_file.sheet_names[0])

    # Drop fully-empty trailing rows but keep all data rows
    replicate_df = replicate_df.dropna(how="all").reset_index(drop=True)
    if replicate_df.empty:
        return pd.DataFrame(), "⚠️ ไฟล์ concentration ไม่มีข้อมูลในชีต"
    return replicate_df, f"✅ อ่านไฟล์สำเร็จ — {len(replicate_df)} แถว"


def parse_concentration_rows(raw_df, treatment, date=None, week=None):
    """
    Maps raw concentration rows (as returned by ``read_concentration_excel``)
    into the replicate-level concentration schema and stamps the supplied
    metadata onto every row.

    Args:
      raw_df: DataFrame with original lab column headers (Sample_ID, Replicate,
              Chl_a (mg/L), ...). Only the rows the user selected should be
              passed here.
      treatment: canonical treatment name (e.g. 'Control_GM'). Required.
      date: measurement date (str / datetime.date / datetime). Used to compute
            week_no via ``_week_from_date``. Falls back to latest harvest date
            in experiment_data, then today.
      week: optional explicit week_no override (backward compat).

    Returns (concentration_df, message_str).
    """
    if raw_df is None or raw_df.empty:
        return generate_empty_concentration_data(), "⚠️ ไม่มีแถวที่เลือกให้นำเข้า"

    # Column aliases used by the lab file (handles trailing spaces & case).
    col_rename = {
        "Sample_ID": "plant_id",
        "Replicate": "replicate",
        "Weight_actual_g": "weight_g",
        "Chl_a (mg/L)": "chl_a_mgL",
        "Chl_a (mg/L) ": "chl_a_mgL",
        "Chl_b (mg/L)": "chl_b_mgL",
        "Chl_b (mg/L) ": "chl_b_mgL",
        "Total_Chl (mg/L)": "total_chl_mgL",
        "Total_Chl (mg/L) ": "total_chl_mgL",
        "Carotenoid (mg/L)": "carotenoid_mgL",
        "Carotenoid (mg/L) ": "carotenoid_mgL",
    }

    df = raw_df.copy()
    rename_map = {}
    for col in df.columns:
        for alias, target in col_rename.items():
            if str(col).strip().lower() == alias.strip().lower():
                rename_map[col] = target
                break
    df = df.rename(columns=rename_map)

    required = ["plant_id", "replicate"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return generate_empty_concentration_data(), (
            f"⚠️ ไฟล์ concentration ขาดคอลัมน์ที่จำเป็น: {missing}"
        )

    # Ensure mg/L columns exist (fill missing ones with NaN)
    for c in ["chl_a_mgL", "chl_b_mgL", "total_chl_mgL", "carotenoid_mgL", "weight_g"]:
        if c not in df.columns:
            df[c] = np.nan

    # Coerce numeric columns
    for c in ["weight_g", "chl_a_mgL", "chl_b_mgL", "total_chl_mgL", "carotenoid_mgL"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Drop rows that have no plant_id (blank trailing rows)
    df = df.dropna(subset=["plant_id"], how="all")
    df["plant_id"] = df["plant_id"].astype(str).str.strip()
    df["replicate"] = df["replicate"].astype(str).str.strip()

    # ----- Resolve treatment -----
    canonical = _normalize_sheet_name(str(treatment).strip())
    if canonical is None:
        return generate_empty_concentration_data(), (
            f"⚠️ treatment ไม่ตรงกับ treatment ที่รองรับ: {treatment}"
        )
    df["treatment"] = canonical
    df["variety"] = data_schema.VARIETY_MAP.get(canonical, "Green Moon")
    df["lighting"] = data_schema.LIGHTING_MAP.get(canonical, "Control")

    # ----- Resolve record_date -----
    if date is not None:
        try:
            resolved_date = pd.to_datetime(date).date()
        except Exception:
            resolved_date = None
    else:
        resolved_date = None
    if resolved_date is None:
        # Fallback: latest harvest date in experiment_data
        exp_df = st.session_state.get("experiment_data")
        if exp_df is not None and not exp_df.empty and "record_date" in exp_df.columns:
            latest_dates = exp_df["record_date"].dropna()
            if not latest_dates.empty:
                try:
                    parsed_dates = pd.to_datetime(latest_dates, errors="coerce").dropna()
                    if not parsed_dates.empty:
                        resolved_date = parsed_dates.max().date()
                except Exception:
                    resolved_date = None
        if resolved_date is None:
            resolved_date = datetime.date.today()

    record_date_str = resolved_date.isoformat()

    # ----- Resolve week_no -----
    if week is not None:
        week_no = int(week)
    else:
        week_no = _week_from_date(resolved_date)
        if week_no is None:
            week_no = 1

    df["record_date"] = record_date_str
    df["week_no"] = week_no

    # Keep only schema columns
    out_cols = [
        "record_date", "week_no", "treatment", "variety", "lighting",
        "plant_id", "replicate", "weight_g",
        "chl_a_mgL", "chl_b_mgL", "total_chl_mgL", "carotenoid_mgL",
    ]
    for c in out_cols:
        if c not in df.columns:
            df[c] = np.nan
    df = df[out_cols].reset_index(drop=True)

    return df, (
        f"✅ นำเข้าข้อมูล concentration สำเร็จ — {len(df)} แถว replicate "
        f"(treatment={canonical}, date={record_date_str}, week={week_no})"
    )


def parse_concentration_excel(file_bytes, filename=None, target_treatment=None, target_date=None, target_week=None):
    """
    Backward-compatible wrapper: reads the Excel file then maps all rows with
    the supplied metadata. New UI should call ``read_concentration_excel`` +
    ``parse_concentration_rows`` directly to support row selection.

    Treatment resolution: ``target_treatment`` > filename > error.
    Date resolution: ``target_date`` > latest in experiment_data > today.
    """
    raw_df, read_msg = read_concentration_excel(file_bytes)
    if raw_df.empty:
        return generate_empty_concentration_data(), read_msg

    # Resolve treatment (target > filename)
    treatment = target_treatment
    if treatment is None:
        treatment = _extract_treatment_from_concentration_filename(filename)
    if treatment is None:
        return generate_empty_concentration_data(), (
            "⚠️ ไม่สามารถระบุ treatment ได้ — "
            "เพิ่มคอลัมน์ Treatment ในไฟล์, เลือกแปลงในฟอร์มอัปโหลด, "
            "หรือตั้งชื่อไฟล์ตามรูปแบบ 'concentration <Treatment>.xlsx' "
            "เช่น 'concentration Control-GM.xlsx'"
        )
    return parse_concentration_rows(raw_df, treatment, date=target_date, week=target_week)


def merge_concentration_data(existing_df, new_df):
    """
    Upserts replicate-level concentration data using the composite key
    [treatment, plant_id, replicate, week_no].

    - Rows whose key matches an existing row OVERWRITE the existing values
      (supports re-uploading a corrected file for the same week/treatment).
    - Rows with a new key are appended (supports uploading additional
      treatments or weeks incrementally).
    """
    if existing_df is None or existing_df.empty:
        return new_df.copy() if new_df is not None and not new_df.empty else generate_empty_concentration_data()
    if new_df is None or new_df.empty:
        return existing_df.copy()

    dedup_keys = ["treatment", "plant_id", "replicate", "week_no"]
    all_cols = list(dict.fromkeys(list(existing_df.columns) + list(new_df.columns)))
    existing_aligned = existing_df.reindex(columns=all_cols)
    new_aligned = new_df.reindex(columns=all_cols)

    existing_idxed = existing_aligned.set_index(dedup_keys)
    new_idxed = new_aligned.set_index(dedup_keys)

    # new (latest) wins on key collision -> new.combine_first(existing)
    combined = new_idxed.combine_first(existing_idxed)
    merged = combined.reset_index()
    sort_cols = [c for c in dedup_keys if c in merged.columns]
    if sort_cols:
        merged = merged.sort_values(sort_cols).reset_index(drop=True)
    return merged


def apply_concentration_means_to_experiment(exp_df, conc_df):
    """
    Aggregates replicate-level concentration data to per-plant means and
    writes the four mg/L columns into experiment_data (overwrite on match).

    Grouping key: [treatment, plant_id, week_no]. Rows in experiment_data
    that have no matching concentration records keep their existing mg/L
    values (which may be NaN).
    """
    if exp_df is None or exp_df.empty:
        return exp_df
    if conc_df is None or conc_df.empty:
        return exp_df

    mgL_cols = ["chl_a_mgL", "chl_b_mgL", "total_chl_mgL", "carotenoid_mgL"]
    # Ensure columns exist in exp_df
    df = exp_df.copy()
    for c in mgL_cols:
        if c not in df.columns:
            df[c] = np.nan

    # Compute per-plant means from replicates
    valid_conc = conc_df.dropna(subset=["treatment", "plant_id"], how="any")
    if valid_conc.empty:
        return df
    means = (
        valid_conc
        .groupby(["treatment", "plant_id", "week_no"], as_index=False)[mgL_cols]
        .mean()
    )

    # Write means back into experiment_data rows matching (treatment, plant_id, week_no)
    df_keys = df.set_index(["treatment", "plant_id", "week_no"])
    means_keys = means.set_index(["treatment", "plant_id", "week_no"])
    # Only update rows that exist in both
    common = df_keys.index.intersection(means_keys.index)
    if len(common) == 0:
        return df
    for c in mgL_cols:
        df_keys.loc[common, c] = means_keys.loc[common, c]
    df = df_keys.reset_index()
    return df


def delete_treatment_week_data(exp_df, conc_df, treatment, week_no):
    """
    Deletes all rows for a given (treatment, week_no) from both experiment_data
    and concentration_data. Handles float/int week mismatch via pd.to_numeric.

    Args:
      exp_df: experiment_data DataFrame (week_no may be float).
      conc_df: concentration_data DataFrame (week_no may be int).
      treatment: canonical treatment name (e.g. 'Control_GM').
      week_no: week number to delete (int or float).

    Returns (exp_out, conc_out) with reset indices.
    """
    target_week = pd.to_numeric(week_no, errors="coerce")

    exp_out = exp_df.copy() if exp_df is not None else pd.DataFrame()
    if not exp_out.empty and "treatment" in exp_out.columns and "week_no" in exp_out.columns:
        exp_weeks = pd.to_numeric(exp_out["week_no"], errors="coerce")
        mask = (exp_out["treatment"] == treatment) & (exp_weeks == target_week)
        exp_out = exp_out[~mask].reset_index(drop=True)

    conc_out = conc_df.copy() if conc_df is not None else pd.DataFrame()
    if not conc_out.empty and "treatment" in conc_out.columns and "week_no" in conc_out.columns:
        conc_weeks = pd.to_numeric(conc_out["week_no"], errors="coerce")
        mask = (conc_out["treatment"] == treatment) & (conc_weeks == target_week)
        conc_out = conc_out[~mask].reset_index(drop=True)

    return exp_out, conc_out


def clear_tab3_section_data(exp_df, conc_df, treatment, section):
    """
    Clears data for a specific section of tab3 (Harvest & Lab Results) for a
    given treatment. Only the columns belonging to that section are set to NaN
    in experiment_data (rows are preserved so other tabs' columns — e.g.
    canopy/leaf count from Weekly Data Entry — are untouched). For the pigment
    section, replicate rows are removed from concentration_data and the mg/L
    mean columns in experiment_data are cleared.

    Args:
      exp_df: experiment_data DataFrame.
      conc_df: concentration_data DataFrame.
      treatment: canonical treatment name (e.g. 'Control_GM').
      section: one of 'harvest', 'uvvis', 'pigment'.

    Returns (exp_out, conc_out) with reset indices.
    """
    exp_out = exp_df.copy() if exp_df is not None else pd.DataFrame()
    conc_out = conc_df.copy() if conc_df is not None else pd.DataFrame()

    harvest_cols = ["fresh_weight", "root_length", "core_length", "head_diameter", "head_firmness"]
    uvvis_cols = ["sample_weight_g", "OD663", "OD645", "OD470", "OD765",
                  "chl_a", "chl_b", "total_chl", "carotenoids", "total_phenolics"]
    mgL_cols = ["chl_a_mgL", "chl_b_mgL", "total_chl_mgL", "carotenoid_mgL"]

    if not exp_out.empty and "treatment" in exp_out.columns:
        mask = exp_out["treatment"] == treatment
        if section == "harvest":
            cols = [c for c in harvest_cols if c in exp_out.columns]
        elif section == "uvvis":
            cols = [c for c in uvvis_cols if c in exp_out.columns]
        elif section == "pigment":
            cols = [c for c in mgL_cols if c in exp_out.columns]
        else:
            cols = []
        for c in cols:
            exp_out.loc[mask, c] = np.nan

    if section == "pigment":
        if not conc_out.empty and "treatment" in conc_out.columns:
            conc_out = conc_out[conc_out["treatment"] != treatment].reset_index(drop=True)

    return exp_out, conc_out


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

    # Pigment concentration (mg/L) replicate-level data
    if "concentration_data" not in st.session_state:
        st.session_state.concentration_data = load_concentration_data_from_disk()
    # Always re-apply per-plant means into experiment_data so analytics
    # reflects the latest replicate values.
    st.session_state.experiment_data = apply_concentration_means_to_experiment(
        st.session_state.experiment_data, st.session_state.concentration_data
    )


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
