"""Generate mathematically coherent mock reporting CSVs for Google Ads, Meta Ads, and CM360."""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

OUTPUT_DIR = Path(__file__).resolve().parent / "data2"
DAYS = 30
RNG_SEED = 42

MONEY_DECIMALS = 2
RATE_DECIMALS = 4
FREQ_DECIMALS = 4


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _round_money(value: float) -> float:
    return round(value, MONEY_DECIMALS)


def _round_rate(value: float) -> float:
    return round(value, RATE_DECIMALS)


def _date_range(n_days: int) -> list[str]:
    today = date.today()
    start = today - timedelta(days=n_days - 1)
    return [(start + timedelta(days=i)).isoformat() for i in range(n_days)]


def _jitter(value: float, rng: random.Random, low: float = 0.75, high: float = 1.25) -> float:
    return value * rng.uniform(low, high)


def generate_google_ads(dates: list[str], rng: random.Random) -> pd.DataFrame:
    campaigns = [
        {
            "id": "GADS-SRCH-101",
            "name": "Search | Brand Footwear",
            "status": "Enabled",
            "type": "Search",
            "impressions": (8_000, 18_000),
            "ctr": (0.035, 0.085),
            "cpc": (0.45, 1.40),
            "cvr": (0.04, 0.12),
            "aov": (55, 95),
        },
        {
            "id": "GADS-SRCH-102",
            "name": "Search | Non-Brand Athletic Shoes",
            "status": "Enabled",
            "type": "Search",
            "impressions": (12_000, 28_000),
            "ctr": (0.018, 0.045),
            "cpc": (0.80, 2.20),
            "cvr": (0.02, 0.07),
            "aov": (60, 110),
        },
        {
            "id": "GADS-DISP-201",
            "name": "Display | Prospecting Retargeting",
            "status": "Enabled",
            "type": "Display",
            "impressions": (40_000, 90_000),
            "ctr": (0.002, 0.008),
            "cpc": (0.25, 0.90),
            "cvr": (0.005, 0.025),
            "aov": (45, 85),
        },
        {
            "id": "GADS-PMAX-301",
            "name": "PMax | Full Funnel Sales",
            "status": "Enabled",
            "type": "PMax",
            "impressions": (20_000, 50_000),
            "ctr": (0.008, 0.025),
            "cpc": (0.50, 1.60),
            "cvr": (0.025, 0.08),
            "aov": (70, 130),
        },
        {
            "id": "GADS-DISP-202",
            "name": "Display | Brand Awareness Holdout",
            "status": "Paused",
            "type": "Display",
            "impressions": (5_000, 12_000),
            "ctr": (0.0015, 0.005),
            "cpc": (0.20, 0.70),
            "cvr": (0.002, 0.012),
            "aov": (40, 75),
        },
    ]

    rows: list[dict] = []
    for campaign in campaigns:
        for day in dates:
            paused_zero = campaign["status"] == "Paused" and rng.random() < 0.35
            if paused_zero:
                impressions = 0
                clicks = 0
                cost = 0.0
                conversions = 0
                conversion_value = 0.0
            else:
                impressions = rng.randint(*campaign["impressions"])
                ctr_target = rng.uniform(*campaign["ctr"])
                clicks = min(impressions, max(0, int(round(impressions * ctr_target))))
                avg_cpc = rng.uniform(*campaign["cpc"])
                cost = _round_money(clicks * avg_cpc)
                cvr_target = rng.uniform(*campaign["cvr"])
                conversions = min(clicks, max(0, int(round(clicks * cvr_target))))
                aov = rng.uniform(*campaign["aov"])
                conversion_value = _round_money(conversions * aov)

            ctr = _round_rate(_safe_div(clicks, impressions))
            avg_cpc_out = _round_money(_safe_div(cost, clicks))
            cost_per_conv = _round_money(_safe_div(cost, conversions))
            conv_rate = _round_rate(_safe_div(conversions, clicks))
            conv_value_per_cost = _round_rate(_safe_div(conversion_value, cost))

            rows.append(
                {
                    "Date": day,
                    "Campaign ID": campaign["id"],
                    "Campaign Name": campaign["name"],
                    "Campaign Status": campaign["status"],
                    "Campaign Type": campaign["type"],
                    "Currency": "USD",
                    "Impressions": impressions,
                    "Clicks": clicks,
                    "CTR": ctr,
                    "Cost": cost,
                    "Avg. CPC": avg_cpc_out,
                    "Conversions": conversions,
                    "Cost / conv.": cost_per_conv,
                    "Conv. rate": conv_rate,
                    "Conversion value": conversion_value,
                    "Conv. value / cost": conv_value_per_cost,
                }
            )

    return pd.DataFrame(rows)


def generate_meta_ads(dates: list[str], rng: random.Random) -> pd.DataFrame:
    campaigns = [
        {
            "id": "META-SALES-001",
            "name": "Sales | Catalog DPA",
            "status": "Active",
            "objective": "OUTCOME_SALES",
            "impressions": (25_000, 60_000),
            "freq": (1.15, 2.40),
            "ctr": (0.008, 0.022),
            "cpc": (0.35, 1.10),
            "purchase_rate": (0.03, 0.09),
            "aov": (48, 92),
        },
        {
            "id": "META-SALES-002",
            "name": "Sales | Retargeting 7d Cart",
            "status": "Active",
            "objective": "OUTCOME_SALES",
            "impressions": (8_000, 20_000),
            "freq": (1.40, 3.20),
            "ctr": (0.015, 0.040),
            "cpc": (0.40, 1.30),
            "purchase_rate": (0.06, 0.16),
            "aov": (55, 105),
        },
        {
            "id": "META-SALES-003",
            "name": "Sales | Lookalike Purchasers 1%",
            "status": "Active",
            "objective": "OUTCOME_SALES",
            "impressions": (18_000, 45_000),
            "freq": (1.10, 2.10),
            "ctr": (0.006, 0.018),
            "cpc": (0.50, 1.50),
            "purchase_rate": (0.02, 0.07),
            "aov": (50, 98),
        },
        {
            "id": "META-TRAF-101",
            "name": "Traffic | Blog & Collection Pages",
            "status": "Active",
            "objective": "OUTCOME_TRAFFIC",
            "impressions": (30_000, 70_000),
            "freq": (1.20, 2.60),
            "ctr": (0.010, 0.030),
            "cpc": (0.12, 0.45),
            "purchase_rate": (0.004, 0.018),
            "aov": (40, 80),
        },
        {
            "id": "META-TRAF-102",
            "name": "Traffic | Seasonal Promo Holdout",
            "status": "Paused",
            "objective": "OUTCOME_TRAFFIC",
            "impressions": (6_000, 15_000),
            "freq": (1.05, 1.80),
            "ctr": (0.007, 0.020),
            "cpc": (0.15, 0.50),
            "purchase_rate": (0.003, 0.012),
            "aov": (35, 70),
        },
    ]

    rows: list[dict] = []
    for campaign in campaigns:
        for day in dates:
            paused_zero = campaign["status"] == "Paused" and rng.random() < 0.35
            if paused_zero:
                impressions = 0
                reach = 0
                frequency = 0.0
                link_clicks = 0
                amount_spent = 0.0
                purchases = 0
                purchase_value = 0.0
            else:
                impressions = rng.randint(*campaign["impressions"])
                frequency_target = rng.uniform(*campaign["freq"])
                reach = max(1, min(impressions, int(round(impressions / frequency_target))))
                frequency = _round_rate(_safe_div(impressions, reach))
                ctr_target = rng.uniform(*campaign["ctr"])
                link_clicks = min(impressions, max(0, int(round(impressions * ctr_target))))
                cpc_target = rng.uniform(*campaign["cpc"])
                amount_spent = _round_money(link_clicks * cpc_target)
                purchases = min(link_clicks, max(0, int(round(link_clicks * rng.uniform(*campaign["purchase_rate"])))))
                purchase_value = _round_money(purchases * rng.uniform(*campaign["aov"]))

            if campaign["objective"] == "OUTCOME_SALES":
                results = purchases
            else:
                results = link_clicks

            cpc = _round_money(_safe_div(amount_spent, link_clicks))
            ctr = _round_rate(_safe_div(link_clicks, impressions))
            cost_per_result = _round_money(_safe_div(amount_spent, results))
            purchase_roas = _round_rate(_safe_div(purchase_value, amount_spent))

            rows.append(
                {
                    "Date": day,
                    "Campaign ID": campaign["id"],
                    "Campaign Name": campaign["name"],
                    "Campaign Status": campaign["status"],
                    "Objective": campaign["objective"],
                    "Reach": reach,
                    "Impressions": impressions,
                    "Frequency": frequency,
                    "Amount Spent": amount_spent,
                    "Link Clicks": link_clicks,
                    "CPC (Cost per Link Click)": cpc,
                    "CTR (Link Click-Through Rate)": ctr,
                    "Results": results,
                    "Cost per Result": cost_per_result,
                    "Purchases": purchases,
                    "Purchases Conversion Value": purchase_value,
                    "Purchase ROAS": purchase_roas,
                }
            )

    return pd.DataFrame(rows)


def generate_cm360(dates: list[str], rng: random.Random) -> pd.DataFrame:
    advertiser_id = "ADV-78421"
    advertiser = "Northwind Athletic"

    campaigns = [
        {
            "id": "CM-DISP-501",
            "name": "CM360 | Programmatic Display Prospecting",
            "impressions": (80_000, 160_000),
            "ctr": (0.0008, 0.0035),
            "viewability": (0.52, 0.78),
            "cpm": (3.50, 8.50),
            "ctc_rate": (0.008, 0.030),
            "vtc_share": (0.35, 0.70),
            "revenue_per_conv": (40, 90),
        },
        {
            "id": "CM-DISP-502",
            "name": "CM360 | Site Retargeting",
            "impressions": (25_000, 55_000),
            "ctr": (0.002, 0.008),
            "viewability": (0.58, 0.82),
            "cpm": (4.00, 9.50),
            "ctc_rate": (0.02, 0.07),
            "vtc_share": (0.15, 0.45),
            "revenue_per_conv": (50, 110),
        },
        {
            "id": "CM-OLV-601",
            "name": "CM360 | Online Video Sports",
            "impressions": (40_000, 90_000),
            "ctr": (0.001, 0.004),
            "viewability": (0.65, 0.88),
            "cpm": (8.00, 18.00),
            "ctc_rate": (0.01, 0.04),
            "vtc_share": (0.40, 0.75),
            "revenue_per_conv": (35, 85),
        },
        {
            "id": "CM-DISP-503",
            "name": "CM360 | High Impact Homepage Takeover",
            "impressions": (10_000, 22_000),
            "ctr": (0.003, 0.010),
            "viewability": (0.70, 0.92),
            "cpm": (12.00, 28.00),
            "ctc_rate": (0.015, 0.05),
            "vtc_share": (0.20, 0.50),
            "revenue_per_conv": (45, 100),
        },
        {
            "id": "CM-AUD-701",
            "name": "CM360 | Audio Podcast Sponsorship",
            "impressions": (15_000, 35_000),
            "ctr": (0.0005, 0.0025),
            "viewability": (0.40, 0.65),
            "cpm": (6.00, 14.00),
            "ctc_rate": (0.005, 0.02),
            "vtc_share": (0.45, 0.80),
            "revenue_per_conv": (30, 70),
        },
    ]

    rows: list[dict] = []
    for campaign in campaigns:
        for day in dates:
            impressions = int(_jitter(rng.randint(*campaign["impressions"]), rng, 0.85, 1.15))
            ctr_target = rng.uniform(*campaign["ctr"])
            clicks = min(impressions, max(0, int(round(impressions * ctr_target))))
            viewable = min(impressions, max(0, int(round(impressions * rng.uniform(*campaign["viewability"])))))
            media_cost = _round_money(impressions / 1000 * rng.uniform(*campaign["cpm"]))

            ctc = min(clicks, max(0, int(round(clicks * rng.uniform(*campaign["ctc_rate"])))))
            vtc_ratio = rng.uniform(*campaign["vtc_share"])
            if ctc == 0:
                vtc = rng.randint(0, 8)
                total_conversions = vtc
            else:
                total_conversions = max(ctc, int(round(ctc / (1 - vtc_ratio)))) if vtc_ratio < 0.95 else ctc + rng.randint(1, 12)
                vtc = total_conversions - ctc

            total_revenue = _round_money(total_conversions * rng.uniform(*campaign["revenue_per_conv"]))
            click_rate = _round_rate(_safe_div(clicks, impressions))
            cost_per_ctc = _round_money(_safe_div(media_cost, ctc))

            rows.append(
                {
                    "Date": day,
                    "Advertiser ID": advertiser_id,
                    "Advertiser": advertiser,
                    "Campaign ID": campaign["id"],
                    "Campaign": campaign["name"],
                    "Impressions": impressions,
                    "Clicks": clicks,
                    "Click Rate": click_rate,
                    "Active View: Viewable Impressions": viewable,
                    "Media Cost": media_cost,
                    "Total Conversions": total_conversions,
                    "Click-through Conversions": ctc,
                    "View-through Conversions": vtc,
                    "Total Revenue": total_revenue,
                    "Cost Per Click-through Conversion": cost_per_ctc,
                }
            )

    return pd.DataFrame(rows)


def _assert_google_ads(df: pd.DataFrame) -> None:
    assert (df["Clicks"] <= df["Impressions"]).all()
    assert (df["Conversions"] <= df["Clicks"]).all()
    expected_ctr = (df["Clicks"] / df["Impressions"].replace(0, pd.NA)).fillna(0).round(RATE_DECIMALS)
    assert (df["CTR"] == expected_ctr).all()


def _assert_meta(df: pd.DataFrame) -> None:
    assert (df["Reach"] <= df["Impressions"]).all()
    assert (df["Link Clicks"] <= df["Impressions"]).all()
    assert (df["Purchases"] <= df["Link Clicks"]).all()
    non_zero = df["Reach"] > 0
    expected_freq = (df.loc[non_zero, "Impressions"] / df.loc[non_zero, "Reach"]).round(RATE_DECIMALS)
    assert (df.loc[non_zero, "Frequency"] == expected_freq).all()


def _assert_cm360(df: pd.DataFrame) -> None:
    assert (df["Clicks"] <= df["Impressions"]).all()
    assert (df["Active View: Viewable Impressions"] <= df["Impressions"]).all()
    assert (df["Click-through Conversions"] <= df["Clicks"]).all()
    assert (
        df["Total Conversions"]
        == df["Click-through Conversions"] + df["View-through Conversions"]
    ).all()


def main() -> None:
    rng = random.Random(RNG_SEED)
    dates = _date_range(DAYS)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    google_ads = generate_google_ads(dates, rng)
    meta_ads = generate_meta_ads(dates, rng)
    cm360 = generate_cm360(dates, rng)

    _assert_google_ads(google_ads)
    _assert_meta(meta_ads)
    _assert_cm360(cm360)

    outputs = {
        "google_ads_mock.csv": google_ads,
        "meta_ads_mock.csv": meta_ads,
        "cm360_mock.csv": cm360,
    }

    for filename, frame in outputs.items():
        path = OUTPUT_DIR / filename
        frame.to_csv(path, index=False)
        print("=" * 80)
        print(f"{filename}  ({len(frame)} rows)  ->  {path}")
        print(frame.head().to_string(index=False))
        print()


if __name__ == "__main__":
    main()
