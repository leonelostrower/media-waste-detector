"""Deterministic narrative for the path-to-conversion report.

Builds the report's prose straight from the computed metrics, so every figure
quoted in the text is guaranteed to match the charts. The result is a list of
sections made of ordered blocks; an agent may rewrite the prose blocks later,
but only using numbers that already appear here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from ptc_pipeline import PATH_TYPE_ORDER, Metrics

NUMBER_PATTERN = re.compile(r"\d[\d,]*(?:\.\d+)?%?")


# ----------------------------------------------------------------------------
# Blocks
# ----------------------------------------------------------------------------

@dataclass
class Prose:
    """Markdown paragraphs and bullets. The only agent-editable block type."""

    text: str

    kind: str = "prose"


@dataclass
class TableBlock:
    headers: list[str]
    rows: list[list[str]]
    caption: str = ""

    kind: str = "table"


@dataclass
class FigureBlock:
    key: str
    caption: str = ""

    kind: str = "figure"


Block = Prose | TableBlock | FigureBlock


@dataclass
class NarrativeSection:
    id: str
    heading: str
    blocks: list[Block] = field(default_factory=list)

    def prose_indexes(self) -> list[int]:
        return [i for i, block in enumerate(self.blocks) if isinstance(block, Prose)]


# ----------------------------------------------------------------------------
# Formatting helpers
# ----------------------------------------------------------------------------

def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NaT


def pct(value: Any, digits: int = 1) -> str:
    if _missing(value):
        return "n/a"
    return f"{value * 100:.{digits}f}%"


def num(value: Any) -> str:
    if _missing(value):
        return "n/a"
    return f"{int(round(float(value))):,}"


def dec(value: Any, digits: int = 1) -> str:
    if _missing(value):
        return "n/a"
    return f"{float(value):.{digits}f}"


def day(value: Any, fmt: str = "%b %d, %Y") -> str:
    if _missing(value):
        return "n/a"
    return pd.Timestamp(value).strftime(fmt)


def join_list(items: Any) -> str:
    """'a', 'a and b', 'a, b and c'."""
    items = [str(item) for item in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _normalize(raw: list[Block]) -> list[Block]:
    """Merge adjacent prose so each section exposes a small number of editable
    blocks while keeping tables and figures anchored where they belong."""
    merged: list[Block] = []
    for block in raw:
        if isinstance(block, Prose) and merged and isinstance(merged[-1], Prose):
            merged[-1] = Prose(text=f"{merged[-1].text}\n\n{block.text}".strip())
            continue
        merged.append(block)
    return [b for b in merged if not (isinstance(b, Prose) and not b.text.strip())]


# ----------------------------------------------------------------------------
# Bullet builders (ported from the report script)
# ----------------------------------------------------------------------------

def summary_bullets(m: Metrics) -> list[str]:
    ranked = m.platform_volume.sort_values("conversions_influenced", ascending=False)
    reach = [
        f"{platform} ({num(row.conversions_influenced)}, "
        f"{pct(row.pct_of_all_conversions)} of conversions)"
        for platform, row in ranked.iterrows()
    ]

    bullets = [
        f"**Mid-funnel touch**: {pct(m.pct_mf_touched)} of conversions in this window "
        f"({num(m.n_mf_touched)} of {num(m.n_conversions)}) were touched by a mid-funnel platform "
        f"at least once; the remaining {pct(m.pct_untouched)} were Search-only. Of the touched "
        f"paths, {pct(m.pct_mf_impr_only, 0)} ({num(m.n_mf_impr_only)}) were view-through only "
        f"(impression, no click), showing mid-funnel is mostly assisting the journey rather than "
        f"being clicked directly.",

        f"**Path mix**: {pct(m.pct_search_only)} of conversions are Search-only, "
        f"{pct(m.pct_mixed)} are Mixed (touched by both Search and mid-funnel), and "
        f"{pct(m.pct_mf_only)} are Mid-funnel-only (view-through, no search touch at all).",
    ]

    if m.n_mixed_paths:
        bullets.append(
            f"The hypothesis is partially supported: {pct(m.pct_classic)} of Mixed paths "
            f"({num(m.n_classic)} of {num(m.n_mixed_paths)}) follow the classic pattern of "
            f"mid-funnel first touch converting via Search. Among these, the median time between "
            f"the first mid-funnel exposure and the converting Search click is "
            f"{dec(m.lag_median)} days, with {pct(m.pct_multi_day)} taking a day or more."
        )

    if {"Mixed", "Search-only"} <= set(m.by_type.index):
        bullets.append(
            f"Mixed paths take meaningfully longer to convert (avg. "
            f"{dec(m.by_type.loc['Mixed', 'avg_days_to_convert'])} days, "
            f"{dec(m.by_type.loc['Mixed', 'avg_path_length'])} touches) than Search-only paths "
            f"(avg. {dec(m.by_type.loc['Search-only', 'avg_days_to_convert'])} days, "
            f"{dec(m.by_type.loc['Search-only', 'avg_path_length'])} touches), consistent with "
            f"mid-funnel nurturing demand rather than capturing existing intent."
        )

    if reach:
        bullets.append(
            f"**Platform reach**: {reach[0]} leads among mid-funnel platforms"
            + (f", ahead of {join_list(reach[1:])}." if len(reach) > 1 else ".")
        )

    bullets.append(
        f"**Attribution coverage**: the export contains {num(m.n_export_conversions)} conversions "
        f"for this activity, of which {num(m.n_conversions)} ({pct(m.pct_attributed)}) carry at "
        f"least one CM360 interaction. The {num(m.n_unattributed)} unattributed conversions "
        f"(path length 0) have no touch data and are excluded from every path metric in this report."
    )
    return bullets


def transition_bullets(matrix: pd.DataFrame, m: Metrics) -> list[str]:
    if matrix.empty:
        return []

    present = [p for p in matrix.index if matrix.loc[p].sum() > 0]
    self_loop = {p: matrix.loc[p, p] for p in present}
    search = [p for p in present if p in m.search_platforms]
    mid = [p for p in present if p in m.mid_funnel_platforms]

    out: list[str] = []
    if search:
        parts = ", ".join(f"{p} ({pct(self_loop[p], 0)})" for p in search)
        out.append(
            f"**Search persistence**: {parts} show high continuity, users return to the same "
            f"search engine for their next touch."
        )
    if mid:
        stayers = sorted(mid, key=lambda p: self_loop[p], reverse=True)
        parts = ", ".join(f"{p} ({pct(self_loop[p], 0)} stay)" for p in stayers)
        out.append(
            f"**Social platform loyalty**: {parts}. Platforms with lower self-transition rates are "
            f"handing users off rather than holding them."
        )
        lowest = stayers[-1]
        row = matrix.loc[lowest].drop(lowest)
        if len(row):
            destination = row.idxmax()
            if row[destination] > 0:
                out.append(
                    f"**{lowest} as an awareness play**: only {pct(self_loop[lowest], 0)} of "
                    f"{lowest} interactions lead to another {lowest} touch; "
                    f"{pct(row[destination], 0)} transition to {destination}, suggesting it "
                    f"functions as an upper-funnel driver rather than a closer."
                )
    return out


def conclusion_bullets(m: Metrics) -> list[str]:
    bullets = [
        f"**Analysis window**: this report covers conversions from {day(m.date_min)} to "
        f"{day(m.date_max)}, the period in which the mid-funnel platforms were live and tagged. "
        f"Pre-activation weeks are excluded so the numbers are not diluted by weeks in which "
        f"mid-funnel could not appear."
    ]

    partial, low_volume = [], []
    for platform in m.mid_funnel_platforms:
        if platform not in m.live_windows.index:
            continue
        window = m.live_windows.loc[platform]
        late = (window["first_touch"] - m.date_min).days > 3
        early_stop = (m.date_max - window["last_touch"]).days > 7
        if late or early_stop:
            partial.append(
                f"{platform} ran {day(window['first_touch'], '%b %d')} to "
                f"{day(window['last_touch'], '%b %d')}"
            )
        if platform in m.platform_volume.index and \
                m.platform_volume.loc[platform, "pct_of_all_conversions"] < 0.01:
            low_volume.append(
                f"{platform} ({num(m.platform_volume.loc[platform, 'conversions_influenced'])} "
                f"conversions influenced)"
            )

    if partial:
        plural = len(partial) > 1
        bullets.append(
            f"**Partial-window platform{'s' if plural else ''}**: {'; '.join(partial)}, so "
            f"{'these platforms were' if plural else 'it was'} not live for the full window. "
            f"{'Their' if plural else 'Its'} metrics are directional and should not be compared "
            f"like-for-like with always-on platforms."
        )
    if low_volume:
        plural = len(low_volume) > 1
        bullets.append(
            f"**Low-volume platform{'s' if plural else ''}**: {join_list(low_volume)} influenced "
            f"under 1% of conversions{' each' if plural else ''}. Any conclusion drawn on "
            f"{'them' if plural else 'it'} is directional, not statistically solid."
        )

    if m.n_truncated_paths:
        bullets.append(
            f"**Truncated paths**: the export records at most {num(m.n_interaction_slots)} "
            f"interactions per conversion, but {num(m.n_truncated_paths)} conversions "
            f"({pct(m.pct_truncated)}) report a longer true path length, up to "
            f"{num(m.max_path_length)} touches. Their earliest touches are missing from the "
            f"sequence, so first-touch and path-shape metrics slightly understate how often "
            f"mid-funnel opens a long journey."
        )

    bullets.append(
        f"The Mixed-path sample is small (n={num(m.n_mixed_paths)}, {pct(m.pct_mixed)} of "
        f"conversions in the window), so point estimates on this subset (for example the "
        f"classic-hypothesis rate) carry wide uncertainty and should be revisited as more data "
        f"accumulates."
    )
    bullets.append(
        "This is a path-to-conversion / last-touch-adjacent export, not a full multi-touch "
        "attribution model, so all percentages here are directional evidence for the mid-funnel "
        "hypothesis rather than a formal attribution result."
    )
    bullets.append(
        "**Recommendation**: re-run this report on the next refresh once every mid-funnel platform "
        "has a full month of in-window data, to tighten these estimates and confirm the trend "
        "direction."
    )
    return bullets


# ----------------------------------------------------------------------------
# Sections
# ----------------------------------------------------------------------------

def _summary(m: Metrics) -> NarrativeSection:
    live_mid = [p for p in m.mid_funnel_platforms if p in m.live_windows.index]
    blocks: list[Block] = [
        Prose(
            f"This report analyzes CM360 path-to-conversion data to test whether mid-funnel "
            f"awareness channels ({join_list(live_mid) or 'none recorded'}) build interest that "
            f"later converts through Search. It covers conversions from {day(m.date_min)} to "
            f"{day(m.date_max)}, the period in which mid-funnel was live and tagged, so the "
            f"numbers reflect mid-funnel's true impact rather than an activation ramp-up."
        ),
        Prose(_bullets(summary_bullets(m))),
    ]
    return NarrativeSection("summary", "Summary", _normalize(blocks))


def _methodology(m: Metrics) -> NarrativeSection:
    blocks: list[Block] = [
        Prose(
            f'Source: CM360 Path-to-Conversion export for the floodlight activity '
            f'"{m.activity_name}", covering activity from {day(m.date_min, "%Y-%m-%d")} to '
            f'{day(m.date_max, "%Y-%m-%d")}. Each conversion\'s full touch sequence (up to '
            f'{num(m.n_interaction_slots)} recorded interactions) was reshaped into a touch-level '
            f'table and classified using the following taxonomy, derived from the campaigns and '
            f'sites actually present in the export:'
        ),
        TableBlock(
            headers=["Campaign", "Site (CM360)", "Channel", "Platform"],
            rows=m.taxonomy_table.astype(str).values.tolist(),
            caption="Taxonomy applied to this export.",
        ),
        Prose(
            f"Attribution coverage: {num(m.n_export_conversions)} conversions were returned for "
            f"this activity. {num(m.n_conversions)} ({pct(m.pct_attributed)}) carry at least one "
            f"CM360 interaction and form the basis of every path metric below; the remaining "
            f"{num(m.n_unattributed)} have a path length of 0, meaning no click or impression was "
            f"matched to them, and are excluded rather than counted as Search-only."
        ),
    ]

    if m.has_rampup:
        blocks.append(Prose(
            f"The raw export covers {day(m.ctx_full_date_min, '%b %d')} to "
            f"{day(m.ctx_full_date_max)} ({num(m.ctx_full_n)} attributed conversions), but the "
            f"mid-funnel platforms were not live for the first part of that range. The first "
            f"mid-funnel interaction recorded anywhere in the data is {day(m.first_mf_date)}; "
            f"everything before that is Search-only by construction, not by consumer behaviour. "
            f"Including those weeks does not measure how often mid-funnel is involved, it measures "
            f"how long the platforms took to turn on, and mechanically drags every mid-funnel "
            f"metric toward zero.\n\n"
            f"The data makes the distortion concrete. Measuring the full export against the "
            f"post-activation window (from {day(m.steady_state_start)}, once mid-funnel was live):"
        ))
        blocks.append(TableBlock(
            headers=["Metric", "Full export", f"This report (from {day(m.steady_state_start, '%b %d')})"],
            rows=[
                ["Attributed conversions", num(m.ctx_full_n), num(m.n_conversions)],
                ["% touched by any mid-funnel", pct(m.ctx_full_pct_touched), pct(m.pct_mf_touched)],
                ["% Mixed (Search + Mid-funnel)", pct(m.ctx_full_pct_mixed), pct(m.pct_mixed)],
            ],
            caption="Full export versus the post-activation window.",
        ))
        blocks.append(Prose(
            f"Scoping to the post-activation window lifts the mid-funnel touch rate from "
            f"{pct(m.ctx_full_pct_touched)} to {pct(m.pct_mf_touched)} because it stops averaging "
            f"in weeks where mid-funnel could not appear. All findings that follow use only this "
            f"post-activation window."
        ))
    else:
        blocks.append(Prose(
            f"Window: the export was pulled from {day(m.date_min)} onward, which is already the "
            f"post-activation window, so no ramp-up weeks need to be trimmed and no mid-funnel "
            f"metric is diluted by weeks in which the platforms were not yet live. Individual "
            f"platforms did, however, start and stop at different points, which is what the touch "
            f"windows below show. Touch dates can precede the conversion window, since an exposure "
            f"that led to an in-window conversion may have happened earlier:"
        ))
        blocks.append(TableBlock(
            headers=["Platform", "First recorded touch", "Last recorded touch", "Touches"],
            rows=[
                [platform, day(row["first_touch"]), day(row["last_touch"]), num(row["touches"])]
                for platform, row in m.live_windows.iterrows()
            ],
            caption="Recorded touch window per platform.",
        ))
        blocks.append(Prose(
            "Platforms that joined or stopped mid-window carry fewer exposure days than the "
            "always-on Search campaigns, so their share of conversions understates their "
            "steady-state contribution. The timeseries below shows daily touch volume per "
            "platform, making each platform's live period and relative intensity visible."
        ))

    if m.n_truncated_paths:
        blocks.append(Prose(
            f"One export limit is worth noting: CM360 records at most "
            f"{num(m.n_interaction_slots)} interactions per conversion, while the reported path "
            f"length runs as high as {num(m.max_path_length)}. "
            f"{num(m.n_truncated_paths)} conversions ({pct(m.pct_truncated)}) therefore have their "
            f"earliest touches cut from the sequence. Average path length is still correct, since "
            f"it uses the reported path length, but the touch-level sequence for those "
            f"conversions starts later than the journey actually did."
        ))

    blocks.append(FigureBlock("daily_mf", "Figure 1. Mid-funnel platforms timeseries."))
    return NarrativeSection("methodology", "Methodology & Data Notes", _normalize(blocks))


def _path_mix(m: Metrics) -> NarrativeSection:
    blocks: list[Block] = [
        Prose(
            f"Out of {num(m.n_conversions)} attributed conversions, the large majority "
            f"({pct(m.pct_search_only)}) never touch a mid-funnel platform at all. "
            f"{pct(m.pct_mf_only)} convert on a mid-funnel view-through impression with no Search "
            f"touch in the path, and {pct(m.pct_mixed)} ({num(m.n_mixed)} conversions) show both "
            f"channels in the same path."
        ),
        FigureBlock("path_type", "Figure 2. Conversions by path type (campaign level)."),
        Prose(
            f"Within these {num(m.n_mixed_paths)} Mixed conversions, {num(m.n_classic)} "
            f"({pct(m.pct_classic)}) follow the exact hypothesis pattern, mid-funnel touches first "
            f"and Search converts last. This confirms the pattern exists and is not negligible, "
            f"but it is not yet the dominant journey shape among Mixed paths; the reverse order "
            f"(Search touching first, mid-funnel later) also occurs."
        ),
    ]
    return NarrativeSection("path_mix", "Mid-Funnel vs. Search Path Mix", _normalize(blocks))


def _top_paths(m: Metrics, rows: list[dict]) -> NarrativeSection:
    top_share = sum(row["pct"] for row in rows)
    blocks: list[Block] = [
        Prose(
            f"Collapsing each conversion's touch sequence into its ordered distinct-consecutive "
            f"platform steps (so repeated touches on the same platform read as one step) and "
            f"ranking the most common journeys gives a DV360-style top converting paths view. "
            f"Position 1 is the converting (last) touch. The {num(len(rows))} journeys below "
            f"account for {pct(top_share)} of all {num(m.n_conversions)} conversions in this window."
        ),
        FigureBlock(
            "top_paths",
            "Figure 3. Top converting paths, grouped by platform (position 1 = converting touch).",
        ),
        TableBlock(
            headers=["Rank", "Converting path (first to last)", "Conversions", "% of conversions"],
            rows=[
                [str(index + 1), row["journey"], num(row["conversions"]), pct(row["pct"])]
                for index, row in enumerate(rows)
            ],
            caption="Most frequent converting journeys.",
        ),
        Prose(
            "Read in practice: the top paths are dominated by single-platform Search journeys, "
            "confirming most conversions never involve a mid-funnel touch. The multi-platform "
            "journeys that do appear are exactly the mid-funnel-assisted paths quantified in the "
            "path mix and funnel velocity sections, real but a small share of total volume in the "
            "current window."
        ),
    ]
    return NarrativeSection("top_paths", "Top Converting Paths by Platform", _normalize(blocks))


def _transitions(m: Metrics, matrix: pd.DataFrame) -> NarrativeSection:
    blocks: list[Block] = [
        Prose(
            "The heatmap below shows, for every consecutive touch pair in a conversion path, the "
            "probability of each next-touch platform (row %). Rows represent the current platform "
            "and columns where the user touches next. The diagonal reflects platform loyalty, how "
            "often a touch on a given platform is immediately followed by another touch on the "
            "same platform, while off-diagonal cells reveal cross-platform migration."
        ),
        Prose(_bullets(transition_bullets(matrix, m))),
        FigureBlock(
            "heatmap",
            "Figure 4. Platform-to-platform transition probabilities (row % of next-touch platform).",
        ),
    ]
    return NarrativeSection("transitions", "Platform Transition Flow", _normalize(blocks))


def _velocity(m: Metrics) -> NarrativeSection:
    ratio = (
        m.touched_apl / m.untouched_apl
        if m.untouched_apl and not pd.isna(m.untouched_apl) else float("nan")
    )
    gap = m.touched_days - m.untouched_days
    blocks: list[Block] = [
        Prose(
            "If mid-funnel is genuinely building interest earlier in the journey rather than "
            "acting as a same-session assist, Mixed paths should show longer paths and longer "
            "time-to-convert than Search-only paths. The data supports this:"
        ),
        TableBlock(
            headers=["Path type", "Conversions", "Avg. path length (touches)", "Avg. days to convert"],
            rows=[
                [
                    path_type,
                    num(m.by_type.loc[path_type, "conversions"]),
                    dec(m.by_type.loc[path_type, "avg_path_length"], 2),
                    dec(m.by_type.loc[path_type, "avg_days_to_convert"], 2),
                ]
                for path_type in PATH_TYPE_ORDER if path_type in m.by_type.index
            ],
            caption="Path length and time to convert by path type.",
        ),
        Prose(
            f"Collapsing this to a two-way comparison makes the gap clear: conversions touched by "
            f"mid-funnel at any point average {dec(m.touched_apl)} touches and "
            f"{dec(m.touched_days)} days from first touch to conversion, versus "
            f"{dec(m.untouched_apl)} touches and {dec(m.untouched_days)} days for Search-only "
            f"conversions. A mid-funnel touch is therefore associated with a path roughly "
            f"{dec(ratio)}x longer that takes about {dec(gap)} more days to close, the signature "
            f"of a longer, more considered journey rather than same-session intent capture."
        ),
        FigureBlock(
            "length_time", "Figure 5. Average path length and days-to-convert by path type."
        ),
    ]
    return NarrativeSection("velocity", "Mixed Paths Take Longer to Convert", _normalize(blocks))


def _platforms(m: Metrics) -> NarrativeSection:
    ranked = m.platform_volume.sort_values("conversions_influenced", ascending=False)
    if len(ranked):
        lead = (
            f"At the site level, {ranked.index[0]} has the largest footprint among mid-funnel "
            f"platforms"
            + (f", followed by {join_list(ranked.index[1:])}." if len(ranked) > 1 else ".")
            + " Touch counts include both clicks and view-through impressions."
        )
    else:
        lead = "No mid-funnel touches were recorded in this window."
    blocks: list[Block] = [
        Prose(lead),
        TableBlock(
            headers=["Platform", "Touches", "Conversions influenced", "% of all conversions"],
            rows=[
                [
                    platform,
                    num(row["touches"]),
                    num(row["conversions_influenced"]),
                    pct(row["pct_of_all_conversions"]),
                ]
                for platform, row in ranked.iterrows()
            ],
            caption="Mid-funnel footprint by platform.",
        ),
        Prose(
            "Looking at where each platform's touch tends to land within the path (first / middle "
            "/ last / only touch) shows whether a platform behaves more like top-of-funnel "
            "awareness or late-stage retargeting:"
        ),
        FigureBlock("position", "Figure 6. Touch position distribution by mid-funnel platform."),
    ]
    return NarrativeSection("platforms", "Platform Breakdown & Path Position", _normalize(blocks))


def _flow(m: Metrics) -> NarrativeSection:
    blocks: list[Block] = [
        Prose(
            "For multi-touch conversions, tracing the flow from the first touch platform to the "
            "last (converting) touch platform gives a quick visual read on whether mid-funnel "
            "platforms feed into Search by the end of the journey, or whether paths tend to stay "
            "within one platform."
        ),
        FigureBlock(
            "sankey",
            "Figure 7. First-touch platform to last-touch platform flow (multi-touch conversions).",
        ),
    ]
    return NarrativeSection("flow", "Path Flow: First Touch to Converting Touch", _normalize(blocks))


def _funnel_velocity(m: Metrics) -> NarrativeSection:
    blocks: list[Block] = [
        Prose(
            f"For the {num(m.n_classic)} mid-funnel-assisted Search conversions, the median time "
            f"between the first mid-funnel touch and the eventual converting Search click is "
            f"{dec(m.lag_median)} days (mean {dec(m.lag_mean)} days). {pct(m.pct_multi_day)} of "
            f"these conversions take a day or more to close after the initial mid-funnel exposure, "
            f"the clearest quantitative evidence that mid-funnel is acting as an earlier-funnel "
            f"nurture touch rather than a same-session assist."
        ),
        FigureBlock(
            "lag", "Figure 8. Days between first mid-funnel touch and converting Search click."
        ),
    ]
    return NarrativeSection(
        "funnel_velocity",
        "Funnel Velocity: Mid-Funnel Builds Interest, Search Converts Later",
        _normalize(blocks),
    )


def _conclusions(m: Metrics) -> NarrativeSection:
    return NarrativeSection(
        "conclusions",
        "Conclusions & Recommendations",
        _normalize([Prose(_bullets(conclusion_bullets(m)))]),
    )


def build_sections(
    m: Metrics,
    top_paths_rows: list[dict],
    transition_matrix: pd.DataFrame,
) -> list[NarrativeSection]:
    """The full report narrative, in reading order."""
    return [
        _summary(m),
        _methodology(m),
        _path_mix(m),
        _top_paths(m, top_paths_rows),
        _transitions(m, transition_matrix),
        _velocity(m),
        _platforms(m),
        _flow(m),
        _funnel_velocity(m),
        _conclusions(m),
    ]


# ----------------------------------------------------------------------------
# Fact sheet and number guard
# ----------------------------------------------------------------------------

def build_fact_sheet(m: Metrics) -> dict[str, str]:
    """Every metric the narrative may quote, pre-formatted. This is the ground
    truth handed to the rewriting agent; it may not invent values outside it."""
    sheet: dict[str, str] = {
        "analysis_window": f"{day(m.date_min)} to {day(m.date_max)}",
        "activity_name": str(m.activity_name),
        "conversions_in_export": num(m.n_export_conversions),
        "attributed_conversions": num(m.n_conversions),
        "unattributed_conversions": num(m.n_unattributed),
        "pct_attributed": pct(m.pct_attributed),
        "interaction_slots": num(m.n_interaction_slots),
        "max_path_length": num(m.max_path_length),
        "truncated_paths": num(m.n_truncated_paths),
        "pct_truncated": pct(m.pct_truncated),
        "search_only_conversions": num(m.n_search_only),
        "pct_search_only": pct(m.pct_search_only),
        "mixed_conversions": num(m.n_mixed),
        "pct_mixed": pct(m.pct_mixed),
        "mid_funnel_only_conversions": num(m.n_mf_only),
        "pct_mid_funnel_only": pct(m.pct_mf_only),
        "mid_funnel_touched_conversions": num(m.n_mf_touched),
        "pct_mid_funnel_touched": pct(m.pct_mf_touched),
        "pct_never_touched": pct(m.pct_untouched),
        "view_through_only_conversions": num(m.n_mf_impr_only),
        "pct_view_through_only": pct(m.pct_mf_impr_only, 0),
        "classic_pattern_conversions": num(m.n_classic),
        "pct_classic_pattern": pct(m.pct_classic),
        "median_lag_days": dec(m.lag_median),
        "mean_lag_days": dec(m.lag_mean),
        "pct_lag_over_one_day": pct(m.pct_multi_day),
        "avg_touches_mid_funnel_touched": dec(m.touched_apl),
        "avg_days_mid_funnel_touched": dec(m.touched_days),
        "avg_touches_search_only": dec(m.untouched_apl),
        "avg_days_search_only": dec(m.untouched_days),
        "mid_funnel_platforms": join_list(m.mid_funnel_platforms) or "none",
        "search_platforms": join_list(m.search_platforms) or "none",
    }

    for path_type in PATH_TYPE_ORDER:
        if path_type not in m.by_type.index:
            continue
        key = path_type.lower().replace("-", "_").replace(" ", "_")
        sheet[f"{key}_conversions"] = num(m.by_type.loc[path_type, "conversions"])
        sheet[f"{key}_avg_path_length"] = dec(m.by_type.loc[path_type, "avg_path_length"], 2)
        sheet[f"{key}_avg_days"] = dec(m.by_type.loc[path_type, "avg_days_to_convert"], 2)

    for platform, row in m.platform_volume.iterrows():
        key = str(platform).lower().replace(" ", "_")
        sheet[f"{key}_touches"] = num(row["touches"])
        sheet[f"{key}_conversions_influenced"] = num(row["conversions_influenced"])
        sheet[f"{key}_pct_of_conversions"] = pct(row["pct_of_all_conversions"])

    for platform, row in m.live_windows.iterrows():
        key = str(platform).lower().replace(" ", "_")
        sheet[f"{key}_live_window"] = f"{day(row['first_touch'])} to {day(row['last_touch'])}"

    if m.has_rampup:
        sheet["full_export_attributed"] = num(m.ctx_full_n)
        sheet["full_export_pct_touched"] = pct(m.ctx_full_pct_touched)
        sheet["full_export_pct_mixed"] = pct(m.ctx_full_pct_mixed)
        sheet["full_export_window"] = f"{day(m.ctx_full_date_min)} to {day(m.ctx_full_date_max)}"
        sheet["first_mid_funnel_touch"] = day(m.first_mf_date)
        sheet["steady_state_start"] = day(m.steady_state_start)

    return sheet


def numbers_in(text: str) -> set[str]:
    """Numeric tokens, normalized so 12.0% and 12% do not read as different."""
    tokens = set()
    for raw in NUMBER_PATTERN.findall(text or ""):
        token = raw.replace(",", "")
        suffix = "%" if token.endswith("%") else ""
        body = token.rstrip("%")
        if "." in body:
            body = body.rstrip("0").rstrip(".")
        tokens.add(f"{body}{suffix}")
    return tokens


def allowed_numbers(sections: list[NarrativeSection], fact_sheet: dict[str, str]) -> set[str]:
    """Every number the agent is permitted to use: those in the deterministic
    draft plus those in the fact sheet."""
    allowed: set[str] = set()
    for section in sections:
        for block in section.blocks:
            if isinstance(block, Prose):
                allowed |= numbers_in(block.text)
            elif isinstance(block, TableBlock):
                for row in block.rows:
                    for cell in row:
                        allowed |= numbers_in(str(cell))
    for value in fact_sheet.values():
        allowed |= numbers_in(str(value))
    return allowed


def unsupported_numbers(text: str, allowed: set[str]) -> list[str]:
    return sorted(numbers_in(text) - allowed)


def section_to_markdown(section: NarrativeSection) -> str:
    parts = [f"## {section.heading}"]
    for block in section.blocks:
        if isinstance(block, Prose):
            parts.append(block.text)
        elif isinstance(block, TableBlock):
            parts.append(f"[table: {block.caption or ', '.join(block.headers)}]")
        elif isinstance(block, FigureBlock):
            parts.append(f"[figure: {block.caption or block.key}]")
    return "\n\n".join(parts)
