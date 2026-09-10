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
from typing import Optional, Dict, List
from config.settings import COLOR_PALETTE
from modules.data_schema import TREATMENTS as _CANONICAL_TREATMENTS

# High-contrast hover label theme for Plotly charts
PLOTLY_HOVERLABEL_THEME = dict(
    bgcolor="#0f172a",       # Deep slate dark background
    font_size=14,
    font_color="#ffffff",    # Crisp high-contrast white text
    font_family="Inter, Thonburi, sans-serif",
    bordercolor="#3b82f6"    # Vibrant blue accent border
)

# Metrics whose values are conceptually integer counts (e.g. number of
# leaves) — chart y-axes for these metrics are formatted as integers so
# no decimal ticks appear.
INTEGER_TICK_METRICS = {"leaf_count"}

# Larger axis typography for readability on tablet / projector displays.
AXIS_TITLE_FONT_SIZE = 16
AXIS_TICK_FONT_SIZE = 14


def get_chart_color_map(overrides: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Return the active treatment -> color mapping.

    Merges the canonical ``COLOR_PALETTE`` with any user-supplied
    ``overrides`` (a {treatment: hex_color} dict). Overrides take
    precedence; missing treatments fall back to the palette default.
    """
    color_map = dict(COLOR_PALETTE)
    if overrides:
        for key, hex_color in overrides.items():
            if key in color_map and hex_color:
                color_map[key] = hex_color
    return color_map


def build_group_color_map(
    comp_spec: Dict[str, object],
    base_colors: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, str]]:
    """Build a {logical_group_label: color} map for comparison-mode charts.

    For ``group_col == "treatment"`` (mode "all" / cross-All) the raw
    treatment palette is returned unchanged. For logical-group modes
    (within / cross with a single lighting filter) each logical group
    inherits the color of the first raw treatment that maps to it, so
    Control vs LED within a variety keeps the light/dark shade contrast
    of the new variety-toned palette.
    """
    base_colors = base_colors if base_colors is not None else dict(COLOR_PALETTE)
    group_col = comp_spec.get("group_col", "treatment")
    group_map = comp_spec.get("group_map", {})

    if group_col == "treatment":
        # Raw treatments on the x-axis — use the palette directly.
        return {t: base_colors.get(t, t) for t in comp_spec.get("treatments", [])}

    # Logical comparison groups — pick the color of the first raw
    # treatment belonging to each group so the shade ordering (light
    # Control -> dark LED) is preserved.
    color_map: Dict[str, str] = {}
    for treatment, group_label in group_map.items():
        if group_label not in color_map and treatment in base_colors:
            color_map[group_label] = base_colors[treatment]
    return color_map or None


def _canonical_treatment_order(df: pd.DataFrame, group_col: str = "treatment") -> Optional[List[str]]:
    """Return the canonical ordering of ``group_col`` values for charts.

    For the raw ``treatment`` column the canonical order from
    ``data_schema.TREATMENTS`` is used so treatments of the same variety
    (Green Moon: Control_GM, LED_GM | Fame: Control_F, LED_F (1),
    LED_F (2)) sit next to each other on the x-axis / legend, instead of
    the alphabetical default that interleaves varieties. Only treatments
    actually present in ``df`` are kept; if none match the canonical list
    the dataframe's own sorted order is returned as a safe fallback.
    """
    if group_col not in df.columns:
        return None
    present = set(df[group_col].dropna().unique().tolist())
    if not present:
        return None
    ordered = [t for t in _CANONICAL_TREATMENTS if t in present]
    # Append any unexpected values (sorted) so nothing is silently dropped.
    ordered += sorted(present - set(ordered))
    return ordered or None

def plot_treatment_bar_chart(
    df: pd.DataFrame,
    metric_key: str,
    metric_label: str,
    week_no: Optional[int] = None,
    group_col: str = "treatment",
    group_label: Optional[str] = None,
    color_map: Optional[Dict[str, str]] = None,
    category_order: Optional[List[str]] = None,
) -> go.Figure:
    """Generate Bar Chart comparing groups with Standard Deviation error bars & Thai Tooltips.

    When `group_col == "treatment"` (default) the canonical COLOR_PALETTE is
    used so the 5 raw treatments keep their brand colours. For any other
    comparison grouping (e.g. Control/LED, Green Moon/Fame) Plotly's default
    colour cycle is used to avoid colour mismatches. Pass an explicit
    ``color_map`` (logical group -> color) to override either behaviour —
    this is how user-customised colors from the analytics tab propagate.
    ``category_order`` forces the x-axis ordering; when omitted and
    ``group_col == "treatment"`` the canonical TREATMENTS order is used so
    treatments of the same variety sit next to each other.
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
    if color_map is not None:
        color_discrete_map = color_map
    else:
        color_discrete_map = COLOR_PALETTE if group_col == "treatment" else None

    # Canonical ordering: treatments of the same variety adjacent.
    if category_order is None and group_col == "treatment":
        category_order = _canonical_treatment_order(stats_df, group_col)
    category_orders = {group_col: category_order} if category_order else None

    is_integer_metric = metric_key in INTEGER_TICK_METRICS
    text_format = ".0f" if is_integer_metric else ".2f"

    fig = px.bar(
        stats_df,
        x=group_col,
        y="mean",
        error_y="std",
        color=group_col,
        color_discrete_map=color_discrete_map,
        category_orders=category_orders,
        title=f"การเปรียบเทียบกลุ่มการทดลอง: {metric_label}{title_suffix}",
        labels={group_col: x_label, "mean": metric_label, "std": "ค่าเบี่ยงเบนมาตรฐาน (SD)"},
        text_auto=text_format
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
        margin=dict(l=55, r=45, t=65, b=55),
        hoverlabel=PLOTLY_HOVERLABEL_THEME
    )
    # Larger axis typography + integer y-axis for count metrics
    y_tickformat = "d" if is_integer_metric else None
    fig.update_xaxes(title_font=dict(size=AXIS_TITLE_FONT_SIZE), tickfont=dict(size=AXIS_TICK_FONT_SIZE))
    fig.update_yaxes(
        title_font=dict(size=AXIS_TITLE_FONT_SIZE),
        tickfont=dict(size=AXIS_TICK_FONT_SIZE),
        tickformat=y_tickformat,
    )
    return fig

def plot_plant_boxplot(
    df: pd.DataFrame,
    metric_key: str,
    metric_label: str,
    week_no: Optional[int] = None,
    group_col: str = "treatment",
    group_label: Optional[str] = None,
    color_map: Optional[Dict[str, str]] = None,
    category_order: Optional[List[str]] = None,
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
    if color_map is not None:
        color_discrete_map = color_map
    else:
        color_discrete_map = COLOR_PALETTE if group_col == "treatment" else None

    # Canonical ordering: treatments of the same variety adjacent.
    if category_order is None and group_col == "treatment":
        category_order = _canonical_treatment_order(sub_df, group_col)
    category_orders = {group_col: category_order} if category_order else None

    fig = px.box(
        sub_df,
        x=group_col,
        y=metric_key,
        color=group_col,
        points="all",
        hover_data=["plant_id"] if "plant_id" in sub_df.columns else None,
        color_discrete_map=color_discrete_map,
        category_orders=category_orders,
        title=f"การกระจายตัวระดับต้นพืช (Plant Distribution): {metric_label}{title_suffix}",
        labels={group_col: x_label, metric_key: metric_label}
    )

    # Custom Thai Hover Tooltip
    fig.update_traces(
        hovertemplate="<b>กลุ่มการทดลอง</b>: %{x}<br><b>รหัสต้นพืช (Plant ID)</b>: %{customdata[0]}<br><b>ค่าวัด</b>: %{y:.2f}<extra></extra>"
    )

    is_integer_metric = metric_key in INTEGER_TICK_METRICS
    y_tickformat = "d" if is_integer_metric else None

    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, Thonburi, sans-serif", size=14),
        showlegend=False,
        height=460,
        margin=dict(l=55, r=45, t=65, b=55),
        hoverlabel=PLOTLY_HOVERLABEL_THEME
    )
    fig.update_xaxes(title_font=dict(size=AXIS_TITLE_FONT_SIZE), tickfont=dict(size=AXIS_TICK_FONT_SIZE))
    fig.update_yaxes(
        title_font=dict(size=AXIS_TITLE_FONT_SIZE),
        tickfont=dict(size=AXIS_TICK_FONT_SIZE),
        tickformat=y_tickformat,
    )
    return fig

def plot_growth_trajectory(
    df: pd.DataFrame, 
    metric_key: str, 
    metric_label: str,
    color_map: Optional[Dict[str, str]] = None,
    category_order: Optional[List[str]] = None,
) -> go.Figure:
    """Generate Time-Series Line Chart showing mean growth trajectories across weeks with Thai Tooltips.

    Each treatment line carries a Standard Deviation error bar (±SD) at
    every measured week so plant-to-plant variability is visible directly
    on the trajectory. The x-axis (week number) is forced to integer ticks
    so no half-week values (e.g. 1.5, 2.5) appear. Count metrics (e.g.
    leaf_count) also get an integer y-axis. ``category_order`` controls
    the legend / trace ordering; when omitted the canonical TREATMENTS
    order is used so treatments of the same variety group together.
    """
    if df.empty or metric_key not in df.columns or "week_no" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="ไม่พบข้อมูลสำหรับการสร้างกราฟแนวโน้มการเจริญเติบโต", showarrow=False, font=dict(size=16))
        return fig
        
    trend_df = (
        df.groupby(["week_no", "treatment"])[metric_key]
        .agg(["mean", "std"])
        .reset_index()
    )
    trend_df["std"] = trend_df["std"].fillna(0)

    active_color_map = color_map if color_map is not None else COLOR_PALETTE

    # Canonical ordering so legend / trace order groups varieties together.
    if category_order is None:
        category_order = _canonical_treatment_order(trend_df, "treatment")
    category_orders = {"treatment": category_order} if category_order else None

    fig = px.line(
        trend_df,
        x="week_no",
        y="mean",
        error_y="std",
        color="treatment",
        markers=True,
        color_discrete_map=active_color_map,
        category_orders=category_orders,
        title=f"แนวโน้มการเจริญเติบโตรายสัปดาห์: {metric_label}",
        labels={"week_no": "สัปดาห์การวัด (Week Number)", metric_key: metric_label, "treatment": "กลุ่มการทดลอง"}
    )
    
    fig.update_traces(
        line=dict(width=3), 
        marker=dict(size=8),
        hovertemplate="<b>สัปดาห์ที่</b>: %{x}<br><b>ค่าเฉลี่ย</b>: %{y:.2f}<br><b>ส่วนเบี่ยงเบนมาตรฐาน (SD)</b>: ±%{error_y.array:.2f}<extra></extra>"
    )

    # Force integer ticks on the week axis (no .5 values) and on the y-axis
    # for count metrics. Larger axis typography for readability.
    week_ticks = sorted(trend_df["week_no"].dropna().unique().tolist())
    is_integer_metric = metric_key in INTEGER_TICK_METRICS
    y_tickformat = "d" if is_integer_metric else None

    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, Thonburi, sans-serif", size=14),
        height=490,
        hovermode="x unified",
        margin=dict(l=55, r=45, t=65, b=55),
        hoverlabel=PLOTLY_HOVERLABEL_THEME
    )
    fig.update_xaxes(
        title_font=dict(size=AXIS_TITLE_FONT_SIZE),
        tickfont=dict(size=AXIS_TICK_FONT_SIZE),
        tickmode="array",
        tickvals=week_ticks,
        tickformat="d",
    )
    fig.update_yaxes(
        title_font=dict(size=AXIS_TITLE_FONT_SIZE),
        tickfont=dict(size=AXIS_TICK_FONT_SIZE),
        tickformat=y_tickformat,
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
