"""
Export Operations Manager for Lettuce Research Project.
Generates multi-sheet Excel workbooks (.xlsx) using openpyxl and CSV exports.
Includes raw data, weekly descriptive summaries, and phytochemical analysis.
"""

import io
import json
import logging
import zipfile
import datetime
import numpy as np
import pandas as pd
from typing import Tuple, List, Optional, Dict, Any

from modules.data_schema import (
    ENG_TO_THAI_COLUMNS, WEEKLY_METRICS, HARVEST_METRICS, PHYTOCHEMICAL_METRICS,
    ALL_ANALYSIS_METRICS
)
from modules.stats_analytics import (
    calculate_descriptive_stats, run_two_way_anova,
    run_tukey_hsd, compute_pearson_correlation,
    run_welch_t_test, run_one_way_anova, run_auto_comparison
)
from modules.visualizations import (
    plot_treatment_bar_chart, plot_plant_boxplot,
    plot_growth_trajectory, plot_correlation_heatmap
)

logger = logging.getLogger(__name__)

# Numeric columns used for the Pearson correlation heatmap (must match app.py tab4)
_PEARSON_NUMERIC_COLS = [
    "canopy_width", "canopy_length", "canopy_height", "leaf_count",
    "fresh_weight", "total_chl", "carotenoids", "total_phenolics",
    "temp_c", "ppfd_led_gm", "soil_ph", "soil_ec", "soil_om",
]

# Single source of truth for the LLM analysis prompt — used both in the
# Tab 4 UI (copy button) and embedded in the exported JSON so users get a
# self-contained file (data + prompt) to feed to ChatGPT / Claude / Gemini.
LLM_ANALYSIS_PROMPT = """You are a plant science research assistant analyzing the effects of LED supplemental lighting on head lettuce (Lactuca sativa). I will provide you with a JSON file exported from the Lectus Research Portal.

## Your Task
Please analyze the JSON and respond IN THAI (ภาษาไทย) with the following:

1. **สรุปผลการเปรียบเทียบ** — พารามิเตอร์ใดบ้างที่มีความแตกต่างอย่างมีนัยสำคัญทางสถิติ (p < 0.05) ระหว่างกลุ่ม
2. **ตารางที่ต้องดู** — สำหรับแต่ละพารามิเตอร์ที่มีนัยสำคัญ บอกว่า:
   - ดูตาราง Descriptive Statistics ตรงกลุ่มใด เพื่อเปรียบเทียบค่าเฉลี่ย
   - ค่าเฉลี่ยต่างกันเท่าไหร่ (mean difference)
3. **กราฟที่ต้องดู** — แนะนำว่าควรดู:
   - Bar Chart (เปรียบเทียบค่าเฉลี่ยระหว่างกลุ่ม มี error bar)
   - Boxplot (ดูการกระจายตัวและความซ้อนทับกันของข้อมูล)
   - Growth Trajectory (ดูแนวโน้มตามสัปดาห์)
4. **จัดอันดับตามขนาดอิทธิพล** — เรียงพารามิเตอร์ตาม Cohen's d (t-test) หรือ F-statistic (ANOVA) จากมากไปน้อย
5. **คำเตือน** — ระบุถ้ามีกลุ่มที่มี sample size น้อย (n < 30) หรือมี warning ในผลลัพธ์

## How to Read the JSON
- `comparison_config` — บอกโหมดการเปรียบเทียบและกลุ่มที่เปรียบเทียบ
- `results[]` — แต่ละ entry คือหนึ่งพารามิเตอร์:
  - `descriptive_stats` — ค่าเฉลี่ย ± SD ของแต่ละกลุ่ม → ดูที่นี่ก่อนเพื่อเห็นความต่างดิบ
  - `statistical_test` — p-value, effect size, significance → ตรวจ p < 0.05
- `pearson_correlation` — ค่า r และ p-value ระหว่างตัวแปร
- `llm_navigation_guide` — คู่มืออ้างอิงว่าตาราง/กราฟแต่ละอันอยู่ตรงไหนในแอป

## Interpretation Rules
- p < 0.05 = มีนัยสำคัญทางสถิติ แต่ไม่จำเป็นต้องสำคัญทางชีววิทยา
- Cohen's d: Negligible < 0.2 < Small < 0.5 < Medium < 0.8 < Large
- สำหรับ ANOVA: Tukey HSD post-hoc บอกว่าคู่กลุ่มใดแตกต่างกัน (ANOVA บอกแค่ "มีอย่างน้อยหนึ่งกลุ่มที่แตกต่าง")

## Context
- Experiment: 2 varieties (Green Moon, Fame) × 2 lighting (Control vs LED supplement)
- 5 experimental plots, 10 plants per plot, weekly measurements
- Output: Thai language (ภาษาไทย) with English technical terms where appropriate

Please analyze the JSON I provide and give me the recommendations above."""

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


# =============================================================================
# Single-Button Full Statistical Export (Tab 4: Statistical Analytics & Graphs)
# =============================================================================

def _metric_has_data(df: pd.DataFrame, metric_key: str) -> bool:
    """Return True if the column exists and has at least one non-NaN value."""
    if metric_key not in df.columns:
        return False
    return df[metric_key].dropna().shape[0] > 0


def _fig_to_png_bytes(fig, width: int = 800, height: int = 450) -> Optional[bytes]:
    """Render a Plotly figure to PNG bytes via kaleido. Returns None on failure."""
    try:
        return fig.to_image(format="png", width=width, height=height, scale=1)
    except Exception as exc:
        logger.warning("kaleido render failed: %s", exc)
        return None


def _generate_statistical_excel(df: pd.DataFrame, env_df: pd.DataFrame) -> bytes:
    """
    Build a .xlsx workbook with all computed statistical tables
    for ALL metrics × ALL weeks.

    Sheets: Descriptive Stats | ANOVA Results | Tukey HSD | Pearson r | Pearson p-value
    """
    output = io.BytesIO()

    # ---- Build week list ----
    weeks: List = []
    if "week_no" in df.columns:
        weeks = sorted([w for w in df["week_no"].dropna().unique().tolist()])
    week_options = ["All Weeks"] + [w for w in weeks]

    metric_items = list(ALL_ANALYSIS_METRICS.items())

    desc_rows: List[dict] = []
    anova_rows: List[dict] = []
    tukey_rows: List[dict] = []

    for metric_key, metric_label in metric_items:
        if not _metric_has_data(df, metric_key):
            continue
        for week_opt in week_options:
            week_no = None if week_opt == "All Weeks" else week_opt
            sub_df = df.copy()
            if week_no is not None and "week_no" in sub_df.columns:
                sub_df = sub_df[sub_df["week_no"] == week_no]

            week_label = week_opt if week_opt == "All Weeks" else f"Week {week_opt}"

            # Descriptive
            try:
                desc_df = calculate_descriptive_stats(sub_df, metric_key, group_by="treatment")
                if not desc_df.empty:
                    for _, r in desc_df.iterrows():
                        desc_rows.append({
                            "Metric": metric_label,
                            "Week": week_label,
                            "Treatment": r.get("treatment"),
                            "Count": r.get("Count"),
                            "Mean ± SD": r.get("Mean_±_SD"),
                            "Min": r.get("Min"),
                            "Max": r.get("Max"),
                        })
            except Exception:
                pass

            # Two-Way ANOVA
            try:
                anova_res = run_two_way_anova(sub_df, metric_key)
                if "error" not in anova_res:
                    p_var = anova_res.get("p_variety", float("nan"))
                    p_light = anova_res.get("p_lighting", float("nan"))
                    p_int = anova_res.get("p_interaction", float("nan"))
                    anova_rows.append({
                        "Metric": metric_label,
                        "Week": week_label,
                        "p_variety": p_var,
                        "p_lighting": p_light,
                        "p_interaction": p_int,
                        "Variety Sig (p<0.05)": "Yes" if p_var < 0.05 else "No",
                        "Lighting Sig (p<0.05)": "Yes" if p_light < 0.05 else "No",
                        "Interaction Sig (p<0.05)": "Yes" if p_int < 0.05 else "No",
                    })
            except Exception:
                pass

            # Tukey HSD
            try:
                tukey_df = run_tukey_hsd(sub_df, metric_key)
                if tukey_df is not None and not tukey_df.empty:
                    for _, r in tukey_df.iterrows():
                        tukey_rows.append({
                            "Metric": metric_label,
                            "Week": week_label,
                            **{c: r.get(c) for c in tukey_df.columns},
                        })
            except Exception:
                pass

    # ---- Pearson correlation ----
    corr_df = pd.DataFrame()
    p_df = pd.DataFrame()
    try:
        joined = df.copy()
        if not env_df.empty and "week_no" in env_df.columns and "week_no" in joined.columns:
            joined = joined.merge(env_df, on="week_no", how="left", suffixes=("", "_env"))
        valid_cols = [c for c in _PEARSON_NUMERIC_COLS if c in joined.columns]
        corr_df, p_df = compute_pearson_correlation(joined, valid_cols)
    except Exception:
        pass

    # ---- Assemble workbook ----
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if desc_rows:
            pd.DataFrame(desc_rows).to_excel(writer, sheet_name="Descriptive Stats", index=False)
        else:
            pd.DataFrame({"Status": ["No descriptive statistics available"]}).to_excel(
                writer, sheet_name="Descriptive Stats", index=False)

        if anova_rows:
            pd.DataFrame(anova_rows).to_excel(writer, sheet_name="ANOVA Results", index=False)
        else:
            pd.DataFrame({"Status": ["No ANOVA results available"]}).to_excel(
                writer, sheet_name="ANOVA Results", index=False)

        if tukey_rows:
            pd.DataFrame(tukey_rows).to_excel(writer, sheet_name="Tukey HSD", index=False)
        else:
            pd.DataFrame({"Status": ["No Tukey HSD results available"]}).to_excel(
                writer, sheet_name="Tukey HSD", index=False)

        if not corr_df.empty:
            corr_df.to_excel(writer, sheet_name="Pearson r")
        else:
            pd.DataFrame({"Status": ["No Pearson correlation available"]}).to_excel(
                writer, sheet_name="Pearson r", index=False)

        if not p_df.empty:
            p_df.to_excel(writer, sheet_name="Pearson p-value")
        else:
            pd.DataFrame({"Status": ["No Pearson p-values available"]}).to_excel(
                writer, sheet_name="Pearson p-value", index=False)

    return output.getvalue()


def generate_statistical_export_package(df: pd.DataFrame, env_df: pd.DataFrame) -> bytes:
    """
    Build a ZIP archive containing:
      - statistical_analysis.xlsx  (computed tables for ALL metrics × ALL weeks)
      - charts/                    (PNG chart images + HTML gallery index)

    ZIP structure:
      statistical_analysis.xlsx
      charts/
        index.html              (gallery showing all PNG charts)
        png/
          bar/                  (bar chart PNGs per metric × week)
          boxplot/              (boxplot PNGs per metric × week)
          growth/               (growth trajectory PNGs per metric)
          heatmap.png           (single Pearson heatmap PNG)
    """
    zip_buf = io.BytesIO()

    if df.empty:
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README.txt",
                "No experiment data available. Please upload or record data first.")
        return zip_buf.getvalue()

    # ---- Build week list ----
    weeks: List = []
    if "week_no" in df.columns:
        weeks = sorted([w for w in df["week_no"].dropna().unique().tolist()])
    week_options = ["All Weeks"] + [w for w in weeks]

    metric_items = list(ALL_ANALYSIS_METRICS.items())

    # Track generated charts for the gallery index
    chart_entries: List[dict] = []  # {type, metric, week, png_path}

    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Excel with all computed tables
        xlsx_bytes = _generate_statistical_excel(df, env_df)
        zf.writestr("statistical_analysis.xlsx", xlsx_bytes)

        # 2. Render PNG charts for each metric × week
        for metric_key, metric_label in metric_items:
            if not _metric_has_data(df, metric_key):
                continue

            metric_slug = metric_key

            # -- Growth trajectory (one per metric) --
            try:
                fig_line = plot_growth_trajectory(df, metric_key, metric_label)
                png = _fig_to_png_bytes(fig_line, width=900, height=500)
                if png:
                    png_path = f"charts/png/growth/{metric_slug}.png"
                    zf.writestr(png_path, png)
                    chart_entries.append({
                        "type": "Growth Trajectory",
                        "metric": metric_label,
                        "week": "All Weeks",
                        "png_path": png_path,
                    })
            except Exception as exc:
                logger.debug("growth PNG skip %s: %s", metric_key, exc)

            # -- Bar & Boxplot per week --
            for week_opt in week_options:
                week_no = None if week_opt == "All Weeks" else week_opt
                week_label = week_opt if week_opt == "All Weeks" else f"Week {week_opt}"
                week_slug = f"w{week_opt}" if week_opt != "All Weeks" else "all"

                # Bar chart
                try:
                    fig_bar = plot_treatment_bar_chart(df, metric_key, metric_label, week_no=week_no)
                    png = _fig_to_png_bytes(fig_bar, width=900, height=500)
                    if png:
                        png_path = f"charts/png/bar/{metric_slug}_{week_slug}.png"
                        zf.writestr(png_path, png)
                        chart_entries.append({
                            "type": "Bar Chart",
                            "metric": metric_label,
                            "week": week_label,
                            "png_path": png_path,
                        })
                except Exception as exc:
                    logger.debug("bar PNG skip %s/%s: %s", metric_key, week_label, exc)

                # Boxplot
                try:
                    fig_box = plot_plant_boxplot(df, metric_key, metric_label, week_no=week_no)
                    png = _fig_to_png_bytes(fig_box, width=900, height=500)
                    if png:
                        png_path = f"charts/png/boxplot/{metric_slug}_{week_slug}.png"
                        zf.writestr(png_path, png)
                        chart_entries.append({
                            "type": "Boxplot",
                            "metric": metric_label,
                            "week": week_label,
                            "png_path": png_path,
                        })
                except Exception as exc:
                    logger.debug("box PNG skip %s/%s: %s", metric_key, week_label, exc)

        # -- Heatmap (single) --
        try:
            joined_h = df.copy()
            if not env_df.empty and "week_no" in env_df.columns and "week_no" in joined_h.columns:
                joined_h = joined_h.merge(env_df, on="week_no", how="left", suffixes=("", "_env"))
            valid_h_cols = [c for c in _PEARSON_NUMERIC_COLS if c in joined_h.columns]
            heat_r, heat_p = compute_pearson_correlation(joined_h, valid_h_cols)
            if not heat_r.empty:
                fig_heat = plot_correlation_heatmap(heat_r, heat_p)
                png = _fig_to_png_bytes(fig_heat, width=1000, height=700)
                if png:
                    png_path = "charts/png/heatmap.png"
                    zf.writestr(png_path, png)
                    chart_entries.append({
                        "type": "Heatmap",
                        "metric": "Pearson Correlation",
                        "week": "—",
                        "png_path": png_path,
                    })
        except Exception as exc:
            logger.debug("heatmap PNG skip: %s", exc)

        # -- Gallery index HTML --
        gallery_items_html = ""
        if chart_entries:
            for i, e in enumerate(chart_entries, 1):
                # Use relative path from charts/ directory
                rel_path = e["png_path"].replace("charts/", "", 1)
                gallery_items_html += f"""
<div class="chart-card">
  <h3>{i}. {e['type']} — {e['metric']} ({e['week']})</h3>
  <img src="{rel_path}" alt="{e['type']} {e['metric']} {e['week']}" loading="lazy">
</div>"""
        else:
            gallery_items_html = "<p>No charts generated (no numerical data available).</p>"

        index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Statistical Analytics — Chart Gallery</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         max-width: 1100px; margin: 0 auto; padding: 1.5rem; background: #f7fafc; }}
  h1 {{ color: #1a365d; border-bottom: 3px solid #2b6cb0; padding-bottom: 0.5rem; }}
  .summary {{ background: #edf2f7; padding: 1rem 1.5rem; border-radius: 8px; margin: 1rem 0 2rem; }}
  .summary strong {{ color: #2b6cb0; }}
  .chart-card {{ background: white; margin: 1.5rem 0; padding: 1rem 1.5rem;
                border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .chart-card h3 {{ color: #2d3748; margin-top: 0; font-size: 1.1rem; }}
  .chart-card img {{ max-width: 100%; height: auto; display: block; margin: 0 auto;
                     border: 1px solid #e2e8f0; border-radius: 4px; }}
  .note {{ color: #718096; font-size: 0.9rem; margin-top: 2rem; }}
</style>
</head>
<body>
<h1>Statistical Analytics & Graphs — Full Export</h1>
<div class="summary">
  <p><strong>{len(chart_entries)}</strong> charts generated across all metrics and weeks.</p>
  <p>Files in this ZIP:
    <strong>statistical_analysis.xlsx</strong> — all computed statistical tables (Descriptive Stats, ANOVA, Tukey HSD, Pearson r, Pearson p-value).<br>
    <strong>charts/png/</strong> — PNG chart images (bar, boxplot, growth, heatmap).
  </p>
</div>
{gallery_items_html}
<p class="note">Tip: Open <code>statistical_analysis.xlsx</code> with Excel/Google Sheets for the full computed tables.</p>
</body>
</html>"""
        zf.writestr("charts/index.html", index_html)

    return zip_buf.getvalue()


# =============================================================================
# JSON Export for AI / LLM consumption (Tab 4 — Comparison Mode results)
# =============================================================================

class _NumpyJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types and NaN/Infinity safely."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            val = float(obj)
            if np.isnan(val) or np.isinf(val):
                return None
            return val
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        if isinstance(obj, (pd.Timestamp, datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super().default(obj)


def _safe_float(val) -> Optional[float]:
    """Convert a numeric value to float, returning None for NaN/None."""
    if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _descriptive_to_dicts(desc_df: pd.DataFrame, group_col: str) -> List[Dict[str, Any]]:
    """Convert a descriptive-stats DataFrame into a list of JSON-friendly dicts."""
    if desc_df.empty:
        return []
    rows = []
    for _, r in desc_df.iterrows():
        rows.append({
            "group": str(r.get(group_col, "")),
            "n": int(r.get("Count", 0)) if not pd.isna(r.get("Count")) else 0,
            "mean": _safe_float(r.get("Mean")),
            "sd": _safe_float(r.get("SD")),
            "min": _safe_float(r.get("Min")),
            "max": _safe_float(r.get("Max")),
        })
    return rows


def _t_test_to_dict(result: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Welch t-test result dict into a JSON-friendly structure."""
    if "error" in result:
        return {"error": result["error"]}
    return {
        "test_kind": "t_test",
        "test_name": result.get("test_name", "Welch's two-sample t-test"),
        "group_labels": result.get("group_labels", []),
        "n_group_1": result.get("n1"),
        "n_group_2": result.get("n2"),
        "mean_group_1": _safe_float(result.get("mean_1")),
        "mean_group_2": _safe_float(result.get("mean_2")),
        "sd_group_1": _safe_float(result.get("sd_1")),
        "sd_group_2": _safe_float(result.get("sd_2")),
        "t_statistic": _safe_float(result.get("t_stat")),
        "df_welch": _safe_float(result.get("df")),
        "p_value": _safe_float(result.get("p_value")),
        "significant": bool(result.get("significant", False)),
        "mean_difference": _safe_float(result.get("mean_diff")),
        "ci_95": [_safe_float(result.get("ci_low")), _safe_float(result.get("ci_high"))],
        "cohens_d": _safe_float(result.get("cohens_d")),
        "cohens_d_interpretation": result.get("cohens_d_interpretation", ""),
        "warning": result.get("warning"),
    }


def _one_way_anova_to_dict(result: Dict[str, Any]) -> Dict[str, Any]:
    """Convert one-way ANOVA result dict into a JSON-friendly structure."""
    if "error" in result:
        return {"error": result["error"]}
    tukey_df = result.get("tukey_table")
    tukey_rows = []
    if tukey_df is not None and not tukey_df.empty:
        for _, r in tukey_df.iterrows():
            tukey_rows.append({
                "group_1": str(r.get("group1", "")),
                "group_2": str(r.get("group2", "")),
                "mean_diff": _safe_float(r.get("meandiff")),
                "p_value": _safe_float(r.get("p-adj")),
                "lower_ci": _safe_float(r.get("lower")),
                "upper_ci": _safe_float(r.get("upper")),
                "reject": bool(r.get("reject", False)),
            })
    return {
        "test_kind": "one_way_anova",
        "test_name": result.get("test_name", "One-Way ANOVA"),
        "group_labels": result.get("group_labels", []),
        "group_counts": {str(k): int(v) for k, v in result.get("group_counts", {}).items()},
        "f_statistic": _safe_float(result.get("f_stat")),
        "p_value": _safe_float(result.get("p_value")),
        "significant": bool(result.get("significant", False)),
        "tukey_hsd": tukey_rows,
        "warning": result.get("warning"),
    }


def _two_way_anova_to_dict(result: Dict[str, Any]) -> Dict[str, Any]:
    """Convert two-way ANOVA result dict into a JSON-friendly structure."""
    if "error" in result:
        return {"error": result["error"]}
    return {
        "test_kind": "two_way_anova",
        "test_name": "Two-Way ANOVA (Variety × Lighting)",
        "p_variety": _safe_float(result.get("p_variety")),
        "p_lighting": _safe_float(result.get("p_lighting")),
        "p_interaction": _safe_float(result.get("p_interaction")),
        "variety_significant": bool(_safe_float(result.get("p_variety")) is not None and _safe_float(result.get("p_variety")) < 0.05),
        "lighting_significant": bool(_safe_float(result.get("p_lighting")) is not None and _safe_float(result.get("p_lighting")) < 0.05),
        "interaction_significant": bool(_safe_float(result.get("p_interaction")) is not None and _safe_float(result.get("p_interaction")) < 0.05),
    }


def _pearson_to_dict(corr_df: pd.DataFrame, p_df: pd.DataFrame, variables: List[str]) -> Dict[str, Any]:
    """Convert Pearson correlation matrices into JSON-friendly nested dicts."""
    if corr_df.empty:
        return {"variables": variables, "r_matrix": {}, "p_matrix": {}}
    r_matrix = {}
    p_matrix = {}
    for c1 in variables:
        r_matrix[c1] = {}
        p_matrix[c1] = {}
        for c2 in variables:
            r_matrix[c1][c2] = _safe_float(corr_df.loc[c1, c2]) if c1 in corr_df.index and c2 in corr_df.columns else None
            p_matrix[c1][c2] = _safe_float(p_df.loc[c1, c2]) if c1 in p_df.index and c2 in p_df.columns else None
    return {"variables": variables, "r_matrix": r_matrix, "p_matrix": p_matrix}


def generate_comparison_json(
    df: pd.DataFrame,
    env_df: pd.DataFrame,
    comp_spec: Dict[str, Any],
    metric_keys: List[str],
    metric_labels: Dict[str, str],
    week_filter: str = "All Weeks",
    pearson_variables: Optional[List[str]] = None,
) -> str:
    """
    Build a JSON string summarizing the Tab 4 comparison-mode analysis results,
    structured for consumption by an LLM / AI assistant.

    Parameters
    ----------
    df : pd.DataFrame
        Full experiment DataFrame (will be filtered by week + comparison treatments).
    env_df : pd.DataFrame
        Environment DataFrame (for Pearson correlation join).
    comp_spec : dict
        Output of data_schema.build_comparison_groups() — must contain keys:
        treatments, group_map, group_col, group_label, summary, test_kind, n_groups.
    metric_keys : list[str]
        Selected analysis metric keys (e.g. ["canopy_width", "fresh_weight"]).
    metric_labels : dict[str, str]
        Mapping metric_key -> human-readable label.
    week_filter : str
        "All Weeks" or a specific week number (as string).
    pearson_variables : list[str], optional
        Variables selected for Pearson correlation. If None or <2, correlation
        section is omitted.

    Returns
    -------
    str — pretty-printed JSON (UTF-8, ensure_ascii=False).
    """
    # ---- Filter data by week ----
    filtered_df = df.copy()
    if week_filter != "All Weeks" and "week_no" in filtered_df.columns:
        try:
            filtered_df = filtered_df[filtered_df["week_no"] == float(week_filter)]
        except (ValueError, TypeError):
            pass

    # ---- Filter by comparison treatments + add comparison_group column ----
    treatments = comp_spec.get("treatments", [])
    group_col = comp_spec.get("group_col", "treatment")
    group_map = comp_spec.get("group_map", {})

    analysis_df = filtered_df[filtered_df["treatment"].isin(treatments)].copy()
    if group_col == "comparison_group":
        analysis_df["comparison_group"] = analysis_df["treatment"].map(group_map)

    # ---- Build per-metric results ----
    results: List[Dict[str, Any]] = []
    for metric_key in metric_keys:
        if metric_key not in analysis_df.columns:
            continue
        metric_label = metric_labels.get(metric_key, metric_key)

        # Descriptive stats
        desc_df = calculate_descriptive_stats(analysis_df, metric_key, group_by=group_col)
        desc_rows = _descriptive_to_dicts(desc_df, group_col)

        # Statistical test — choose based on comp_spec test_kind
        test_kind = comp_spec.get("test_kind", "two_way_anova")
        test_dict: Dict[str, Any]
        if test_kind == "two_way_anova":
            anova_res = run_two_way_anova(analysis_df, metric_key)
            test_dict = _two_way_anova_to_dict(anova_res)
        else:
            auto_res = run_auto_comparison(analysis_df, metric_key, group_col=group_col)
            if "error" in auto_res or "error" in auto_res.get("result", {}):
                err = auto_res.get("error") or auto_res.get("result", {}).get("error")
                test_dict = {"test_kind": test_kind, "error": err}
            else:
                inner = auto_res["result"]
                if auto_res["test_kind"] == "t_test":
                    test_dict = _t_test_to_dict(inner)
                else:
                    test_dict = _one_way_anova_to_dict(inner)

        results.append({
            "metric_key": metric_key,
            "metric_label": metric_label,
            "descriptive_stats": desc_rows,
            "statistical_test": test_dict,
        })

    # ---- Pearson correlation (optional) ----
    pearson_section: Optional[Dict[str, Any]] = None
    if pearson_variables and len(pearson_variables) >= 2:
        try:
            joined = df.copy()
            if not env_df.empty and "week_no" in env_df.columns and "week_no" in joined.columns:
                joined = joined.merge(env_df, on="week_no", how="left", suffixes=("", "_env"))
            valid_cols = [c for c in pearson_variables if c in joined.columns]
            if len(valid_cols) >= 2:
                corr_df, p_df = compute_pearson_correlation(joined, valid_cols)
                pearson_section = _pearson_to_dict(corr_df, p_df, valid_cols)
        except Exception as exc:
            pearson_section = {"error": f"Pearson correlation failed: {str(exc)}"}

    # ---- Assemble final JSON structure ----
    output = {
        "report_metadata": {
            "generated_at": datetime.datetime.now().isoformat(),
            "app": "Lectus Research Portal — Head Lettuce LED Supplementation Study",
            "experiment_design": (
                "2 varieties (Green Moon, Fame) × 2 lighting conditions "
                "(Natural/Control vs LED supplement), 5 experimental plots, "
                "10 plants per plot, weekly measurements"
            ),
        },
        "llm_prompt": LLM_ANALYSIS_PROMPT,
        "comparison_config": {
            "mode": comp_spec.get("summary", "").split("—")[0].strip() if "—" in comp_spec.get("summary", "") else "",
            "summary": comp_spec.get("summary", ""),
            "test_kind": comp_spec.get("test_kind", ""),
            "n_groups": comp_spec.get("n_groups", 0),
            "group_col": group_col,
            "group_label": comp_spec.get("group_label", ""),
            "treatment_to_group_map": {str(k): str(v) for k, v in group_map.items()},
            "week_filter": week_filter,
            "n_observations_in_analysis": int(len(analysis_df)),
        },
        "results": results,
        "pearson_correlation": pearson_section,
        "llm_navigation_guide": {
            "how_to_read": (
                "Each entry in 'results' corresponds to one measured plant parameter. "
                "Read 'descriptive_stats' first to see mean ± SD per group, then check "
                "'statistical_test' for p-value and effect size. A p-value < 0.05 means "
                "the difference between groups is statistically significant."
            ),
            "where_to_look_in_app": {
                "descriptive_stats_table": (
                    "In the app's Tab 4, expand the metric's expander → 'Descriptive Statistics' table "
                    "shows Mean ± SD, Min, Max, and Count per group."
                ),
                "statistical_test_card": (
                    "Below the descriptive table, the 'Statistical Test' card shows p-value, "
                    "test name, and effect size (Cohen's d for t-test, F-statistic for ANOVA)."
                ),
                "bar_chart": (
                    "The Bar Chart (left) compares group means with SD error bars — "
                    "use this to visually compare which group has higher/lower values."
                ),
                "boxplot": (
                    "The Boxplot (right) shows data distribution per group — "
                    "use this to see overlap, outliers, and spread between groups."
                ),
                "growth_trajectory": (
                    "The Growth Trajectory line chart shows mean values across weeks per treatment — "
                    "use this to see trends over time."
                ),
                "anova_tukey_table": (
                    "For ANOVA results, expand 'ANOVA Table & Tukey HSD Post-Hoc' to see "
                    "which specific group pairs differ significantly."
                ),
            },
            "interpretation_tips": [
                "Statistical significance (p < 0.05) does NOT imply biological importance — also check effect size (Cohen's d).",
                "Cohen's d: Negligible < 0.2 < Small < 0.5 < Medium < 0.8 < Large.",
                "Small sample sizes (n < 30 per group) reduce test power — note warnings in results.",
                "For ANOVA, Tukey HSD post-hoc identifies WHICH pairs differ (ANOVA only tells you 'at least one differs').",
            ],
        },
    }

    return json.dumps(output, indent=2, ensure_ascii=False, cls=_NumpyJSONEncoder)
