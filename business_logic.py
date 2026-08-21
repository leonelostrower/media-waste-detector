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
    """Compare connected network audiences and verify candidates in CM360."""
    meta = read_source("meta")
    google = read_source("google_ads")
    cm360 = read_source("cm360")

    meta_texts = (
        meta["ad_set_name"].astype(str) + ". " + meta["audience_description"].astype(str)
    ).tolist()
    google_texts = (
        google["ad_group_name"].astype(str)
        + ". "
        + google["audience_description"].astype(str)
    ).tolist()
    similarities = similarity_matrix(meta_texts, google_texts)

    findings: list[OverlapFinding] = []
    for meta_index, meta_row in meta.iterrows():
        for google_index, google_row in google.iterrows():
            verification = cm360[
                (cm360["meta_audience"] == meta_row["ad_set_name"])
                & (cm360["google_audience"] == google_row["ad_group_name"])
            ]
            verified_confidence = (
                float(verification.iloc[0]["overlap_percentage"]) / 100
                if not verification.empty
                else 0.0
            )
            semantic_score = float(similarities[meta_index, google_index])
            confidence = max(semantic_score, verified_confidence)
            if confidence <= threshold or verification.empty:
                continue
            match = verification.iloc[0]
            findings.append(
                OverlapFinding(
                    meta_audience=str(meta_row["ad_set_name"]),
                    google_audience=str(google_row["ad_group_name"]),
                    semantic_similarity=semantic_score,
                    overlap_percentage=float(match["overlap_percentage"]),
                    duplicated_conversions=int(match["duplicated_conversions"]),
                    monthly_impact=float(match["overlap_cost"]),
                )
            )
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
    pacing: list[PacingFinding],
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

Hallazgo: {asdict(finding)}
Desvíos de pacing: {[asdict(item) for item in pacing]}
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
    pacing = monitor_pacing()
    if not overlaps:
        return {"overlaps": [], "pacing": pacing, "alert": None}

    primary = overlaps[0]
    query = (
        f"solapamiento {primary.meta_audience} {primary.google_audience}, "
        "eficiencia, CPA, duplicación y reasignación de presupuesto"
    )
    context = retrieve_context(query, media_plan)
    reasoning = _gemini_reasoning(context, primary, pacing)
    strategic, action = reasoning or _local_reasoning(context, primary)
    alert = {
        "confidence": primary.overlap_percentage,
        "duplicated_conversions": primary.duplicated_conversions,
        "monthly_impact": primary.monthly_impact,
        "strategic_context": strategic,
        "recommended_action": action,
    }
    return {"overlaps": overlaps, "pacing": pacing, "alert": alert}


def findings_frame(findings: list[OverlapFinding]) -> pd.DataFrame:
    return pd.DataFrame([asdict(item) for item in findings])
