"""
Export Operations Manager for Lettuce Research Project.
Generates multi-sheet Excel workbooks (.xlsx) using openpyxl and CSV exports.
Includes raw data, weekly descriptive summaries, and phytochemical analysis.
"""

import io
import pandas as pd
from typing import Tuple
from modules.data_schema import ENG_TO_THAI_COLUMNS, WEEKLY_METRICS, HARVEST_METRICS, PHYTOCHEMICAL_METRICS

def generate_csv_export(df: pd.DataFrame) -> str:
    """Convert DataFrame to UTF-8 encoded CSV string with BOM for Excel compatibility."""
    return df.to_csv(index=False, encoding="utf-8-sig")

def generate_multisheet_excel(df: pd.DataFrame, env_df: pd.DataFrame) -> bytes:
    """
    Build structured multi-sheet Excel workbook (.xlsx):
    - Sheet 1: Raw Data
    - Sheet 2: Weekly Summary (Mean +/- SD)
    - Sheet 3: Phytochemical & Harvest Analysis
    - Sheet 4: Environmental Loggers
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: Raw Data (with Thai column header aliases for convenience)
        raw_df = df.copy()
        raw_df_thai = raw_df.rename(columns=ENG_TO_THAI_COLUMNS)
        raw_df_thai.to_excel(writer, sheet_name="Raw Data", index=False)
        
        # Sheet 2: Weekly Summary
        summary_rows = []
        if not df.empty and "week_no" in df.columns:
            weekly_cols = [c for c in WEEKLY_METRICS.keys() if c in df.columns]
            grouped = df.groupby(["week_no", "treatment"])
            
            for (w, trt), group in grouped:
                row = {"Week": w, "Treatment": trt, "Sample Count": len(group)}
                for col in weekly_cols:
                    label = WEEKLY_METRICS[col]
                    mean_val = group[col].mean()
                    std_val = group[col].std()
                    row[f"{label} (Mean)"] = round(mean_val, 2) if not pd.isna(mean_val) else ""
                    row[f"{label} (SD)"] = round(std_val, 2) if not pd.isna(std_val) else ""
                summary_rows.append(row)
                
        summary_df = pd.DataFrame(summary_rows)
        if summary_df.empty:
            summary_df = pd.DataFrame({"Status": ["No summary data available"]})
        summary_df.to_excel(writer, sheet_name="Weekly Summary", index=False)
        
        # Sheet 3: Phytochemical & Harvest Analysis
        phyto_cols = ["week_no", "treatment", "plant_id"] + [
            c for c in list(HARVEST_METRICS.keys()) + ["OD663", "OD645", "OD470", "OD765"] + list(PHYTOCHEMICAL_METRICS.keys())
            if c in df.columns
        ]
        phyto_df = df[phyto_cols].dropna(how="all", subset=[c for c in phyto_cols if c not in ["week_no", "treatment", "plant_id"]])
        if phyto_df.empty:
            phyto_df = df[phyto_cols].copy()
            
        phyto_df.to_excel(writer, sheet_name="Phytochemical Analysis", index=False)
        
        # Sheet 4: Environmental Loggers
        if not env_df.empty:
            env_df.to_excel(writer, sheet_name="Environmental Loggers", index=False)
            
    return output.getvalue()
