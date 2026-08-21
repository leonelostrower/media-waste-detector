"""Plotly figures for the path-to-conversion report.

Each builder returns a figure and, where the report narrative needs the
underlying numbers, the data frame or rows that produced it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ptc_pipeline import MID_FUNNEL, PATH_TYPE_COLORS, PATH_TYPE_ORDER, SEARCH, Taxonomy

FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"
INK = "#3C3C3E"
MUTED = "#787C96"
GRID = "rgba(0,0,0,0.07)"

POSITION_COLORS = {
    "First": "#4C72B0",
    "Middle": "#DD8452",
    "Last": "#55A868",
    "Only touch": "#C44E52",
}


def _layout(fig: go.Figure, title: str, height: int = 420, **kwargs) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=INK), x=0, xanchor="left"),
        font=dict(family=FONT, size=12, color=INK),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=10, r=10, t=56, b=10),
        hoverlabel=dict(font_family=FONT),
        **kwargs,
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    return fig


def _empty(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5,
        font=dict(size=13, color=MUTED),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _layout(fig, "", height=220)


# ----------------------------------------------------------------------------
# 1. Daily mid-funnel timeseries
# ----------------------------------------------------------------------------

def chart_daily_mid_funnel(touches: pd.DataFrame, taxonomy: Taxonomy) -> go.Figure:
    """Daily touch volume per mid-funnel platform. Shades any leading stretch
    with no mid-funnel tagging at all, and marks platforms that launched
    mid-window, so the chart reads correctly whether or not the export covers an
    activation ramp-up."""
    mid_platforms = taxonomy.mid_funnel_platforms
    if touches.empty or not mid_platforms:
        return _empty("No mid-funnel touches recorded.")

    daily = touches.copy()
    daily["day"] = daily["touch_time"].dt.normalize()
    counts = daily.groupby(["day", "platform"]).size().unstack(fill_value=0)
    present = [p for p in mid_platforms if p in counts.columns]
    if not present:
        return _empty("No mid-funnel touches recorded.")

    colors = taxonomy.platform_colors
    fig = go.Figure()
    for platform in present:
        fig.add_trace(go.Scatter(
            x=counts.index, y=counts[platform], mode="lines+markers", name=platform,
            line=dict(color=colors.get(platform), width=2), marker=dict(size=4),
            hovertemplate=f"<b>{platform}</b><br>%{{x|%b %d, %Y}}<br>%{{y}} touches<extra></extra>",
        ))

    totals = counts[present].sum(axis=1)
    live_days = totals[totals > 0].index
    if len(live_days):
        first_live, day_one = min(live_days), counts.index.min()
        if (first_live - day_one).days > 1:
            fig.add_vrect(
                x0=day_one, x1=first_live, fillcolor="gray", opacity=0.10, line_width=0,
                annotation_text="No mid-funnel tagging yet", annotation_position="top left",
                annotation_font=dict(size=10, color=MUTED),
            )
        for platform in present:
            platform_days = counts[platform][counts[platform] > 0].index
            if len(platform_days) and (min(platform_days) - first_live).days > 7:
                fig.add_vline(
                    x=min(platform_days), line=dict(color=colors.get(platform), dash="dash", width=1),
                    annotation_text=f"{platform} starts", annotation_position="top",
                    annotation_font=dict(size=10, color=colors.get(platform)),
                )

    _layout(fig, "Daily mid-funnel touches by platform (by touch date)", height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1))
    fig.update_yaxes(title_text="Touches")
    return fig


# ----------------------------------------------------------------------------
# 2. Conversions by path type
# ----------------------------------------------------------------------------

def chart_path_type(paths: pd.DataFrame) -> go.Figure:
    counts = paths["path_type"].value_counts()
    share = paths["path_type"].value_counts(normalize=True)
    order = [p for p in PATH_TYPE_ORDER if p in counts.index]
    if not order:
        return _empty("No conversions to plot.")

    fig = go.Figure(go.Bar(
        x=order,
        y=[counts[p] for p in order],
        marker_color=[PATH_TYPE_COLORS.get(p, "#B0B0B0") for p in order],
        text=[f"{counts[p]:,}<br>({share[p]:.1%})" for p in order],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y:,} conversions<extra></extra>",
    ))
    _layout(fig, "Conversions by Path Type (Campaign Level)", height=400, showlegend=False)
    fig.update_yaxes(title_text="Conversions", range=[0, counts.max() * 1.18])
    return fig


# ----------------------------------------------------------------------------
# 3. Top converting paths (DV360-style chevrons)
# ----------------------------------------------------------------------------

def chart_top_paths(
    paths: pd.DataFrame,
    taxonomy: Taxonomy,
    level: str = "platform",
    n_top: int = 8,
) -> tuple[go.Figure, list[dict]]:
    """Collapses each conversion's touch sequence into ordered
    distinct-consecutive steps (Reddit > Reddit > Search becomes
    Reddit > Search), then ranks the most common journeys by share of
    conversions. Position 1 (rightmost) is the converting (last) touch."""
    column = "platform_sequence" if level == "platform" else "channel_sequence"

    def collapse(sequence: str) -> str:
        steps: list[str] = []
        for step in sequence.split(" > "):
            if not steps or steps[-1] != step:
                steps.append(step)
        return " > ".join(steps)

    if paths.empty:
        return _empty("No conversions to plot."), []

    journeys = paths[column].map(collapse)
    total = len(paths)
    top = journeys.value_counts().head(n_top)
    rows = [
        {"journey": journey, "conversions": int(count), "pct": count / total}
        for journey, count in top.items()
    ]
    if not rows:
        return _empty("No conversions to plot."), []

    colors = dict(taxonomy.platform_colors)
    colors.update({SEARCH: "#4285F4", MID_FUNNEL: "#FF7043", "Other": "#B0B0B0"})
    short = {"Google Search": "Google", "MSN Search": "MSN"}

    sequences = [row["journey"].split(" > ") for row in rows]
    max_len = max(len(s) for s in sequences)
    seg_w, gap, notch, height = 1.0, 0.06, 0.28, 0.72
    n_rows = len(rows)
    x_right = float(max_len)

    fig = go.Figure()
    shapes, annotations = [], []
    for row_index, (row, sequence) in enumerate(zip(rows, sequences)):
        y = n_rows - 1 - row_index
        reversed_steps = list(reversed(sequence))  # rightmost = converting touch
        for index, label in enumerate(reversed_steps):
            x1 = x_right - index * (seg_w + gap)
            x0 = x1 - seg_w
            left_notch = notch if index < len(reversed_steps) - 1 else 0.0
            shapes.append(dict(
                type="path",
                path=(
                    f"M {x0},{y - height / 2} L {x1 - notch},{y - height / 2} L {x1},{y} "
                    f"L {x1 - notch},{y + height / 2} L {x0},{y + height / 2} "
                    f"L {x0 + left_notch},{y} Z"
                ),
                fillcolor=colors.get(label, "#9AB4E8"),
                line=dict(color="white", width=1.5),
                layer="below",
            ))
            annotations.append(dict(
                x=(x0 + x1) / 2 + (notch / 2 if left_notch else 0), y=y,
                text=f"<b>{short.get(label, label)}</b>", showarrow=False,
                font=dict(color="white", size=11),
            ))
        annotations.append(dict(
            x=x_right + 0.35, y=y, text=f"<b>{row['pct'] * 100:.0f}%</b>",
            showarrow=False, xanchor="left", font=dict(color="#1a73e8", size=13),
        ))

    for position in range(1, max_len + 1):
        annotations.append(dict(
            x=x_right - (position - 1) * (seg_w + gap) - seg_w / 2, y=-0.85,
            text=str(position), showarrow=False, font=dict(color=MUTED, size=10),
        ))
    annotations.append(dict(
        x=x_right + 0.35, y=n_rows - 0.2, text="<b>% of Conv.</b>", showarrow=False,
        xanchor="left", font=dict(color=MUTED, size=10),
    ))
    annotations.append(dict(
        x=x_right - max_len * (seg_w + gap) - 0.7, y=-1.35, xanchor="left",
        text="<i>Ad exposures - position 1 = converting (last) touch</i>",
        showarrow=False, font=dict(color=MUTED, size=10),
    ))

    fig.update_layout(shapes=shapes, annotations=annotations)
    _layout(fig, "Top Converting Paths, grouped by Platform",
            height=int(58 * n_rows + 110), showlegend=False)
    fig.update_xaxes(
        visible=False, range=[x_right - max_len * (seg_w + gap) - 0.8, x_right + 1.9],
    )
    fig.update_yaxes(visible=False, range=[-1.7, n_rows - 0.05])
    return fig, rows


# ----------------------------------------------------------------------------
# 4. Transition heatmap
# ----------------------------------------------------------------------------

def chart_transition_heatmap(
    touches: pd.DataFrame,
    taxonomy: Taxonomy,
) -> tuple[go.Figure, pd.DataFrame]:
    """Full sequential (Markov-style) transition analysis: for every consecutive
    touch pair in every path, what platform comes next? Row-normalized, so each
    row sums to 100% — the diagonal is platform loyalty (repeat exposure),
    off-diagonal is cross-platform migration."""
    order = taxonomy.platforms
    if touches.empty or not order:
        return _empty("No touches to plot."), pd.DataFrame()

    ordered = touches.sort_values(["Conversion ID", "touch_order"]).copy()
    ordered["next_platform"] = ordered.groupby("Conversion ID")["platform"].shift(-1)
    transitions = ordered.dropna(subset=["next_platform"])
    if transitions.empty:
        return _empty("No multi-touch paths to plot."), pd.DataFrame()

    matrix = pd.crosstab(
        transitions["platform"], transitions["next_platform"], normalize="index"
    ).reindex(index=order, columns=order).fillna(0)

    fig = go.Figure(go.Heatmap(
        z=matrix.values, x=list(matrix.columns), y=list(matrix.index),
        colorscale="YlOrRd", zmin=0, zmax=1,
        text=[[f"{value:.0%}" if value > 0 else "" for value in row] for row in matrix.values],
        texttemplate="%{text}", textfont=dict(size=10),
        colorbar=dict(title="Share", tickformat=".0%", thickness=12),
        hovertemplate="<b>%{y}</b> then <b>%{x}</b><br>%{z:.1%}<extra></extra>",
    ))
    _layout(fig, "Platform to Next-Touch Platform Transition Probability (Row %)", height=460)
    fig.update_xaxes(title_text="Next touch platform", tickangle=-30)
    fig.update_yaxes(title_text="Current touch platform", autorange="reversed")
    return fig, matrix


# ----------------------------------------------------------------------------
# 5. Path length and time to convert
# ----------------------------------------------------------------------------

def chart_length_time(by_type: pd.DataFrame) -> go.Figure:
    order = [p for p in PATH_TYPE_ORDER if p in by_type.index]
    if not order:
        return _empty("No conversions to plot.")

    colors = [PATH_TYPE_COLORS.get(p, "#B0B0B0") for p in order]
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Avg. Path Length by Path Type", "Avg. Days From First Touch to Conversion"),
    )
    fig.add_trace(go.Bar(
        x=order, y=[by_type.loc[p, "avg_path_length"] for p in order],
        marker_color=colors, text=[f"{by_type.loc[p, 'avg_path_length']:.2f}" for p in order],
        textposition="outside", hovertemplate="<b>%{x}</b><br>%{y:.2f} touches<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=order, y=[by_type.loc[p, "avg_days_to_convert"] for p in order],
        marker_color=colors, text=[f"{by_type.loc[p, 'avg_days_to_convert']:.2f}" for p in order],
        textposition="outside", hovertemplate="<b>%{x}</b><br>%{y:.2f} days<extra></extra>",
    ), row=1, col=2)

    _layout(fig, "", height=400, showlegend=False)
    fig.update_annotations(font=dict(size=13, color=INK))
    fig.update_yaxes(title_text="Touches", row=1, col=1)
    fig.update_yaxes(title_text="Days", row=1, col=2)
    return fig


# ----------------------------------------------------------------------------
# 6. Touch position distribution
# ----------------------------------------------------------------------------

def chart_position(position_dist: pd.DataFrame) -> go.Figure:
    if position_dist.empty:
        return _empty("No mid-funnel touches recorded.")

    fig = go.Figure()
    for position in position_dist.columns:
        fig.add_trace(go.Bar(
            name=position, x=list(position_dist.index), y=position_dist[position],
            marker_color=POSITION_COLORS.get(position, "#B0B0B0"),
            hovertemplate=f"<b>%{{x}}</b><br>{position}: %{{y:.1%}}<extra></extra>",
        ))
    _layout(fig, "Touch Position Distribution by Mid-Funnel Platform", height=420,
            barmode="stack",
            legend=dict(title="Position in path", orientation="h", yanchor="bottom",
                        y=1.0, xanchor="right", x=1))
    fig.update_yaxes(title_text="Share of touches", tickformat=".0%")
    return fig


# ----------------------------------------------------------------------------
# 7. First touch to converting touch flow
# ----------------------------------------------------------------------------

def chart_sankey(paths: pd.DataFrame, taxonomy: Taxonomy, min_flow: int = 3) -> go.Figure:
    multi = paths[paths["n_touches"] > 1]
    if multi.empty:
        return _empty("No multi-touch conversions to plot.")

    flows = multi.groupby(["first_touch_platform", "last_touch_platform"]).size().reset_index(name="n")
    flows = flows[flows["n"] >= min_flow]
    if flows.empty:
        return _empty(f"No first-to-last platform flow reaches {min_flow} conversions.")

    first_labels = sorted(flows["first_touch_platform"].unique())
    last_labels = sorted(flows["last_touch_platform"].unique())
    nodes = [f"{p} (first)" for p in first_labels] + [f"{p} (last)" for p in last_labels]
    index_of = {node: index for index, node in enumerate(nodes)}
    colors = taxonomy.platform_colors

    fig = go.Figure(go.Sankey(
        node=dict(
            label=nodes, pad=15, thickness=18,
            color=[colors.get(p, "#999") for p in first_labels]
            + [colors.get(p, "#999") for p in last_labels],
            line=dict(color="white", width=0.5),
        ),
        link=dict(
            source=[index_of[f"{row.first_touch_platform} (first)"] for row in flows.itertuples()],
            target=[index_of[f"{row.last_touch_platform} (last)"] for row in flows.itertuples()],
            value=[row.n for row in flows.itertuples()],
            color="rgba(120,124,150,0.25)",
        ),
    ))
    _layout(fig, "First Touch Platform to Last (Converting) Touch Platform", height=520)
    return fig


# ----------------------------------------------------------------------------
# 8. Mid-funnel to search lag
# ----------------------------------------------------------------------------

def chart_lag_histogram(lag_days: pd.Series) -> go.Figure:
    if lag_days is None or not len(lag_days):
        return _empty("No mid-funnel-assisted search conversions to plot.")

    median = float(np.median(lag_days))
    fig = go.Figure(go.Histogram(
        x=lag_days, nbinsx=15, marker=dict(color="#DD8452", line=dict(color="white", width=1)),
        hovertemplate="%{x} days<br>%{y} conversions<extra></extra>",
    ))
    fig.add_vline(
        x=median, line=dict(color="black", dash="dash", width=1.5),
        annotation_text=f"Median = {median:.1f} days", annotation_position="top right",
        annotation_font=dict(size=11, color=INK),
    )
    _layout(
        fig,
        "Days Between First Mid-Funnel Touch and Converting Search Click",
        height=400, showlegend=False,
    )
    fig.update_xaxes(title_text="Days")
    fig.update_yaxes(title_text="Conversions")
    return fig


# ----------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------

def build_figures(result) -> tuple[dict[str, go.Figure], list[dict], pd.DataFrame]:
    """All eight report figures, plus the two datasets the narrative quotes."""
    m = result.metrics
    taxonomy = result.taxonomy

    top_paths_fig, top_paths_rows = chart_top_paths(result.paths, taxonomy)
    heatmap_fig, transition_matrix = chart_transition_heatmap(result.touches, taxonomy)

    figures = {
        "daily_mf": chart_daily_mid_funnel(result.touches_full, taxonomy),
        "path_type": chart_path_type(result.paths),
        "top_paths": top_paths_fig,
        "heatmap": heatmap_fig,
        "length_time": chart_length_time(m.by_type),
        "position": chart_position(m.position_dist),
        "sankey": chart_sankey(result.paths, taxonomy),
        "lag": chart_lag_histogram(result.lag_days),
    }
    return figures, top_paths_rows, transition_matrix
