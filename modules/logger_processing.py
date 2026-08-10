"""
High-Frequency Environmental & PPFD Logger Processing Module.
Optimized for Hourly Downsampling (Pre-aggregated hourly storage),
accumulative merging across multiple uploads, custom plot naming,
and Daily Light Integral (DLI) calculations with dd/mm/yyyy date formatting.
"""

import os
import io
import re
import datetime
import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PPFD_STORAGE_PATH = os.path.join(DATA_DIR, "accumulated_ppfd_logger.csv")
TEMP_STORAGE_PATH = os.path.join(DATA_DIR, "accumulated_temp_logger.csv")


def parse_thai_ppfd_date(s):
    """Parses Thai PPFD date strings like '07/10/26 04 นาฬิกา 1 นาที' or standard dates."""
    if not isinstance(s, str):
        return pd.NaT
    clean = re.sub(r'\s*นาฬิกา\s*', ':', s)
    clean = re.sub(r'\s*นาที\s*', '', clean).strip()
    try:
        dt = pd.to_datetime(clean, format='%m/%d/%y %H:%M', errors='coerce')
        if pd.isna(dt):
            dt = pd.to_datetime(clean, errors='coerce')
        return dt
    except Exception:
        return pd.NaT


def parse_be_temp_date(s):
    """Parses Thai Buddhist Era dates like '22/6/2569 11:43:56' or standard dates."""
    if not isinstance(s, str):
        return pd.NaT
    s = s.strip()
    match = re.match(r'(\d+)/(\d+)/(\d+)\s+(\d+:\d+:\d+|\d+:\d+)', s)
    if match:
        d, m, y, t = int(match.group(1)), int(match.group(2)), int(match.group(3)), match.group(4)
        if y > 2500:
            y -= 543
        elif y < 100:
            y += 2000
        return pd.to_datetime(f'{y:04d}-{m:02d}-{d:02d} {t}', errors='coerce')
    return pd.to_datetime(s, errors='coerce')


def parse_ppfd_csv(file_input, downsample_hourly=True):
    """
    Parses HOBO PPFD CSV file content or path into a structured pandas DataFrame.
    Automatically downsamples high-frequency data to Hourly Averages if downsample_hourly=True.
    """
    if isinstance(file_input, (str, os.PathLike)):
        with open(file_input, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    elif isinstance(file_input, bytes):
        content = file_input.decode('utf-8', errors='ignore')
    elif hasattr(file_input, 'getvalue'):
        content = file_input.getvalue().decode('utf-8', errors='ignore')
    else:
        content = str(file_input)

    lines = content.splitlines()
    header_idx = 0
    for i, line in enumerate(lines[:20]):
        if 'Date Time' in line or 'PAR' in line or 'µmol' in line:
            header_idx = i
            break

    df = pd.read_csv(io.StringIO(content), skiprows=header_idx)
    
    date_cols = [c for c in df.columns if 'date' in str(c).lower() or 'time' in str(c).lower()]
    if not date_cols:
        return pd.DataFrame(), []
    
    date_col = date_cols[0]
    par_cols = [c for c in df.columns if 'par' in str(c).lower() or 'µmol' in str(c).lower() or 'umol' in str(c).lower()]
    
    df['datetime'] = df[date_col].astype(str).apply(parse_thai_ppfd_date)
    df = df.dropna(subset=['datetime'])
    
    for pc in par_cols:
        df[pc] = pd.to_numeric(df[pc], errors='coerce').clip(lower=0.0)
        
    df = df.sort_values('datetime').drop_duplicates(subset=['datetime']).reset_index(drop=True)
    
    if downsample_hourly and not df.empty:
        df = df.set_index('datetime')[par_cols].resample('1h').mean().reset_index()
        df = df.dropna(subset=par_cols, how='all')
        
    return df, par_cols


def parse_temp_excel_or_csv(file_input, file_name="", downsample_hourly=True):
    """
    Parses Temperature/Humidity XLS, XLSX, or CSV logger files.
    Automatically downsamples high-frequency data to Hourly Averages if downsample_hourly=True.
    """
    is_excel = file_name.endswith(('.xls', '.xlsx')) or (isinstance(file_input, (str, os.PathLike)) and str(file_input).endswith(('.xls', '.xlsx')))
    
    if is_excel:
        if isinstance(file_input, bytes):
            raw_excel = pd.read_excel(io.BytesIO(file_input))
        else:
            raw_excel = pd.read_excel(file_input)
            
        header_row = None
        for idx in range(min(25, len(raw_excel))):
            row_vals = [str(x) for x in raw_excel.iloc[idx].values]
            if any('date/time' in v.lower() or 'date' in v.lower() for v in row_vals):
                header_row = idx
                break
                
        if header_row is not None:
            if isinstance(file_input, bytes):
                df = pd.read_excel(io.BytesIO(file_input), skiprows=header_row+1)
            else:
                df = pd.read_excel(file_input, skiprows=header_row+1)
        else:
            df = raw_excel
    else:
        if isinstance(file_input, bytes):
            content = file_input.decode('utf-8', errors='ignore')
        elif hasattr(file_input, 'getvalue'):
            content = file_input.getvalue().decode('utf-8', errors='ignore')
        else:
            content = str(file_input)
        df = pd.read_csv(io.StringIO(content))

    date_cols = [c for c in df.columns if 'date' in str(c).lower() or 'time' in str(c).lower()]
    if not date_cols:
        return pd.DataFrame(), []
    
    date_col = date_cols[0]
    temp_cols = [c for c in df.columns if c != 'id' and c != date_col and not str(c).startswith('Unnamed')]
    
    df['datetime'] = df[date_col].astype(str).apply(parse_be_temp_date)
    df = df.dropna(subset=['datetime'])
    
    for tc in temp_cols:
        df[tc] = pd.to_numeric(df[tc].astype(str).str.replace('----', '').str.replace('-', ''), errors='coerce')
        
    df = df.sort_values('datetime').drop_duplicates(subset=['datetime']).reset_index(drop=True)
    
    if downsample_hourly and not df.empty:
        df = df.set_index('datetime')[temp_cols].resample('1h').mean().reset_index()
        df = df.dropna(subset=temp_cols, how='all')
        
    return df, temp_cols


def merge_accumulative_logger_data(existing_df, new_df):
    """
    Merges newly uploaded logger data into existing accumulative dataframe.
    Deduplicates based on 'datetime' and sorts chronologically.
    """
    if existing_df is None or existing_df.empty:
        return new_df
    if new_df is None or new_df.empty:
        return existing_df
        
    combined = pd.concat([existing_df, new_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=['datetime'], keep='last')
    combined = combined.sort_values('datetime').reset_index(drop=True)
    return combined


def compute_hourly_logger_aggregates(df, value_cols):
    """
    Returns hourly data (or computes hourly averages if not already downsampled).
    """
    if df is None or df.empty or 'datetime' not in df.columns:
        return pd.DataFrame()
        
    df_copy = df.copy()
    df_copy['datetime'] = pd.to_datetime(df_copy['datetime'])
    df_copy = df_copy.set_index('datetime')
    
    valid_cols = [c for c in value_cols if c in df_copy.columns]
    if not valid_cols:
        return pd.DataFrame()
        
    hourly = df_copy[valid_cols].resample('1h').mean().reset_index()
    return hourly


def compute_daily_dli(df_ppfd, channel_mapping=None):
    """
    Computes Daily Light Integral (DLI) in mol/m²/day for each PPFD channel.
    Formats Date column as dd/mm/yyyy.
    Formula: DLI = Sum over 24 hours of (Hourly_Mean_PPFD * 3600) / 1,000,000
    """
    if df_ppfd is None or df_ppfd.empty or 'datetime' not in df_ppfd.columns:
        return pd.DataFrame()
        
    par_cols = [c for c in df_ppfd.columns if c != 'datetime']
    if not par_cols:
        return pd.DataFrame()
        
    df_copy = df_ppfd.copy()
    df_copy['datetime'] = pd.to_datetime(df_copy['datetime'])
    df_copy = df_copy.set_index('datetime')
    
    # Resample to hourly means
    hourly = df_copy[par_cols].resample('1h').mean().reset_index()
    hourly['date'] = hourly['datetime'].dt.date
    
    # Calculate DLI per day: sum(hourly_mean * 3600) / 1,000,000
    dli_records = []
    grouped = hourly.groupby('date')
    
    for date_val, group in grouped:
        d_str = pd.to_datetime(date_val).strftime('%d/%m/%Y')
        row_dict = {'Date': d_str}
        for col in par_cols:
            channel_name = channel_mapping.get(col, col) if channel_mapping else col
            hourly_means = group[col].dropna()
            if not hourly_means.empty:
                dli_val = round((hourly_means.sum() * 3600) / 1000000.0, 2)
            else:
                dli_val = np.nan
            row_dict[channel_name] = dli_val
        dli_records.append(row_dict)
        
    dli_df = pd.DataFrame(dli_records)
    return dli_df


def save_logger_storage_disk(df_ppfd, df_temp):
    """Saves accumulated PPFD and Temperature logger datasets to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if df_ppfd is not None and not df_ppfd.empty:
        df_ppfd.to_csv(PPFD_STORAGE_PATH, index=False)
    if df_temp is not None and not df_temp.empty:
        df_temp.to_csv(TEMP_STORAGE_PATH, index=False)


def load_logger_storage_disk():
    """Loads accumulated PPFD and Temperature logger datasets from disk if available."""
    df_ppfd = pd.DataFrame()
    df_temp = pd.DataFrame()
    
    if os.path.exists(PPFD_STORAGE_PATH):
        try:
            df_ppfd = pd.read_csv(PPFD_STORAGE_PATH)
            df_ppfd['datetime'] = pd.to_datetime(df_ppfd['datetime'])
        except Exception:
            pass
            
    if os.path.exists(TEMP_STORAGE_PATH):
        try:
            df_temp = pd.read_csv(TEMP_STORAGE_PATH)
            df_temp['datetime'] = pd.to_datetime(df_temp['datetime'])
        except Exception:
            pass
            
    return df_ppfd, df_temp
