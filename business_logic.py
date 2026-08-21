"""Waste, pacing, and Gemini reasoning for Media QA Copilot."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from data_manager import read_source
from rag_engine import REQUEST_TIMEOUT, retrieve_context, similarity_matrix


@dataclass
class OverlapFinding:
    meta_audience: str
    google_audience: str
    semantic_similarity: float
    overlap_percentage: float
    duplicated_conversions: int
    monthly_impact: float


@dataclass
class PacingFinding:
    campaign_name: str
    deviation: float
    actual: float
    planned: float


def detect_waste(threshold: float = 0.8) -> list[OverlapFinding]:
    """Detect waste using only CM360 data."""
    cm360 = read_source("cm360")
    
    # If no data or not enough rows, return empty findings
    if cm360.empty or len(cm360) < 2:
        return []
    
    findings: list[OverlapFinding] = []
    
    # Process CM360 data directly - extract audience pairs with high overlap
    for _, row in cm360.iterrows():
        try:
            overlap_pct = float(row.get("overlap_percentage", 0)) / 100
            if overlap_pct <= threshold:
                continue
            
            finding = OverlapFinding(
                meta_audience=str(row.get("meta_audience", "Unknown")),
                google_audience=str(row.get("google_audience", "Unknown")),
                semantic_similarity=overlap_pct,
                overlap_percentage=float(row.get("overlap_percentage", 0)),
                duplicated_conversions=int(row.get("duplicated_conversions", 0)),
                monthly_impact=float(row.get("overlap_cost", 0)),
            )
            findings.append(finding)
        except (ValueError, TypeError):
            continue
    
    return sorted(findings, key=lambda item: item.monthly_impact, reverse=True)


def monitor_pacing(threshold: float = 20.0) -> list[PacingFinding]:
    """Return campaigns whose absolute daily budget deviation exceeds the threshold."""
    pacing = read_source("pacing")
    anomalies = pacing[pacing["pct_deviation"].abs() > threshold]
    return [
        PacingFinding(
            campaign_name=str(row["campaign_name"]),
            deviation=float(row["pct_deviation"]),
            actual=float(row["daily_spend_actual"]),
            planned=float(row["daily_spend_plan"]),
        )
        for _, row in anomalies.iterrows()
    ]


def _local_reasoning(context: list[str], finding: OverlapFinding) -> tuple[str, str]:
    context_text = " ".join(context).lower()
    if "eficiencia" in context_text or "cpa" in context_text:
        strategic = (
            "El solapamiento contradice el objetivo de priorizar eficiencia y concentra "
            "inversión sobre una audiencia ya cubierta."
        )
    else:
        strategic = (
            "La duplicación reduce la cobertura incremental y desvía presupuesto de los "
            "objetivos definidos en el plan."
        )
    action = (
        "Reducir la inversión del conjunto con mayor CPA, aplicar exclusiones cruzadas "
        "y reasignar el presupuesto a audiencias incrementales."
    )
    return strategic, action


def _gemini_reasoning(
    context: list[str],
    finding: OverlapFinding,
) -> tuple[str, str] | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        )
        prompt = f"""
Actúa como director de medios. Responde en español con exactamente dos líneas:
CONTEXTO: una explicación ejecutiva de máximo 35 palabras basada solo en el plan.
ACCION: una recomendación operativa de máximo 30 palabras.

Hallazgo de solapamiento en CM360: {asdict(finding)}
Fragmentos del media plan:
{chr(10).join(context)}
"""
        response = model.generate_content(
            prompt,
            request_options={"timeout": REQUEST_TIMEOUT, "retry": None},
        )
        text = response.text.strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        context_line = next(
            (line.split(":", 1)[1].strip() for line in lines if line.startswith("CONTEXTO:")),
            "",
        )
        action_line = next(
            (line.split(":", 1)[1].strip() for line in lines if line.startswith("ACCION:")),
            "",
        )
        return (context_line, action_line) if context_line and action_line else None
    except Exception:
        return None


def run_copilot_analysis(media_plan: str) -> dict[str, Any]:
    """Run the complete QA pipeline and return structured, UI-ready findings."""
    overlaps = detect_waste()
    if not overlaps:
        return {"overlaps": [], "alert": None}

    primary = overlaps[0]
    query = (
        f"solapamiento en {primary.meta_audience} y {primary.google_audience}, "
        "eficiencia, duplicación y reasignación de presupuesto"
    )
    context = retrieve_context(query, media_plan)
    reasoning = _gemini_reasoning(context, primary)
    strategic, action = reasoning or _local_reasoning(context, primary)
    alert = {
        "confidence": primary.overlap_percentage,
        "duplicated_conversions": primary.duplicated_conversions,
        "monthly_impact": primary.monthly_impact,
        "strategic_context": strategic,
        "recommended_action": action,
    }
    return {"overlaps": overlaps, "alert": alert}


def findings_frame(findings: list[OverlapFinding]) -> pd.DataFrame:
    return pd.DataFrame([asdict(item) for item in findings])


def get_daily_platform_activity() -> pd.DataFrame:
    """Return daily platform activity data for multi-series chart.
    
    Returns a DataFrame with columns:
    - date: reporting date
    - platform: platform name (Google, Meta, Display, Search)
    - daily_touches: number of touches for that platform on that date
    - status: 'active', 'paused', or 'deactivated'
    """
    import datetime as dt
    
    # Generate 30 days of mock data
    base_date = dt.datetime.now() - dt.timedelta(days=30)
    dates = [base_date + dt.timedelta(days=i) for i in range(30)]
    
    platforms = ["Google Search", "Meta Ads", "Display", "LinkedIn"]
    records = []
    
    for date in dates:
        # Simulate daily touches with some variance
        day_of_week = date.weekday()
        base_multiplier = 1.2 if day_of_week < 5 else 0.8  # Higher on weekdays
        
        for platform in platforms:
            # Each platform has different baseline activity
            baseline = {"Google Search": 450, "Meta Ads": 380, "Display": 220, "LinkedIn": 120}.get(platform, 300)
            
            # Add daily variance
            import random
            random.seed(date.toordinal() + hash(platform) % 10000)
            daily_touches = int(baseline * base_multiplier * (0.8 + random.random() * 0.4))
            
            records.append({
                "date": date.date(),
                "platform": platform,
                "daily_touches": daily_touches,
                "status": "active"
            })
    
    return pd.DataFrame(records)


def get_path_mix_data() -> dict:
    """Return mid-funnel vs search path mix data.
    
    Returns a dict with:
    - categories: List of path types
    - absolute: List of absolute conversion counts
    - percentage: List of percentage of total conversions
    """
    # Mock data representing conversion path analysis
    total_conversions = 2847
    
    return {
        "categories": ["Search-only", "Mixed", "Mid-funnel-only"],
        "absolute": [1124, 1138, 585],
        "percentage": [39.5, 40.0, 20.5],
        "total": total_conversions,
        "description": (
            "Most conversions follow a mixed attribution path combining search and mid-funnel "
            "channels. Search-only conversions account for 39.5% of the total, indicating strong "
            "direct response performance. Mid-funnel-only conversions represent awareness and "
            "consideration plays with a 20.5% contribution rate."
        ),
    }


def get_journey_length_data() -> dict:
    """Return conversion journey length metrics.
    
    Returns a dict with:
    - groups: List of journey types
    - avg_path_length: Average number of touches per path
    - avg_days_to_convert: Average days from first touch to conversion
    - table_data: Detailed comparison metrics
    """
    return {
        "groups": ["Search-only", "Mixed", "Mid-funnel-only"],
        "avg_path_length": [1.2, 4.8, 3.1],
        "avg_days_to_convert": [1.3, 7.4, 5.2],
        "table_data": [
            {
                "Journey Type": "Search-only",
                "Avg Path Length": 1.2,
                "Avg Days to Convert": 1.3,
                "Conversions": 1124,
                "Total Touches": 1349,
            },
            {
                "Journey Type": "Mixed",
                "Avg Path Length": 4.8,
                "Avg Days to Convert": 7.4,
                "Conversions": 1138,
                "Total Touches": 5462,
            },
            {
                "Journey Type": "Mid-funnel-only",
                "Avg Path Length": 3.1,
                "Avg Days to Convert": 5.2,
                "Conversions": 585,
                "Total Touches": 1814,
            },
        ],
        "description": (
            "Search-only journeys are the fastest and most direct, with an average of 1.2 touches "
            "and 1.3 days to conversion. Mixed-path journeys involve significantly more interactions "
            "(4.8 touches, 7.4 days), reflecting complex customer decision-making. Mid-funnel-only "
            "journeys show moderate complexity with 3.1 touches and 5.2-day average conversion time."
        ),
    }


# ==================== REPORT DATA SECTIONS ====================

def get_executive_summary_data() -> dict:
    """Section 1: Executive Summary"""
    return {
        "introductory_paragraph": (
            "This comprehensive conversion path analysis examines 7,281 attributed conversions across "
            "multiple platforms and channels. The report reveals significant opportunities for optimization "
            "through audience segmentation and cross-platform journey mapping."
        ),
        "key_findings": [
            "Mixed-path conversions represent 40% of total attributed conversions",
            "Average conversion journey spans 4.2 touches across 2.8 platforms",
            "Mid-funnel channels drive 35% of total conversions but only cost 22% of media spend",
            "Search-to-Meta transitional patterns account for 18% of all conversions"
        ],
        "kpis": {
            "attributed_conversions": 7281,
            "mid_funnel_touched_pct": 68.5,
            "search_only_pct": 39.5,
            "mixed_paths_pct": 40.0,
            "median_conversion_lag_days": 5.2
        },
        "editable_summary": "Analysis shows strong mixed-path performance with clear cross-platform synergies."
    }


def get_methodology_data() -> dict:
    """Section 2: Methodology & Data Notes"""
    return {
        "data_source": "Campaign Manager 360 (CM360)",
        "analysed_period": "June 1, 2026 – August 31, 2026",
        "attribution_coverage": "95.2% of conversions with complete path data",
        "classification_methodology": "First-click, last-click, and linear attribution models applied",
        "lookback_window": "90 days from conversion event",
        "limitations": [
            "Cross-device tracking limited to authenticated users",
            "Direct traffic attribution relies on UTM parameters",
            "Offline conversions excluded from this analysis"
        ],
        "assumptions": [
            "Platform timestamps synchronized within 5-second window",
            "Session timeout set to 30 minutes of inactivity"
        ],
        "warnings": [
            "14 conversions (0.2%) removed due to timestamp inconsistencies"
        ]
    }


def get_top_converting_paths_data() -> dict:
    """Section 5: Top Converting Paths"""
    return {
        "paths": [
            {"path": "Google Search", "percentage": 12.5},
            {"path": "Meta Ads", "percentage": 10.2},
            {"path": "Display", "percentage": 8.7},
            {"path": "Google Search → Meta Ads", "percentage": 9.4},
            {"path": "Meta Ads → Google Search", "percentage": 7.8},
            {"path": "Display → Google Search", "percentage": 6.3},
            {"path": "Google Search → Display → Meta Ads", "percentage": 5.1},
        ],
        "table_data": [
            {"rank": 1, "path": "Google Search", "conversions": 911, "pct": 12.5},
            {"rank": 2, "path": "Meta Ads", "conversions": 742, "pct": 10.2},
            {"rank": 3, "path": "Display", "conversions": 633, "pct": 8.7},
            {"rank": 4, "path": "Google Search → Meta Ads", "conversions": 684, "pct": 9.4},
            {"rank": 5, "path": "Meta Ads → Google Search", "conversions": 568, "pct": 7.8},
        ],
        "editable_insights": "Single-channel journeys dominate but show declining efficiency compared to multi-touch paths."
    }


def get_platform_transition_data() -> dict:
    """Section 6: Platform Transition Flow"""
    platforms = ["Google Search", "Meta Ads", "Display", "LinkedIn"]
    # Transition probability matrix (from row to column)
    transition_matrix = [
        [0, 0.35, 0.28, 0.12],  # From Google Search
        [0.42, 0, 0.32, 0.08],  # From Meta Ads
        [0.38, 0.36, 0, 0.15],  # From Display
        [0.25, 0.30, 0.28, 0],  # From LinkedIn
    ]
    return {
        "platforms": platforms,
        "transition_matrix": transition_matrix,
        "editable_insights": "Meta Ads shows strongest transition to other platforms, indicating strong funnel acceleration properties."
    }


def get_platform_breakdown_data() -> dict:
    """Section 8: Platform Breakdown & Path Position"""
    return {
        "platform_table": [
            {"platform": "Google Search", "touches": 3248, "conversions_influenced": 2841, "pct": 39.0},
            {"platform": "Meta Ads", "touches": 2156, "conversions_influenced": 2103, "pct": 28.9},
            {"platform": "Display", "touches": 1834, "conversions_influenced": 1547, "pct": 21.2},
            {"platform": "LinkedIn", "touches": 892, "conversions_influenced": 790, "pct": 10.8},
        ],
        "path_position_data": {
            "Google Search": {"first": 35, "middle": 42, "last": 18, "only": 5},
            "Meta Ads": {"first": 28, "middle": 48, "last": 16, "only": 8},
            "Display": {"first": 22, "middle": 41, "last": 24, "only": 13},
            "LinkedIn": {"first": 18, "middle": 35, "last": 31, "only": 16},
        }
    }


def get_first_last_touch_data() -> dict:
    """Section 9: First Touch → Converting Touch"""
    platforms = ["Google Search", "Meta Ads", "Display", "LinkedIn"]
    return {
        "platforms": platforms,
        "first_touch_flows": [
            {"from": "Google Search", "to": "Google Search", "conversions": 892},
            {"from": "Google Search", "to": "Meta Ads", "conversions": 456},
            {"from": "Google Search", "to": "Display", "conversions": 234},
            {"from": "Meta Ads", "to": "Google Search", "conversions": 684},
            {"from": "Meta Ads", "to": "Meta Ads", "conversions": 512},
            {"from": "Meta Ads", "to": "Display", "conversions": 198},
            {"from": "Display", "to": "Google Search", "conversions": 412},
            {"from": "Display", "to": "Meta Ads", "conversions": 324},
        ]
    }


def get_funnel_velocity_data() -> dict:
    """Section 10: Funnel Velocity"""
    return {
        "histogram_data": {
            "bins": [0, 1, 2, 3, 5, 7, 14, 30, 60, 90],
            "counts": [2341, 1823, 1456, 892, 756, 543, 312, 98, 60, 0],
        },
        "median_days": 5.2,
        "mean_days": 7.8,
        "sample_size": 8281,
        "editable_interpretation": "Median 5.2-day conversion window indicates need for consistent retargeting cadence."
    }


def get_conclusions_data() -> dict:
    """Section 11: Conclusions & Recommendations"""
    return {
        "conclusions": [
            "Mixed-path conversions generate 40% of attributed value despite complex journey requirements",
            "Platform synergies exist between Google Search and Meta Ads (mutual 35%+ transition rates)",
            "Mid-funnel channels (Display, LinkedIn) deliver disproportionate value relative to cost"
        ],
        "recommendations": [
            "Implement sequential messaging strategy exploiting Google Search → Meta Ads transition pattern",
            "Increase mid-funnel budget allocation by 15-20% based on conversion efficiency",
            "Develop platform-specific audience exclusion rules to prevent unnecessary frequency capping",
            "Establish 7-day minimum lookback window for cross-platform attribution"
        ],
        "limitations": [
            "Analysis excludes offline conversions and phone leads",
            "Cross-device attribution limited to logged-in users",
            "Privacy-driven changes may impact future path visibility"
        ]
    }

