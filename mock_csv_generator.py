"""Standalone generator for local platform exports used by Media QA Copilot."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"


def _write_csv(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def generate_exports(output_dir: Path | None = None) -> Path:
    """Create data/ and the four platform CSVs. Returns the output directory."""
    target = output_dir or DATA_DIR
    target.mkdir(parents=True, exist_ok=True)

    _write_csv(
        target / "meta.csv",
        [
            {
                "campaign_id": "META-SNK-001",
                "ad_set_name": "Sneakerheads",
                "audience_description": (
                    "Sneakerheads: enthusiasts of limited-edition athletic sneakers, "
                    "streetwear drops, and premium basketball shoes."
                ),
                "spend": 18500.00,
                "conversions": 142,
            },
            {
                "campaign_id": "META-RET-002",
                "ad_set_name": "Cart Abandoners 7d",
                "audience_description": (
                    "Users who added running or basketball shoes to cart in the last 7 days "
                    "but did not purchase."
                ),
                "spend": 4200.00,
                "conversions": 88,
            },
            {
                "campaign_id": "META-LAL-003",
                "ad_set_name": "LAL Purchasers 1%",
                "audience_description": (
                    "1% lookalike of purchasers of athletic footwear in the last 90 days."
                ),
                "spend": 9100.00,
                "conversions": 61,
            },
            {
                "campaign_id": "META-AW-004",
                "ad_set_name": "Parents Back to School",
                "audience_description": (
                    "Parents of school-age children interested in affordable kids apparel "
                    "and school supplies, not athletic sneakers."
                ),
                "spend": 3500.00,
                "conversions": 40,
            },
        ],
    )

    _write_csv(
        target / "gads.csv",
        [
            {
                "campaign_id": "GADS-INM-101",
                "ad_group_name": "Athletic Shoes",
                "audience_description": (
                    "Athletic Shoes In-Market: shoppers actively researching running shoes, "
                    "basketball sneakers, and performance athletic footwear."
                ),
                "spend": 16200.00,
                "conversions": 155,
            },
            {
                "campaign_id": "GADS-BRD-102",
                "ad_group_name": "Brand Exact Footwear",
                "audience_description": (
                    "Users searching brand-exact terms for our sneaker lines and official store."
                ),
                "spend": 7800.00,
                "conversions": 210,
            },
            {
                "campaign_id": "GADS-YTB-103",
                "ad_group_name": "YouTube Sports Highlights",
                "audience_description": (
                    "YouTube viewers of professional basketball and running race highlights."
                ),
                "spend": 5400.00,
                "conversions": 29,
            },
            {
                "campaign_id": "GADS-GSP-104",
                "ad_group_name": "School Uniforms Shopping",
                "audience_description": (
                    "In-market for school uniforms, backpacks, and kids apparel; not athletic shoes."
                ),
                "spend": 2100.00,
                "conversions": 18,
            },
        ],
    )

    _write_csv(
        target / "cm360.csv",
        [
            {
                "meta_audience": "Sneakerheads",
                "google_audience": "Athletic Shoes",
                "overlap_percentage": 85.0,
                "duplicated_conversions": 48,
                "overlap_cost": 4200.00,
            },
            {
                "meta_audience": "Cart Abandoners 7d",
                "google_audience": "Brand Exact Footwear",
                "overlap_percentage": 22.0,
                "duplicated_conversions": 6,
                "overlap_cost": 310.00,
            },
            {
                "meta_audience": "LAL Purchasers 1%",
                "google_audience": "YouTube Sports Highlights",
                "overlap_percentage": 14.0,
                "duplicated_conversions": 3,
                "overlap_cost": 180.00,
            },
            {
                "meta_audience": "Parents Back to School",
                "google_audience": "School Uniforms Shopping",
                "overlap_percentage": 41.0,
                "duplicated_conversions": 5,
                "overlap_cost": 420.00,
            },
            {
                "meta_audience": "Sneakerheads",
                "google_audience": "Brand Exact Footwear",
                "overlap_percentage": 31.0,
                "duplicated_conversions": 18,
                "overlap_cost": 890.00,
            },
            {
                "meta_audience": "Cart Abandoners 7d",
                "google_audience": "Athletic Shoes",
                "overlap_percentage": 56.0,
                "duplicated_conversions": 14,
                "overlap_cost": 720.00,
            },
            {
                "meta_audience": "LAL Purchasers 1%",
                "google_audience": "Brand Exact Footwear",
                "overlap_percentage": 19.0,
                "duplicated_conversions": 8,
                "overlap_cost": 450.00,
            },
        ],
    )

    _write_csv(
        target / "pacing.csv",
        [
            {
                "campaign_name": "Meta — Sneakerheads",
                "daily_spend_actual": 1850.00,
                "daily_spend_plan": 1200.00,
                "pct_deviation": 54.17,
            },
            {
                "campaign_name": "Google — Athletic Shoes",
                "daily_spend_actual": 980.00,
                "daily_spend_plan": 1100.00,
                "pct_deviation": -10.91,
            },
            {
                "campaign_name": "Meta — Cart Abandoners 7d",
                "daily_spend_actual": 410.00,
                "daily_spend_plan": 400.00,
                "pct_deviation": 2.50,
            },
            {
                "campaign_name": "Google — Brand Exact Footwear",
                "daily_spend_actual": 720.00,
                "daily_spend_plan": 700.00,
                "pct_deviation": 2.86,
            },
            {
                "campaign_name": "YouTube — Sports Highlights",
                "daily_spend_actual": 310.00,
                "daily_spend_plan": 450.00,
                "pct_deviation": -31.11,
            },
        ],
    )

    return target


if __name__ == "__main__":
    out = generate_exports()
    print(f"Exports generated in: {out}")
    for path in sorted(out.iterdir()):
        if path.suffix == ".csv":
            print(f"  - {path.name}")
