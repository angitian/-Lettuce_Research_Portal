"""
Phytochemical Calculations Module.
Provides Gratani equations & Folin-Ciocalteu spectrophotometric quantification
for pigments and phenolics in Head Lettuce leaves with sample weight normalization.
"""

import numpy as np
import pandas as pd
from typing import Dict

def calculate_chlorophyll_a(
    od663: float, 
    od645: float, 
    extract_vol_ml: float = 25.0, 
    sample_weight_g: float = 0.5
) -> float:
    """Calculate Chlorophyll a (mg/g FW) normalized by sample weight."""
    if pd.isna(od663) or pd.isna(od645):
        return np.nan
    weight = sample_weight_g if not pd.isna(sample_weight_g) and sample_weight_g > 0 else 0.5
    raw_mg_l = 12.7 * od663 - 2.69 * od645
    val = (raw_mg_l * extract_vol_ml) / (weight * 1000.0)
    return max(0.0, float(val))

def calculate_chlorophyll_b(
    od663: float, 
    od645: float, 
    extract_vol_ml: float = 25.0, 
    sample_weight_g: float = 0.5
) -> float:
    """Calculate Chlorophyll b (mg/g FW) normalized by sample weight."""
    if pd.isna(od663) or pd.isna(od645):
        return np.nan
    weight = sample_weight_g if not pd.isna(sample_weight_g) and sample_weight_g > 0 else 0.5
    raw_mg_l = 22.9 * od645 - 4.86 * od663
    val = (raw_mg_l * extract_vol_ml) / (weight * 1000.0)
    return max(0.0, float(val))

def calculate_total_chlorophyll(
    od663: float, 
    od645: float, 
    extract_vol_ml: float = 25.0, 
    sample_weight_g: float = 0.5
) -> float:
    """Calculate Total Chlorophyll (mg/g FW) normalized by sample weight."""
    if pd.isna(od663) or pd.isna(od645):
        return np.nan
    weight = sample_weight_g if not pd.isna(sample_weight_g) and sample_weight_g > 0 else 0.5
    raw_mg_l = 8.02 * od663 + 20.20 * od645
    val = (raw_mg_l * extract_vol_ml) / (weight * 1000.0)
    return max(0.0, float(val))

def calculate_carotenoids(
    od470: float, 
    total_chl_mg_g: float, 
    extract_vol_ml: float = 25.0, 
    sample_weight_g: float = 0.5
) -> float:
    """Calculate Total Carotenoids (mg/g FW) normalized by sample weight."""
    if pd.isna(od470) or pd.isna(total_chl_mg_g):
        return np.nan
    weight = sample_weight_g if not pd.isna(sample_weight_g) and sample_weight_g > 0 else 0.5
    
    # Gratani equation formula
    raw_val = (4.7 * od470 - 0.27 * (total_chl_mg_g * weight * 1000.0 / extract_vol_ml)) * extract_vol_ml / (weight * 1000.0)
    return max(0.0, float(raw_val))

def calculate_total_phenolics(
    od765: float, 
    std_slope: float = 0.01, 
    std_intercept: float = 0.0, 
    sample_weight_g: float = 0.5,
    dilution_factor: float = 1.0
) -> float:
    """
    Calculate Total Phenolics Content (mg GAE/g FW) using Folin-Ciocalteu assay
    against a Gallic Acid standard curve (y = slope * x + intercept).
    """
    if pd.isna(od765) or std_slope == 0:
        return np.nan
    weight = sample_weight_g if not pd.isna(sample_weight_g) and sample_weight_g > 0 else 0.5
    gae_conc = (od765 - std_intercept) / std_slope * dilution_factor
    final_val = gae_conc / weight
    return max(0.0, float(final_val))

def compute_phytochemical_row(
    od663: float, 
    od645: float, 
    od470: float, 
    od765: float,
    sample_weight_g: float = 0.5,
    std_slope: float = 0.01,
    std_intercept: float = 0.0
) -> Dict[str, float]:
    """Compute all phytochemical metrics for a single plant record."""
    w = sample_weight_g if not pd.isna(sample_weight_g) and sample_weight_g > 0 else 0.5
    chl_a = calculate_chlorophyll_a(od663, od645, sample_weight_g=w)
    chl_b = calculate_chlorophyll_b(od663, od645, sample_weight_g=w)
    total_chl = calculate_total_chlorophyll(od663, od645, sample_weight_g=w)
    carot = calculate_carotenoids(od470, total_chl, sample_weight_g=w)
    phenolics = calculate_total_phenolics(od765, std_slope=std_slope, std_intercept=std_intercept, sample_weight_g=w)
    
    return {
        "chl_a": round(chl_a, 4) if not pd.isna(chl_a) else np.nan,
        "chl_b": round(chl_b, 4) if not pd.isna(chl_b) else np.nan,
        "total_chl": round(total_chl, 4) if not pd.isna(total_chl) else np.nan,
        "carotenoids": round(carot, 4) if not pd.isna(carot) else np.nan,
        "total_phenolics": round(phenolics, 4) if not pd.isna(phenolics) else np.nan
    }

def apply_phytochemical_calculations(df: pd.DataFrame) -> pd.DataFrame:
    """Apply auto-calculations across an entire DataFrame containing OD & weight columns."""
    df_out = df.copy()
    
    required_cols = ["OD663", "OD645", "OD470", "OD765", "sample_weight_g"]
    for col in required_cols:
        if col not in df_out.columns:
            df_out[col] = 0.5 if col == "sample_weight_g" else np.nan
            
    res = df_out.apply(
        lambda r: compute_phytochemical_row(
            r["OD663"], r["OD645"], r["OD470"], r["OD765"], r["sample_weight_g"]
        ),
        axis=1
    )
    res_df = pd.DataFrame(res.tolist(), index=df_out.index)
    
    for c in res_df.columns:
        df_out[c] = res_df[c]
        
    return df_out
