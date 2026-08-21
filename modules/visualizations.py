"""
Plotly Visualization Module for Lettuce Research Project.
Provides interactive, high-contrast Plotly figures with High-Contrast Dark Thai Hover Tooltips:
- Bar chart with SD error bars
- Plant-level Boxplot distribution
- Growth trajectory time-series line chart
- Pearson correlation matrix heatmap
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import Optional
from config.settings import COLOR_PALETTE

# High-contrast hover label theme for Plotly charts
PLOTLY_HOVERLABEL_THEME = dict(
    bgcolor="#0f172a",       # Deep slate dark background
    font_size=14,
    font_color="#ffffff",    # Crisp high-contrast white text
    font_family="Inter, Thonburi, sans-serif",
    bordercolor="#3b82f6"    # Vibrant blue accent border
)

def plot_treatment_bar_chart(
    df: pd.DataFrame,
    metric_key: str,
    metric_label: str,
    week_no: Optional[int] = None,
    group_col: str = "treatment",
    group_label: Optional[str] = None,
) -> go.Figure:
    """Generate Bar Chart comparing groups with Standard Deviation error bars & Thai Tooltips.

    When `group_col == "treatment"` (default) the canonical COLOR_PALETTE is
    used so the 5 raw treatments keep their brand colours. For any other
    comparison grouping (e.g. Control/LED, Green Moon/Fame) Plotly's default
    colour cycle is used to avoid colour mismatches.
    """
    sub_df = df.copy()
    if week_no is not None and "week_no" in sub_df.columns:
        sub_df = sub_df[sub_df["week_no"] == week_no]

    if sub_df.empty or metric_key not in sub_df.columns or group_col not in sub_df.columns:
        fig = go.Figure()
        fig.add_annotation(text="ไม่พบข้อมูลสำหรับการสร้างกราฟแท่งเปรียบเทียบ", showarrow=False, font=dict(size=16))
        return fig

    stats_df = sub_df.groupby(group_col)[metric_key].agg(["mean", "std", "count"]).reset_index()
    stats_df["std"] = stats_df["std"].fillna(0)

    title_suffix = f" (สัปดาห์ที่ {week_no})" if week_no else ""
    x_label = group_label or group_col
    color_discrete_map = COLOR_PALETTE if group_col == "treatment" else None

    fig = px.bar(
        stats_df,
        x=group_col,
        y="mean",
        error_y="std",
        color=group_col,
        color_discrete_map=color_discrete_map,
        title=f"การเปรียบเทียบกลุ่มการทดลอง: {metric_label}{title_suffix}",
        labels={group_col: x_label, "mean": metric_label, "std": "ค่าเบี่ยงเบนมาตรฐาน (SD)"},
        text_auto=".2f"
    )

    # Custom Thai Hover Tooltip
    fig.update_traces(
        hovertemplate="<b>กลุ่มการทดลอง</b>: %{x}<br><b>ค่าเฉลี่ย (Mean)</b>: %{y:.2f}<br><b>ส่วนเบี่ยงเบนมาตรฐาน (SD)</b>: ±%{error_y.array:.2f}<extra></extra>"
    )

    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, Thonburi, sans-serif", size=14),
        showlegend=False,
        height=460,
        margin=dict(l=45, r=45, t=65, b=45),
        hoverlabel=PLOTLY_HOVERLABEL_THEME
    )
    return fig

def plot_plant_boxplot(
    df: pd.DataFrame,
    metric_key: str,
    metric_label: str,
    week_no: Optional[int] = None,
    group_col: str = "treatment",
    group_label: Optional[str] = None,
) -> go.Figure:
    """Generate Boxplot showing plant-level distribution with jittered individual data points & Thai Tooltips."""
    sub_df = df.copy()
    if week_no is not None and "week_no" in sub_df.columns:
        sub_df = sub_df[sub_df["week_no"] == week_no]

    if sub_df.empty or metric_key not in sub_df.columns or group_col not in sub_df.columns:
        fig = go.Figure()
        fig.add_annotation(text="ไม่พบข้อมูลสำหรับการสร้างกราฟ Boxplot", showarrow=False, font=dict(size=16))
        return fig

    title_suffix = f" (สัปดาห์ที่ {week_no})" if week_no else ""
    x_label = group_label or group_col
    color_discrete_map = COLOR_PALETTE if group_col == "treatment" else None

    fig = px.box(
        sub_df,
        x=group_col,
        y=metric_key,
        color=group_col,
        points="all",
        hover_data=["plant_id"] if "plant_id" in sub_df.columns else None,
        color_discrete_map=color_discrete_map,
        title=f"การกระจายตัวระดับต้นพืช (Plant Distribution): {metric_label}{title_suffix}",
        labels={group_col: x_label, metric_key: metric_label}
    )

    # Custom Thai Hover Tooltip
    fig.update_traces(
        hovertemplate="<b>กลุ่มการทดลอง</b>: %{x}<br><b>รหัสต้นพืช (Plant ID)</b>: %{customdata[0]}<br><b>ค่าวัด</b>: %{y:.2f}<extra></extra>"
    )

    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, Thonburi, sans-serif", size=14),
        showlegend=False,
        height=460,
        margin=dict(l=45, r=45, t=65, b=45),
        hoverlabel=PLOTLY_HOVERLABEL_THEME
    )
    return fig

def plot_growth_trajectory(
    df: pd.DataFrame, 
    metric_key: str, 
    metric_label: str
) -> go.Figure:
    """Generate Time-Series Line Chart showing mean growth trajectories across weeks with Thai Tooltips."""
    if df.empty or metric_key not in df.columns or "week_no" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="ไม่พบข้อมูลสำหรับการสร้างกราฟแนวโน้มการเจริญเติบโต", showarrow=False, font=dict(size=16))
        return fig
        
    trend_df = df.groupby(["week_no", "treatment"])[metric_key].mean().reset_index()
    
    fig = px.line(
        trend_df,
        x="week_no",
        y=metric_key,
        color="treatment",
        markers=True,
        color_discrete_map=COLOR_PALETTE,
        title=f"แนวโน้มการเจริญเติบโตรายสัปดาห์: {metric_label}",
        labels={"week_no": "สัปดาห์การวัด (Week Number)", metric_key: metric_label, "treatment": "กลุ่มการทดลอง"}
    )
    
    fig.update_traces(
        line=dict(width=3), 
        marker=dict(size=8),
        hovertemplate="<b>สัปดาห์ที่</b>: %{x}<br><b>ค่าเฉลี่ย</b>: %{y:.2f}<extra></extra>"
    )
    
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, Thonburi, sans-serif", size=14),
        height=490,
        hovermode="x unified",
        margin=dict(l=45, r=45, t=65, b=45),
        hoverlabel=PLOTLY_HOVERLABEL_THEME
    )
    return fig

def plot_correlation_heatmap(corr_matrix: pd.DataFrame, p_matrix: pd.DataFrame) -> go.Figure:
    """Generate Pearson Correlation Heatmap with r-values, significance annotations, and Thai Tooltips."""
    if corr_matrix.empty:
        fig = go.Figure()
        fig.add_annotation(text="ไม่พบข้อมูลสำหรับการสร้าง Heatmap เมทริกซ์สหสัมพันธ์", showarrow=False, font=dict(size=16))
        return fig
        
    cols = corr_matrix.columns.tolist()
    z = corr_matrix.values
    
    annot_text = []
    for i in range(len(cols)):
        row_text = []
        for j in range(len(cols)):
            r_val = corr_matrix.iloc[i, j]
            p_val = p_matrix.iloc[i, j] if not p_matrix.empty else 1.0
            sig = "*" if p_val < 0.05 and i != j else ""
            row_text.append(f"{r_val:.2f}{sig}")
        annot_text.append(row_text)
        
    fig = px.imshow(
        z,
        x=cols,
        y=cols,
        color_continuous_scale="RdBu_r",
        zmin=-1.0,
        zmax=1.0,
        title="เมทริกซ์สหสัมพันธ์ Pearson Correlation (ค่า r, * p < 0.05)",
        labels=dict(color="สหสัมพันธ์ (r)")
    )
    
    fig.update_traces(
        text=annot_text,
        texttemplate="%{text}",
        textfont={"size": 13},
        hovertemplate="<b>ตัวแปร Y</b>: %{y}<br><b>ตัวแปร X</b>: %{x}<br><b>ค่า r</b>: %{z:.3f}<extra></extra>"
    )
    
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, Thonburi, sans-serif", size=13),
        height=540,
        margin=dict(l=65, r=65, t=65, b=65),
        hoverlabel=PLOTLY_HOVERLABEL_THEME
    )
    return fig
