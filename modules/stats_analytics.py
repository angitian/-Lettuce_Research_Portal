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

    # Collapse the multi-value `lighting` column (Control / LED / LED Plot 1 /
    # LED Plot 2) into a binary Control-vs-LED factor so the Two-Way ANOVA
    # matches the research hypothesis (Variety x Lighting: 2 x 2 design).
    sub_df["lighting_binary"] = sub_df["lighting"].astype(str).apply(
        lambda v: "LED" if v.strip().upper().startswith("LED") else "Control"
    )

    try:
        model = ols('response ~ C(variety) + C(lighting_binary) + C(variety):C(lighting_binary)', data=sub_df).fit()
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
            "p_lighting": anova_table.loc["C(lighting_binary)", "PR(>F)"] if "C(lighting_binary)" in anova_table.index else np.nan,
            "p_interaction": anova_table.loc["C(variety):C(lighting_binary)", "PR(>F)"] if "C(variety):C(lighting_binary)" in anova_table.index else np.nan
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

def run_welch_t_test(df: pd.DataFrame, metric: str, group_col: str = "comparison_group") -> Dict[str, Any]:
    """
    Welch's two-sample t-test (unequal variances) between exactly 2 groups
    defined by `group_col`. Also reports Cohen's d (pooled-SD) and 95% CI
    for the mean difference.

    Returns a dict with: success, test_name, group_labels, n1, n2,
    mean_1, mean_2, sd_1, sd_2, t_stat, df, p_value, mean_diff,
    ci_low, ci_high, cohens_d, cohens_d_interpretation, significant, warning.
    """
    if df.empty or metric not in df.columns or group_col not in df.columns:
        return {"error": f"Metric '{metric}' or group column '{group_col}' not available."}

    sub_df = df.dropna(subset=[metric, group_col])
    groups = sub_df[group_col].dropna().unique().tolist()
    if len(groups) != 2:
        return {"error": f"Welch t-test requires exactly 2 groups, got {len(groups)}."}

    g1, g2 = groups
    x1 = sub_df.loc[sub_df[group_col] == g1, metric].astype(float).dropna().values
    x2 = sub_df.loc[sub_df[group_col] == g2, metric].astype(float).dropna().values
    n1, n2 = len(x1), len(x2)
    if n1 < 2 or n2 < 2:
        return {"error": f"Each group needs at least 2 observations (got n1={n1}, n2={n2})."}

    mean_1, mean_2 = float(np.mean(x1)), float(np.mean(x2))
    sd_1, sd_2 = float(np.std(x1, ddof=1)), float(np.std(x2, ddof=1))

    t_stat, p_value = stats.ttest_ind(x1, x2, equal_var=False)
    # Welch–Satterthwaite degrees of freedom
    s1_sq, s2_sq = sd_1 ** 2, sd_2 ** 2
    df_welch = (s1_sq / n1 + s2_sq / n2) ** 2 / (
        (s1_sq / n1) ** 2 / (n1 - 1) + (s2_sq / n2) ** 2 / (n2 - 1)
    )

    # Mean difference (g1 - g2) with 95% CI using Welch SE
    mean_diff = mean_1 - mean_2
    se_diff = np.sqrt(s1_sq / n1 + s2_sq / n2)
    t_crit = stats.t.ppf(0.975, df_welch)
    ci_low = mean_diff - t_crit * se_diff
    ci_high = mean_diff + t_crit * se_diff

    # Cohen's d (pooled SD)
    pooled_sd = np.sqrt(((n1 - 1) * s1_sq + (n2 - 1) * s2_sq) / (n1 + n2 - 2))
    cohens_d = float(mean_diff / pooled_sd) if pooled_sd > 0 else float("nan")
    abs_d = abs(cohens_d)
    if abs_d < 0.2:
        d_interp = "Negligible (< 0.2)"
    elif abs_d < 0.5:
        d_interp = "Small (0.2 – 0.5)"
    elif abs_d < 0.8:
        d_interp = "Medium (0.5 – 0.8)"
    else:
        d_interp = "Large (≥ 0.8)"

    warning = None
    if n1 < 30 or n2 < 30:
        warning = "ขนาดกลุ่มเล็ก (n < 30) — ผลอาจไม่แม่นยำ ควรตรวจสอบสมมติฐานและเพิ่มข้อมูลถ้าเป็นไปได้"

    return {
        "success": True,
        "test_name": "Welch's two-sample t-test",
        "group_labels": [g1, g2],
        "n1": n1, "n2": n2,
        "mean_1": mean_1, "mean_2": mean_2,
        "sd_1": sd_1, "sd_2": sd_2,
        "t_stat": float(t_stat),
        "df": float(df_welch),
        "p_value": float(p_value),
        "mean_diff": float(mean_diff),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "cohens_d": cohens_d,
        "cohens_d_interpretation": d_interp,
        "significant": bool(p_value < 0.05),
        "warning": warning,
    }


def run_one_way_anova(df: pd.DataFrame, metric: str, factor_col: str = "comparison_group") -> Dict[str, Any]:
    """
    One-way ANOVA across 3+ groups defined by `factor_col`.
    Returns ANOVA summary table, F-stat, p-value, and significance flag.
    """
    if df.empty or metric not in df.columns or factor_col not in df.columns:
        return {"error": f"Metric '{metric}' or factor column '{factor_col}' not available."}

    sub_df = df.dropna(subset=[metric, factor_col]).copy()
    groups = sub_df[factor_col].dropna().unique().tolist()
    if len(groups) < 3:
        return {"error": f"One-way ANOVA needs at least 3 groups, got {len(groups)}."}

    sub_df["response"] = sub_df[metric].astype(float)
    # Sanitize factor values into a column safe for statsmodels formula
    sub_df["_grp"] = sub_df[factor_col].astype(str).str.replace(r"[^A-Za-z0-9_]", "_", regex=True)

    if len(sub_df) < 6:
        return {"error": "Insufficient observations for one-way ANOVA (need at least 6 valid data points)."}

    try:
        model = ols("response ~ C(_grp)", data=sub_df).fit()
        anova_table = sm.stats.anova_lm(model, typ=2)
        anova_table["PR(>F)_formatted"] = anova_table["PR(>F)"].apply(
            lambda p: f"{p:.4f} *" if p < 0.05 else (f"{p:.4f} (ns)" if not pd.isna(p) else "N/A")
        )
        f_stat = float(anova_table.loc["C(_grp)", "F"]) if "C(_grp)" in anova_table.index else float("nan")
        p_val = float(anova_table.loc["C(_grp)", "PR(>F)"]) if "C(_grp)" in anova_table.index else float("nan")

        warning = None
        group_counts = sub_df.groupby(factor_col)[metric].count().to_dict()
        if any(n < 5 for n in group_counts.values()):
            warning = "บางกลุ่มมี n < 5 — ผล ANOVA อาจไม่แม่นยำ ควรตรวจสมมติฐานเพิ่ม"

        return {
            "success": True,
            "test_name": "One-Way ANOVA",
            "anova_table": anova_table,
            "model_summary": model.summary().as_text(),
            "group_labels": groups,
            "group_counts": group_counts,
            "f_stat": f_stat,
            "p_value": p_val,
            "significant": bool(p_val < 0.05),
            "warning": warning,
        }
    except Exception as e:
        return {"error": f"Failed to calculate one-way ANOVA: {str(e)}"}


def run_auto_comparison(df: pd.DataFrame, metric: str, group_col: str = "comparison_group") -> Dict[str, Any]:
    """
    Automatically choose the appropriate statistical test based on the number
    of distinct groups in `group_col`:
      - 2 groups  -> Welch's two-sample t-test (+ Cohen's d)
      - 3+ groups -> One-way ANOVA (+ Tukey HSD post-hoc when significant)

    Returns a dict containing the chosen test name and its full result payload
    under the key `result`, plus a human-readable `decision_note`.
    """
    if df.empty or metric not in df.columns or group_col not in df.columns:
        return {"error": f"Metric '{metric}' or group column '{group_col}' not available."}

    sub_df = df.dropna(subset=[metric, group_col])
    n_groups = sub_df[group_col].nunique()
    if n_groups < 2:
        return {"error": "Need at least 2 groups to compare."}

    if n_groups == 2:
        res = run_welch_t_test(df, metric, group_col=group_col)
        return {
            "test_kind": "t_test",
            "test_name": res.get("test_name", "Welch's two-sample t-test"),
            "decision_note": (
                "เลือก Welch's t-test อัตโนมัติเพราะมี 2 กลุ่มอิสระ "
                "(ไม่สมมติความแปรปรวนเท่ากัน — ปลอดภัยกว่า Student's t-test ในทั่วไป)"
            ),
            "result": res,
        }

    res = run_one_way_anova(df, metric, factor_col=group_col)
    if "error" in res:
        return {"test_kind": "one_way_anova", "test_name": "One-Way ANOVA",
                "decision_note": "เลือก One-Way ANOVA อัตโนมัติเพราะมี 3 กลุ่มขึ้นไป",
                "result": res}
    # Attach Tukey HSD post-hoc when omnibus is significant
    tukey_df = None
    if res.get("significant"):
        tukey_df = run_tukey_hsd(df, metric, group_col=group_col)
    res["tukey_table"] = tukey_df
    return {
        "test_kind": "one_way_anova",
        "test_name": "One-Way ANOVA" + (" + Tukey HSD" if tukey_df is not None else ""),
        "decision_note": (
            "เลือก One-Way ANOVA อัตโนมัติเพราะมี 3 กลุ่มขึ้นไป "
            "(+ Tukey HSD post-hoc เมื่อ ANOVA มีนัยสำคัญ)"
        ),
        "result": res,
    }


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
