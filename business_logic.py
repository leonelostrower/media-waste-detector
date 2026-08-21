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
