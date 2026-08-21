"""Gemini agents for the path-to-conversion report.

Two jobs, both degrading gracefully to deterministic behaviour when no API key
is configured or the model returns something unusable:

1. propose_taxonomy - classify the export's campaigns and sites.
2. rewrite_narrative - turn the computed draft into client-ready prose without
   ever changing a number.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, replace
from typing import Any

import pandas as pd

from ptc_narrative import (
    NarrativeSection,
    Prose,
    allowed_numbers,
    unsupported_numbers,
)
from ptc_pipeline import (
    MID_FUNNEL,
    OTHER,
    SEARCH,
    Taxonomy,
    is_null_token,
    reconcile_platform_channel,
)
from rag_engine import REQUEST_TIMEOUT

SEARCH_HINTS = ("google search", "msn search", "bing", "yahoo search")


# ----------------------------------------------------------------------------
# Gemini plumbing
# ----------------------------------------------------------------------------

def gemini_available() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def _call_gemini(prompt: str, temperature: float = 0.2) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
        response = model.generate_content(
            prompt,
            generation_config={"temperature": temperature, "response_mime_type": "application/json"},
            request_options={"timeout": REQUEST_TIMEOUT, "retry": None},
        )
        return (response.text or "").strip()
    except Exception:
        return None


def _parse_json(text: str | None) -> Any:
    if not text:
        return None
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"[\{\[].*[\}\]]", cleaned, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


# ----------------------------------------------------------------------------
# Agent 1: taxonomy
# ----------------------------------------------------------------------------

def infer_platform_name(site: str) -> str:
    """Clean platform name from a raw CM360 site value, handling the common
    'Advertiser - Platform' and 'Campaign : Platform' naming patterns."""
    if is_null_token(site):
        return OTHER
    lowered = site.lower()
    for needle, platform in (
        ("google", "Google Search"),
        ("msn", "MSN Search"),
        ("bing", "MSN Search"),
        ("facebook", "Facebook"),
        ("instagram", "Instagram"),
        ("reddit", "Reddit"),
        ("tiktok", "TikTok"),
        ("pinterest", "Pinterest"),
        ("stackadapt", "StackAdapt"),
        ("stack adapt", "StackAdapt"),
        ("youtube", "YouTube"),
        ("linkedin", "LinkedIn"),
        ("snapchat", "Snapchat"),
        ("amazon", "Amazon"),
    ):
        if needle in lowered:
            return platform
    if re.search(r"\bfb\b", lowered):
        return "Facebook"
    if re.search(r"\byt\b", lowered):
        return "YouTube"

    # Strip the advertiser / campaign prefix and title-case what remains.
    tail = re.split(r"\s*[:\-|]\s*", site)[-1].strip()
    return tail.title() if tail else OTHER


def infer_channel(campaign: str) -> str:
    """Search campaigns almost always name themselves; everything else that is
    running against a path-to-conversion export is mid-funnel by elimination."""
    if is_null_token(campaign):
        return OTHER
    lowered = campaign.lower()
    if any(token in lowered for token in ("search", "sem", "brand term", "pmax", "shopping")):
        return SEARCH
    return MID_FUNNEL


def heuristic_taxonomy(campaigns: list[str], sites: list[str]) -> Taxonomy:
    return Taxonomy(
        channel_map={campaign: infer_channel(campaign) for campaign in campaigns},
        platform_map={site: infer_platform_name(site) for site in sites},
    )


TAXONOMY_PROMPT = """You are a paid-media analyst classifying a Campaign Manager 360 \
path-to-conversion export so it can be analysed.

Export metadata:
{meta}

Campaigns present in the export:
{campaigns}

Sites present in the export, with the campaigns they run under:
{pairs}

For every campaign, decide its channel:
- "Search" for paid search / SEM campaigns (Google Search, Bing/MSN, brand terms, PMax, shopping).
- "Mid-funnel" for social, display, video, native and programmatic awareness or consideration \
campaigns.
- "Other" only if it genuinely fits neither.

For every site, give the clean consumer-facing platform name (for example "Rates.ca - FB" becomes \
"Facebook", "DART Search : Google" becomes "Google Search", "Acme - StackAdapt" becomes \
"StackAdapt"). Strip advertiser and campaign prefixes. Use the well-known brand spelling. Two \
different sites that mean the same platform must get exactly the same name.

Respond with JSON only, using this exact shape:
{{"campaigns": {{"<campaign name>": "Search|Mid-funnel|Other"}}, \
"sites": {{"<site name>": "<platform name>"}}, "notes": "<one short sentence, or empty>"}}

Every campaign and every site listed above must appear as a key, spelled exactly as given."""


@dataclass
class TaxonomyProposal:
    taxonomy: Taxonomy
    source: str  # "agent" | "heuristic"
    notes: str = ""


def propose_taxonomy(
    campaigns: list[str],
    sites: list[str],
    pairs: pd.DataFrame,
    export_meta: dict[str, str] | None = None,
) -> TaxonomyProposal:
    """Ask the model to classify campaigns and sites, falling back to the naming
    heuristics. Platform channel is always derived from the export itself, so
    the two halves of the mapping cannot disagree."""
    fallback = heuristic_taxonomy(campaigns, sites)
    proposal = TaxonomyProposal(taxonomy=fallback, source="heuristic")

    if campaigns or sites:
        pair_lines = "\n".join(
            f"- {row.site} (under campaign: {row.campaign}, {row.n:,} touches)"
            for row in pairs.itertuples()
        ) if len(pairs) else "\n".join(f"- {site}" for site in sites)

        prompt = TAXONOMY_PROMPT.format(
            meta=json.dumps(export_meta or {}, indent=2)[:1500],
            campaigns="\n".join(f"- {campaign}" for campaign in campaigns),
            pairs=pair_lines[:4000],
        )
        parsed = _parse_json(_call_gemini(prompt))
        if isinstance(parsed, dict):
            channel_map = dict(fallback.channel_map)
            platform_map = dict(fallback.platform_map)
            valid_channels = {SEARCH, MID_FUNNEL, OTHER}

            for campaign, channel in (parsed.get("campaigns") or {}).items():
                if campaign in channel_map and str(channel) in valid_channels:
                    channel_map[campaign] = str(channel)
            for site, platform in (parsed.get("sites") or {}).items():
                if site in platform_map and str(platform).strip():
                    platform_map[site] = str(platform).strip()

            proposal = TaxonomyProposal(
                taxonomy=Taxonomy(channel_map=channel_map, platform_map=platform_map),
                source="agent",
                notes=str(parsed.get("notes") or ""),
            )

    proposal.taxonomy.platform_channel = resolve_platform_channel(proposal.taxonomy, pairs)
    return proposal


def resolve_platform_channel(taxonomy: Taxonomy, pairs: pd.DataFrame) -> dict[str, str]:
    """Derive each platform's channel from the campaigns it runs under, with a
    name-based backstop for platforms the export cannot place."""
    resolved = reconcile_platform_channel(pairs, taxonomy.channel_map, taxonomy.platform_map)
    for platform in taxonomy.platforms:
        if resolved.get(platform) in {SEARCH, MID_FUNNEL}:
            continue
        lowered = str(platform).lower()
        resolved[platform] = SEARCH if any(h in lowered for h in SEARCH_HINTS) else MID_FUNNEL
    return resolved


# ----------------------------------------------------------------------------
# Agent 2: narrative
# ----------------------------------------------------------------------------

NARRATIVE_PROMPT = """You are a senior paid-media strategist finalising a client-facing \
Path-to-Conversion report.

Below is a verified fact sheet and a machine-generated draft. Rewrite the draft into polished, \
confident, client-ready prose in {language}.

ABSOLUTE RULES
1. Never invent, recompute, round or alter a number. Every figure, percentage, count and date you \
write must appear verbatim in the fact sheet or in the draft block you are rewriting.
2. If a claim in the draft is not supported by the numbers, do not repeat it. Report it in "flags" \
instead and rewrite the sentence to match what the data actually shows.
3. Keep the same structure: same number of blocks per section, bullets stay bullets \
(lines starting with "- "), paragraphs stay paragraphs.
4. Keep markdown bold lead-ins like "**Path mix**:" where the draft has them.
5. Do not add headings, preambles or commentary inside the text.

VERIFIED FACT SHEET
{fact_sheet}

DRAFT BLOCKS
{blocks}

Respond with JSON only:
{{"blocks": {{"<block id>": "<rewritten markdown>"}}, \
"flags": [{{"section": "<section id>", "issue": "<one sentence>"}}]}}

Every block id above must appear as a key."""


@dataclass
class NarrativeReview:
    sections: list[NarrativeSection]
    flags: list[dict[str, str]]
    rejected: list[dict[str, str]]
    source: str  # "agent" | "draft"


def _block_id(section_id: str, index: int) -> str:
    return f"{section_id}::{index}"


def rewrite_narrative(
    sections: list[NarrativeSection],
    fact_sheet: dict[str, str],
    language: str = "English",
) -> NarrativeReview:
    """Rewrite every prose block, then verify that the agent did not introduce a
    number the data does not support. Blocks that fail keep the draft text."""
    allowed = allowed_numbers(sections, fact_sheet)

    draft_blocks: dict[str, str] = {}
    for section in sections:
        for index, block in enumerate(section.blocks):
            if isinstance(block, Prose):
                draft_blocks[_block_id(section.id, index)] = block.text

    if not draft_blocks or not gemini_available():
        return NarrativeReview(sections=sections, flags=[], rejected=[], source="draft")

    rendered = "\n\n".join(
        f"### {block_id}\n{text}" for block_id, text in draft_blocks.items()
    )
    prompt = NARRATIVE_PROMPT.format(
        language=language,
        fact_sheet=json.dumps(fact_sheet, indent=2),
        blocks=rendered,
    )
    parsed = _parse_json(_call_gemini(prompt, temperature=0.35))
    if not isinstance(parsed, dict) or not isinstance(parsed.get("blocks"), dict):
        return NarrativeReview(sections=sections, flags=[], rejected=[], source="draft")

    rewritten = parsed["blocks"]
    rejected: list[dict[str, str]] = []
    updated: list[NarrativeSection] = []

    for section in sections:
        blocks = list(section.blocks)
        for index, block in enumerate(blocks):
            if not isinstance(block, Prose):
                continue
            candidate = rewritten.get(_block_id(section.id, index))
            if not isinstance(candidate, str) or not candidate.strip():
                continue
            candidate = candidate.strip()
            unsupported = unsupported_numbers(candidate, allowed)
            if unsupported:
                rejected.append({
                    "section": section.heading,
                    "numbers": ", ".join(unsupported),
                })
                continue
            blocks[index] = Prose(text=candidate)
        updated.append(replace(section, blocks=blocks))

    flags = [
        {"section": str(flag.get("section", "")), "issue": str(flag.get("issue", ""))}
        for flag in (parsed.get("flags") or [])
        if isinstance(flag, dict) and flag.get("issue")
    ]
    return NarrativeReview(sections=updated, flags=flags, rejected=rejected, source="agent")
