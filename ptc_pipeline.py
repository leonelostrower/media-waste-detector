"""CM360 path-to-conversion data pipeline.

Reshapes a raw CM360 path-to-conversion export into touch-level, path-level and
metric-level tables. Every number is computed from the upload, never hardcoded,
so a refreshed export can be re-run with no code changes.
"""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

SEARCH = "Search"
MID_FUNNEL = "Mid-funnel"
OTHER = "Other"

PATH_TYPE_ORDER = ["Search-only", "Mixed", "Mid-funnel-only"]

PATH_TYPE_COLORS = {
    "Search-only": "#4C72B0",
    "Mixed": "#DD8452",
    "Mid-funnel-only": "#55A868",
}

# Recognisable platforms get their brand colour; anything else is assigned from
# the fallback cycle so a newly launched platform still renders distinctly.
KNOWN_PLATFORM_COLORS = {
    "Google Search": "#4285F4",
    "MSN Search": "#00A4EF",
    "Facebook": "#1877F2",
    "Instagram": "#E4405F",
    "Reddit": "#FF4500",
    "StackAdapt": "#00C4A7",
    "TikTok": "#EE1D52",
    "Pinterest": "#BD081C",
    "YouTube": "#FF0000",
    "LinkedIn": "#0A66C2",
    "Snapchat": "#FFFC00",
    "Amazon": "#FF9900",
}

FALLBACK_COLORS = [
    "#7B61FF", "#00897B", "#C2185B", "#F9A825",
    "#5D4037", "#455A64", "#8E24AA", "#43A047",
]

NULL_TOKENS = {"---", "", "nan", "None"}


# ----------------------------------------------------------------------------
# Taxonomy
# ----------------------------------------------------------------------------

@dataclass
class Taxonomy:
    """Campaign -> channel and site -> platform mapping for one export.

    Replaces the module-level CHANNEL_MAP / PLATFORM_MAP globals so several
    clients can be analysed in the same process without cross-contamination.
    """

    channel_map: dict[str, str] = field(default_factory=dict)
    platform_map: dict[str, str] = field(default_factory=dict)
    platform_channel: dict[str, str] = field(default_factory=dict)

    def channel_for(self, campaign: Any) -> str:
        return self.channel_map.get(campaign, OTHER)

    def platform_for(self, site: Any) -> str:
        return self.platform_map.get(site, OTHER)

    @property
    def platforms(self) -> list[str]:
        seen: list[str] = []
        for platform in self.platform_map.values():
            if platform not in seen:
                seen.append(platform)
        return seen

    @property
    def search_platforms(self) -> list[str]:
        return [p for p in self.platforms if self.platform_channel.get(p) == SEARCH]

    @property
    def mid_funnel_platforms(self) -> list[str]:
        return [p for p in self.platforms if self.platform_channel.get(p) == MID_FUNNEL]

    @property
    def platform_colors(self) -> dict[str, str]:
        colors: dict[str, str] = {}
        spare = iter(FALLBACK_COLORS * 4)
        for platform in self.platforms:
            colors[platform] = KNOWN_PLATFORM_COLORS.get(platform) or next(spare, "#999999")
        colors.setdefault(OTHER, "#B0B0B0")
        return colors

    def signature(self) -> str:
        """Stable key for cache invalidation when the mapping is edited."""
        payload = repr((
            sorted(self.channel_map.items()),
            sorted(self.platform_map.items()),
            sorted(self.platform_channel.items()),
        ))
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_map": dict(self.channel_map),
            "platform_map": dict(self.platform_map),
            "platform_channel": dict(self.platform_channel),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "Taxonomy | None":
        if not raw or not raw.get("platform_map"):
            return None
        return cls(
            channel_map=dict(raw.get("channel_map") or {}),
            platform_map=dict(raw.get("platform_map") or {}),
            platform_channel=dict(raw.get("platform_channel") or {}),
        )


def is_null_token(value: Any) -> bool:
    return value is None or str(value).strip() in NULL_TOKENS


# ----------------------------------------------------------------------------
# Export parsing
# ----------------------------------------------------------------------------

def read_preamble(raw: bytes) -> tuple[dict[str, str], int]:
    """CM360 exports prepend a metadata block ('Date Range', 'Activity', ...)
    before the real column header. Returns (preamble dict, header row index).
    Exports already cleaned in Sheets have no preamble, so the header is row 0."""
    meta: dict[str, str] = {}
    header_row = 0
    text = raw.decode("utf-8-sig", errors="replace")
    for index, line in enumerate(io.StringIO(text)):
        if line.startswith("Conversion ID,"):
            header_row = index
            break
        parts = [p.strip().strip('"') for p in line.rstrip("\n").split(",")]
        if len(parts) >= 2 and parts[0] and parts[1]:
            meta[parts[0]] = parts[1]
        if index > 60:  # header should appear early; avoid scanning a huge file
            break
    return meta, header_row


def load_data(raw: bytes, header_row: int, period_start: pd.Timestamp | None = None) -> pd.DataFrame:
    frame = pd.read_csv(io.BytesIO(raw), skiprows=header_row, low_memory=False)
    df = frame[frame["Conversion ID"] != "Grand Total:"].copy()
    df["Path Length"] = pd.to_numeric(df["Path Length"], errors="coerce").astype("Int64")
    df["Activity Date/Time"] = pd.to_datetime(df["Activity Date/Time"], errors="coerce")
    df = df.dropna(subset=["Activity Date/Time"])
    if period_start is not None:
        df = df[df["Activity Date/Time"] >= period_start].copy()
    return df


def n_interaction_slots(df: pd.DataFrame) -> int:
    """How many 'Interaction N: ...' column blocks the export actually carries."""
    found = [
        int(match.group(1))
        for column in df.columns
        if (match := re.match(r"Interaction (\d+): Campaign$", column))
    ]
    return max(found) if found else 0


def pair_counts(df: pd.DataFrame, slots: int) -> pd.DataFrame:
    """How often each campaign/site pair appears, across every interaction slot."""
    frames = []
    for index in range(1, slots + 1):
        columns = {
            f"Interaction {index}: Campaign": "campaign",
            f"Interaction {index}: Site (CM360)": "site",
        }
        frames.append(df[list(columns)].rename(columns=columns).dropna())
    if not frames:
        return pd.DataFrame(columns=["campaign", "site", "n"])
    pairs = pd.concat(frames, ignore_index=True)
    pairs = pairs[~pairs["site"].map(is_null_token) & ~pairs["campaign"].map(is_null_token)]
    return pairs.groupby(["campaign", "site"]).size().reset_index(name="n")


def reconcile_platform_channel(
    pairs: pd.DataFrame,
    channel_map: dict[str, str],
    platform_map: dict[str, str],
) -> dict[str, str]:
    """A platform's channel is the channel of the campaigns it actually runs
    under. Deriving it from the export keeps the two halves of the mapping
    consistent even if an agent or a user classifies them differently."""
    if pairs.empty:
        return {}
    scored = pairs.copy()
    scored["platform"] = scored["site"].map(lambda s: platform_map.get(s, OTHER))
    scored["channel"] = scored["campaign"].map(lambda c: channel_map.get(c, OTHER))
    totals = scored.groupby(["platform", "channel"])["n"].sum().reset_index()
    dominant = totals.sort_values("n", ascending=False).drop_duplicates("platform")
    return dict(zip(dominant["platform"], dominant["channel"]))


def distinct_values(df: pd.DataFrame, slots: int) -> tuple[list[str], list[str]]:
    """Campaigns and sites present anywhere in the export, for the taxonomy step."""
    campaigns: set[str] = set()
    sites: set[str] = set()
    for index in range(1, slots + 1):
        campaigns |= set(df[f"Interaction {index}: Campaign"].dropna().unique())
        sites |= set(df[f"Interaction {index}: Site (CM360)"].dropna().unique())
    return (
        sorted(str(c) for c in campaigns if not is_null_token(c)),
        sorted(str(s) for s in sites if not is_null_token(s)),
    )


# ----------------------------------------------------------------------------
# Reshaping
# ----------------------------------------------------------------------------

def build_touches(df: pd.DataFrame, taxonomy: Taxonomy, slots: int | None = None) -> pd.DataFrame:
    slots = slots if slots is not None else n_interaction_slots(df)
    blocks = []
    for index in range(1, slots + 1):
        columns = {
            "Conversion ID": "Conversion ID",
            f"Interaction {index}: Interaction Date/Time": "touch_time",
            f"Interaction {index}: Interaction Number": "interaction_number",
            f"Interaction {index}: Campaign": "campaign",
            f"Interaction {index}: Site (CM360)": "site",
            f"Interaction {index}: Interaction Type": "interaction_type",
        }
        blocks.append(df[list(columns)].rename(columns=columns).dropna(subset=["site"]))

    touches = pd.concat(blocks, ignore_index=True)
    touches = touches[~touches["site"].map(is_null_token)]
    touches["touch_time"] = pd.to_datetime(touches["touch_time"], errors="coerce")
    touches = touches.dropna(subset=["touch_time"])
    touches["channel"] = touches["campaign"].map(taxonomy.channel_for)
    touches["platform"] = touches["site"].map(taxonomy.platform_for)
    touches = touches.sort_values(["Conversion ID", "touch_time"]).reset_index(drop=True)
    touches["touch_order"] = touches.groupby("Conversion ID").cumcount() + 1
    return touches


def build_paths(touches: pd.DataFrame, activity: pd.DataFrame) -> pd.DataFrame:
    grouped = touches.groupby("Conversion ID", sort=False)

    first_touch = grouped.first()[["channel", "platform"]].rename(
        columns={"channel": "first_touch_channel", "platform": "first_touch_platform"})
    last_touch = grouped.last()[["channel", "platform"]].rename(
        columns={"channel": "last_touch_channel", "platform": "last_touch_platform"})
    first_time = grouped["touch_time"].first().rename("first_touch_time")

    paths = pd.concat([first_touch, last_touch, first_time], axis=1)
    paths["channel_sequence"] = grouped["channel"].apply(" > ".join)
    paths["platform_sequence"] = grouped["platform"].apply(" > ".join)
    paths["n_touches"] = grouped.size()
    paths["n_mid_funnel_touches"] = grouped["channel"].apply(lambda s: (s == MID_FUNNEL).sum())
    paths["n_search_touches"] = grouped["channel"].apply(lambda s: (s == SEARCH).sum())

    has_mid = paths["n_mid_funnel_touches"] > 0
    has_search = paths["n_search_touches"] > 0
    paths["path_type"] = np.select(
        [has_mid & has_search, has_mid, has_search],
        ["Mixed", "Mid-funnel-only", "Search-only"],
        default=OTHER,
    )

    def mid_funnel_then_search(sequence: str) -> bool:
        steps = sequence.split(" > ")
        if MID_FUNNEL not in steps or SEARCH not in steps:
            return False
        first_mid = steps.index(MID_FUNNEL)
        last_search = len(steps) - 1 - steps[::-1].index(SEARCH)
        return first_mid < last_search

    paths["mid_funnel_assisted_search"] = paths["channel_sequence"].map(mid_funnel_then_search)

    paths = paths.merge(
        activity.set_index("Conversion ID")[["Activity Date/Time", "Path Length"]],
        left_index=True,
        right_index=True,
    )
    paths["days_to_convert"] = (
        paths["Activity Date/Time"] - paths["first_touch_time"]
    ).dt.total_seconds() / 86400
    return paths.reset_index()


def build_touch_positions(touches: pd.DataFrame) -> pd.DataFrame:
    positions = touches.merge(
        touches.groupby("Conversion ID").size().rename("path_len_touch"),
        left_on="Conversion ID",
        right_index=True,
    )
    positions["position"] = np.where(
        positions["touch_order"] == 1,
        "First",
        np.where(positions["touch_order"] == positions["path_len_touch"], "Last", "Middle"),
    )
    positions.loc[positions["path_len_touch"] == 1, "position"] = "Only touch"
    return positions


def compute_lag_days(touches: pd.DataFrame, mixed: pd.DataFrame) -> pd.Series:
    """Days from the first mid-funnel exposure to the converting search click,
    for mid-funnel-assisted paths. Computed with a single grouped pass rather
    than one full scan of the touch table per conversion."""
    assisted = set(mixed.loc[mixed["mid_funnel_assisted_search"], "Conversion ID"])
    if not assisted:
        return pd.Series(dtype=float)

    subset = touches[touches["Conversion ID"].isin(assisted)]
    first_mid = subset[subset["channel"] == MID_FUNNEL].groupby("Conversion ID")["touch_time"].min()
    last_search = subset[subset["channel"] == SEARCH].groupby("Conversion ID")["touch_time"].max()

    lag = (last_search - first_mid).dropna().dt.total_seconds() / 86400
    return lag[lag >= 0]


def build_taxonomy_table(touches: pd.DataFrame) -> pd.DataFrame:
    """Campaign / site / channel / platform combinations present in the export."""
    return (
        touches[["campaign", "site", "channel", "platform"]]
        .drop_duplicates()
        .sort_values(["channel", "platform"])
        .reset_index(drop=True)
    )


def platform_live_windows(touches: pd.DataFrame) -> pd.DataFrame:
    """First / last recorded touch per platform, straight from the data, so the
    narrative stays correct on every refresh."""
    windows = touches.groupby("platform")["touch_time"].agg(["min", "max", "count"])
    windows.columns = ["first_touch", "last_touch", "touches"]
    return windows.sort_values("touches", ascending=False)


def derive_steady_state(touches: pd.DataFrame, taxonomy: Taxonomy) -> pd.Timestamp | None:
    """Date from which mid-funnel was live at all.

    Using the date on which *every* mid-funnel platform was live would discard
    weeks of valid data whenever one platform launches late; that case is
    covered by the partial-window caveat in the narrative instead.
    """
    mid = touches[touches["channel"] == MID_FUNNEL]
    if mid.empty:
        return None
    return pd.Timestamp(mid["touch_time"].min().normalize())


# ----------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------

class Metrics:
    """Container for every number referenced in the report narrative."""


def compute_metrics(
    df: pd.DataFrame,
    touches: pd.DataFrame,
    paths: pd.DataFrame,
    platform_volume: pd.DataFrame,
    lag_days: pd.Series,
    taxonomy: Taxonomy,
) -> Metrics:
    m = Metrics()
    m.n_conversions = len(paths)
    m.date_min = df["Activity Date/Time"].min()
    m.date_max = df["Activity Date/Time"].max()

    # Exports pulled with "Include Unattributed Conversions" carry rows with no
    # interactions at all (Path Length 0); every path metric below is computed on
    # the attributed subset, so both counts are reported for transparency.
    m.n_export_conversions = len(df)
    m.n_unattributed = m.n_export_conversions - m.n_conversions
    m.pct_attributed = m.n_conversions / m.n_export_conversions if m.n_export_conversions else float("nan")
    m.activity_name = df["Activity"].dropna().iloc[0] if "Activity" in df and len(df) else "n/a"
    m.live_windows = platform_live_windows(touches)

    counts = paths["path_type"].value_counts()
    pct = paths["path_type"].value_counts(normalize=True)
    m.n_search_only, m.pct_search_only = int(counts.get("Search-only", 0)), float(pct.get("Search-only", 0))
    m.n_mixed, m.pct_mixed = int(counts.get("Mixed", 0)), float(pct.get("Mixed", 0))
    m.n_mf_only, m.pct_mf_only = int(counts.get("Mid-funnel-only", 0)), float(pct.get("Mid-funnel-only", 0))

    mixed = paths[paths["path_type"] == "Mixed"].copy()
    m.n_mixed_paths = len(mixed)
    m.n_classic = int((
        (mixed["first_touch_channel"] == MID_FUNNEL) & (mixed["last_touch_channel"] == SEARCH)
    ).sum())
    m.pct_classic = m.n_classic / m.n_mixed_paths if m.n_mixed_paths else float("nan")

    last_click_search = paths[paths["last_touch_channel"] == SEARCH]
    m.n_last_click_search = len(last_click_search)
    m.n_assisted = int((last_click_search["n_mid_funnel_touches"] > 0).sum())
    m.pct_assisted = m.n_assisted / m.n_conversions if m.n_conversions else float("nan")

    # Any mid-funnel touch (Mixed + Mid-funnel-only) — the headline "touched" number
    touched = paths["n_mid_funnel_touches"] > 0
    m.n_mf_touched = int(touched.sum())
    m.pct_mf_touched = m.n_mf_touched / m.n_conversions if m.n_conversions else float("nan")
    m.n_untouched = m.n_conversions - m.n_mf_touched
    m.pct_untouched = m.n_untouched / m.n_conversions if m.n_conversions else float("nan")

    # Of the touched paths, how many had at least one mid-funnel CLICK vs
    # impression-only (view-through)
    mid = touches[touches["channel"] == MID_FUNNEL]
    if len(mid):
        mid_click = mid.groupby("Conversion ID")["interaction_type"].apply(lambda s: (s == "Click").any())
        m.n_mf_with_click = int(mid_click.sum())
        m.first_mf_date = mid["touch_time"].min()
    else:
        m.n_mf_with_click = 0
        m.first_mf_date = pd.NaT
    m.n_mf_impr_only = m.n_mf_touched - m.n_mf_with_click
    m.pct_mf_impr_only = m.n_mf_impr_only / m.n_mf_touched if m.n_mf_touched else float("nan")

    # Path length / velocity: any mid-funnel touch vs. search-only (never touched)
    m.touched_apl = paths.loc[touched, "Path Length"].mean()
    m.touched_days = paths.loc[touched, "days_to_convert"].mean()
    m.untouched_apl = paths.loc[~touched, "Path Length"].mean()
    m.untouched_days = paths.loc[~touched, "days_to_convert"].mean()

    m.by_type = paths.groupby("path_type").agg(
        conversions=("Conversion ID", "count"),
        avg_path_length=("Path Length", "mean"),
        avg_days_to_convert=("days_to_convert", "mean"),
    ).round(2)

    m.platform_volume = platform_volume
    m.lag_days = lag_days
    m.lag_median = lag_days.median() if len(lag_days) else float("nan")
    m.lag_mean = lag_days.mean() if len(lag_days) else float("nan")
    m.pct_multi_day = (lag_days >= 1).mean() if len(lag_days) else float("nan")

    m.mid_funnel_platforms = taxonomy.mid_funnel_platforms
    m.search_platforms = taxonomy.search_platforms
    m.mixed = mixed
    return m


# ----------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------

@dataclass
class PipelineResult:
    metrics: Metrics
    paths: pd.DataFrame
    touches: pd.DataFrame
    touches_full: pd.DataFrame
    mid_funnel_touches: pd.DataFrame
    lag_days: pd.Series
    taxonomy: Taxonomy
    export_meta: dict[str, str]
    unmapped_campaigns: list[str]
    unmapped_sites: list[str]


def run_pipeline(
    raw: bytes,
    taxonomy: Taxonomy,
    steady_state: pd.Timestamp | None = None,
) -> PipelineResult:
    export_meta, header_row = read_preamble(raw)

    # Whole export, used to decide whether a ramp-up caveat is needed and to draw
    # the mid-funnel timeseries across every day available.
    df_full = load_data(raw, header_row)
    slots = n_interaction_slots(df_full)
    campaigns, sites = distinct_values(df_full, slots)

    touches_full = build_touches(df_full, taxonomy, slots)
    activity_full = df_full[["Conversion ID", "Activity Date/Time", "Path Length"]]
    paths_full = build_paths(touches_full, activity_full)

    if steady_state is None:
        steady_state = derive_steady_state(touches_full, taxonomy)

    # An export pulled from the steady-state date onward needs no trimming; an
    # older one still covering the activation ramp-up does.
    has_rampup = bool(steady_state is not None and df_full["Activity Date/Time"].min() < steady_state)
    if has_rampup:
        df = load_data(raw, header_row, steady_state)
        touches = build_touches(df, taxonomy, slots)
        paths = build_paths(touches, df[["Conversion ID", "Activity Date/Time", "Path Length"]])
    else:
        df, touches, paths = df_full, touches_full, paths_full

    positions = build_touch_positions(touches)
    mid_funnel_touches = positions[positions["channel"] == MID_FUNNEL].copy()

    platform_volume = mid_funnel_touches.groupby("platform").agg(
        touches=("Conversion ID", "count"),
        conversions_influenced=("Conversion ID", "nunique"),
    ).sort_values("touches", ascending=False)
    platform_volume["pct_of_all_conversions"] = (
        platform_volume["conversions_influenced"] / len(paths) if len(paths) else np.nan
    )

    mixed = paths[paths["path_type"] == "Mixed"].copy()
    lag_days = compute_lag_days(touches, mixed)

    m = compute_metrics(df, touches, paths, platform_volume, lag_days, taxonomy)
    m.has_rampup = has_rampup
    m.steady_state_start = steady_state
    m.n_interaction_slots = slots
    m.taxonomy_table = build_taxonomy_table(touches)
    m.position_dist = position_distribution(mid_funnel_touches)

    # The export caps recorded interactions at `slots`, but Path Length reports
    # the true touch count, so longer journeys are silently truncated.
    m.n_truncated_paths = int((paths["Path Length"] > slots).sum())
    m.pct_truncated = m.n_truncated_paths / len(paths) if len(paths) else float("nan")
    m.max_path_length = int(paths["Path Length"].max()) if len(paths) else 0

    if has_rampup:
        m.ctx_full_n = len(paths_full)
        m.ctx_full_pct_touched = float((paths_full["n_mid_funnel_touches"] > 0).mean())
        m.ctx_full_pct_mixed = float((paths_full["path_type"] == "Mixed").mean())
        m.ctx_full_date_min = df_full["Activity Date/Time"].min()
        m.ctx_full_date_max = df_full["Activity Date/Time"].max()
        mid_full = touches_full[touches_full["channel"] == MID_FUNNEL]
        if len(mid_full):
            m.first_mf_date = mid_full["touch_time"].min()  # true first touch, pre-cut

    return PipelineResult(
        metrics=m,
        paths=paths,
        touches=touches,
        touches_full=touches_full,
        mid_funnel_touches=mid_funnel_touches,
        lag_days=lag_days,
        taxonomy=taxonomy,
        export_meta=export_meta,
        unmapped_campaigns=[c for c in campaigns if c not in taxonomy.channel_map],
        unmapped_sites=[s for s in sites if s not in taxonomy.platform_map],
    )


def position_distribution(mid_funnel_touches: pd.DataFrame) -> pd.DataFrame:
    if mid_funnel_touches.empty:
        return pd.DataFrame()
    dist = pd.crosstab(
        mid_funnel_touches["platform"], mid_funnel_touches["position"], normalize="index"
    ).round(3)
    return dist.reindex(
        columns=[c for c in ["First", "Middle", "Last", "Only touch"] if c in dist.columns],
        fill_value=0,
    )


def inspect_export(raw: bytes) -> dict[str, Any]:
    """Cheap pre-pass for the taxonomy step: what values need mapping."""
    export_meta, header_row = read_preamble(raw)
    df = load_data(raw, header_row)
    slots = n_interaction_slots(df)
    campaigns, sites = distinct_values(df, slots)
    return {
        "export_meta": export_meta,
        "campaigns": campaigns,
        "sites": sites,
        "pairs": pair_counts(df, slots),
        "slots": slots,
        "n_rows": len(df),
        "date_min": df["Activity Date/Time"].min(),
        "date_max": df["Activity Date/Time"].max(),
    }


def digest(raw: bytes) -> str:
    return hashlib.sha1(raw).hexdigest()
