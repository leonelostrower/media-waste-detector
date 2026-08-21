# Media QA Copilot

Streamlit app that finds **cross-platform media waste**: overlapping audiences between Meta and Google Ads, duplicate conversions verified in Campaign Manager 360, and daily pacing deviations against the media plan.

The UI is Spanish. Platform exports and the demo client (**Northstar Athletic**, performance footwear) are English.

## What it does

Media teams often buy the same people twice: a Meta ad set like “Sneakerheads” and a Google in-market group like “Athletic Shoes.” Networks report conversions independently, so spend and CPA look fine until you check an independent pixel (CM360).

For each client workspace the copilot:

1. **Connects sources** (demo handshake; data comes from local CSVs).
2. **Indexes the media plan** (paste or upload TXT/PDF) for retrieval.
3. **Compares audience taxonomies** with embeddings (Gemini if configured, otherwise TF-IDF).
4. **Confirms overlap in CM360** (overlap %, duplicated conversions, overlap cost).
5. **Flags pacing** when daily spend is more than 20% off plan.
6. **Writes an executive alert** with strategic context and a recommended action (Gemini, or a local heuristic).

Analysis is enabled only when CM360 is connected, at least one of Google Ads / Meta is connected, and a media plan is saved.

Default thresholds:

- Audience overlap / semantic similarity: **> 80%**
- Pacing deviation: **> 20%** absolute vs. daily plan

## Architecture

| File | Role |
| --- | --- |
| `app.py` | Streamlit UI: client portfolio, source cards, media-plan editor, QA results |
| `data_manager.py` | Clients in `clients.json`, logos under `data/logos/`, CSV reads |
| `business_logic.py` | Waste detection, pacing, Gemini / local reasoning |
| `rag_engine.py` | Chunking, embeddings, cosine similarity, top-k retrieval |
| `mock_csv_generator.py` | Regenerates demo platform exports |
| `data/` | `meta.csv`, `gads.csv`, `cm360.csv`, `pacing.csv`, sample plan |

Connecting a source in the UI does not call live APIs. It sleeps through a fake handshake, then reads the matching CSV. Connecting CM360 also loads `pacing.csv`.

## Setup

Python 3.11+ recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Gemini is optional. Without a key, similarity uses TF-IDF and alerts use the local heuristic.

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# set GEMINI_API_KEY
```

You can also export `GEMINI_API_KEY`. Optional overrides: `GEMINI_MODEL` (default `gemini-2.0-flash`), `GEMINI_EMBEDDING_MODEL` (default `models/text-embedding-004`).

Do not commit `.streamlit/secrets.toml` or `clients.json`.

## Run

```bash
streamlit run app.py
```

1. Open a client (a **Northstar Athletic** workspace is created on first run).
2. **Fuentes de datos**: connect CM360 (required) plus Google Ads and/or Meta.
3. **Contexto de negocio**: paste strategy or upload TXT/PDF, then save. Sample copy: `data/estrategia_medios.txt`.
4. **QA & Insights**: run analysis.

Expected demo signal: **Sneakerheads** (Meta) vs **Athletic Shoes** (Google) at **85%** CM360 overlap, **48** duplicated conversions, **$4,200/month**. Pacing should flag Meta Sneakerheads (~+54%) and YouTube Sports Highlights (~−31%).

To reset the CSVs:

```bash
python mock_csv_generator.py
```

## Data contracts

**`data/meta.csv`** — `campaign_id`, `ad_set_name`, `audience_description`, `spend`, `conversions`

**`data/gads.csv`** — `campaign_id`, `ad_group_name`, `audience_description`, `spend`, `conversions`

**`data/cm360.csv`** — `meta_audience`, `google_audience`, `overlap_percentage`, `duplicated_conversions`, `overlap_cost`

**`data/pacing.csv`** — `campaign_name`, `daily_spend_actual`, `daily_spend_plan`, `pct_deviation`

CM360 rows are matched to Meta `ad_set_name` and Google `ad_group_name`. A pair is reported only if semantic or CM360 confidence exceeds the threshold **and** a CM360 verification row exists.
