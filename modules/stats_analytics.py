"""
Statistical Analytics Engine for Lettuce Research Project.
Provides Two-Way ANOVA (Variety x Lighting), Tukey HSD post-hoc testing,
Pearson correlation analysis, and descriptive summary statistics.
"""

import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from typing import Dict, Any, Tuple, Optional

def calculate_descriptive_stats(df: pd.DataFrame, metric: str, group_by: str = "treatment") -> pd.DataFrame:
    """Calculate Mean, SD, Min, Max, and Count for a target metric grouped by treatment or variety."""
    if df.empty or metric not in df.columns:
        return pd.DataFrame()
    
    clean_df = df.dropna(subset=[metric, group_by])
    if clean_df.empty:
        return pd.DataFrame()
        
    summary = clean_df.groupby(group_by)[metric].agg(
        Mean="mean",
        SD="std",
        Min="min",
        Max="max",
        Count="count"
    ).reset_index()
    
    summary["Mean_±_SD"] = summary.apply(
        lambda r: f"{r['Mean']:.2f} ± {r['SD']:.2f}" if not pd.isna(r['SD']) else f"{r['Mean']:.2f}",
        axis=1
    )
    return summary

def run_two_way_anova(df: pd.DataFrame, target_metric: str) -> Dict[str, Any]:
    """
    Execute Two-Way ANOVA on target metric with Factors: Variety (Green Moon vs Fame) and Lighting (Control vs LED).
    Returns ANOVA summary table and significance status.
    """
    if df.empty or target_metric not in df.columns:
        return {"error": f"Metric '{target_metric}' not available in dataset."}
        
    sub_df = df.dropna(subset=[target_metric, "variety", "lighting"]).copy()
    if len(sub_df) < 6:
        return {"error": "Insufficient observations for Two-Way ANOVA (need at least 6 valid data points)."}
        
    # Standardize column names for statsmodels formula
    sub_df["response"] = sub_df[target_metric].astype(float)
    
    try:
        model = ols('response ~ C(variety) + C(lighting) + C(variety):C(lighting)', data=sub_df).fit()
        anova_table = sm.stats.anova_lm(model, typ=2)
        
        # Formatting table output
        anova_table["PR(>F)_formatted"] = anova_table["PR(>F)"].apply(
            lambda p: f"{p:.4f} *" if p < 0.05 else (f"{p:.4f} (ns)" if not pd.isna(p) else "N/A")
        )
        
        return {
            "success": True,
            "anova_table": anova_table,
            "model_summary": model.summary().as_text(),
            "p_variety": anova_table.loc["C(variety)", "PR(>F)"] if "C(variety)" in anova_table.index else np.nan,
            "p_lighting": anova_table.loc["C(lighting)", "PR(>F)"] if "C(lighting)" in anova_table.index else np.nan,
            "p_interaction": anova_table.loc["C(variety):C(lighting)", "PR(>F)"] if "C(variety):C(lighting)" in anova_table.index else np.nan
        }
    except Exception as e:
        return {"error": f"Failed to calculate Two-Way ANOVA: {str(e)}"}

def run_tukey_hsd(df: pd.DataFrame, target_metric: str, group_col: str = "treatment") -> Optional[pd.DataFrame]:
    """Execute Tukey HSD Post-Hoc Test across treatments for a specific metric."""
    if df.empty or target_metric not in df.columns or group_col not in df.columns:
        return None
        
    sub_df = df.dropna(subset=[target_metric, group_col])
    if len(sub_df) < 5 or sub_df[group_col].nunique() < 2:
        return None
        
    try:
        tukey = pairwise_tukeyhsd(endog=sub_df[target_metric], groups=sub_df[group_col], alpha=0.05)
        tukey_df = pd.DataFrame(data=tukey._results_table.data[1:], columns=tukey._results_table.data[0])
        return tukey_df
    except Exception:
        return None

def compute_pearson_correlation(df: pd.DataFrame, numeric_cols: list) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Compute Pearson Correlation coefficients (r) and p-values for selected numeric columns."""
    valid_cols = [c for c in numeric_cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if len(valid_cols) < 2:
        return pd.DataFrame(), pd.DataFrame()
        
    sub_df = df[valid_cols].dropna()
    if len(sub_df) < 3:
        return pd.DataFrame(), pd.DataFrame()
        
    corr_matrix = pd.DataFrame(index=valid_cols, columns=valid_cols, dtype=float)
    p_matrix = pd.DataFrame(index=valid_cols, columns=valid_cols, dtype=float)
    
    for c1 in valid_cols:
        for c2 in valid_cols:
            if c1 == c2:
                corr_matrix.loc[c1, c2] = 1.0
                p_matrix.loc[c1, c2] = 0.0
            else:
                r, p = stats.pearsonr(sub_df[c1], sub_df[c2])
                corr_matrix.loc[c1, c2] = round(r, 3)
                p_matrix.loc[c1, c2] = round(p, 4)
                
    return corr_matrix, p_matrix
