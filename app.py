"""Streamlit entry point for Media QA Copilot."""

from __future__ import annotations

import io
import os
import time

import pandas as pd
import streamlit as st
from pypdf import PdfReader

# Fallback for st.space (added in Streamlit 1.51, we use 1.50)
if not hasattr(st, "space"):
    def _space(size="small"):
        pixels = {"small": 16, "medium": 32, "large": 64, "stretch": 16}.get(size, 16)
        if not isinstance(size, str):
            pixels = int(size)
        st.markdown(f'<div style="height:{pixels}px"></div>', unsafe_allow_html=True)
    
    st.space = _space

import data_manager as dm
from business_logic import run_copilot_analysis

try:
    secret_key = st.secrets.get("GEMINI_API_KEY")
    if secret_key and not os.getenv("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = str(secret_key)
except FileNotFoundError:
    pass

st.set_page_config(
    page_title="Media QA Copilot",
    page_icon=":material/query_stats:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.html(
    """
    <style>
    :root {
      --mf-plum: #4F24EE;
      --mf-plum-dark: #3B11D5;
      --mf-plum-light: #F7F6FE;
      --mf-text: #3C3C3E;
      --mf-text-muted: #787C96;
      --mf-border: rgba(0, 0, 0, 0.12);
      --mf-border-strong: rgba(0, 0, 0, 0.19);
      --mf-shadow-2: 0px 2px 7px 0px rgba(0, 0, 0, 0.1);
      --mf-shadow-4: 0px 4px 16px 0px rgba(0, 0, 0, 0.1);
    }
    html, body, .stApp, [class*="st-"] {
      font-family: 'Helvetica Now for Monks', Helvetica, Arial, sans-serif;
    }
    .stApp { background: #FFFFFF; color: var(--mf-text); }
    header[data-testid="stHeader"] { background: transparent; height: 0; }
    .block-container {
      max-width: 1160px;
      padding: 2rem 1.5rem 4rem;
    }
    h1 { 
      font-size: 36px !important; 
      line-height: 44px !important; 
      letter-spacing: -0.04em !important; 
      font-weight: 400 !important; 
      margin: 0 0 8px !important; 
      color: var(--mf-text) !important;
    }
    h2 { 
      font-size: 24px !important; 
      line-height: 32px !important; 
      letter-spacing: -0.04em !important; 
      font-weight: 400 !important; 
      margin: 0 0 8px !important; 
      padding: 0 !important; 
      color: var(--mf-text) !important;
    }
    h3 { 
      font-size: 20px !important; 
      line-height: 28px !important; 
      letter-spacing: -0.04em !important; 
      font-weight: 500 !important; 
      margin: 0 0 8px !important; 
      padding: 0 !important;
      color: var(--mf-text) !important;
    }
    p, li, label, .stMarkdown { 
      letter-spacing: -0.01em; 
      color: var(--mf-text);
    }
    .stCaption { color: var(--mf-text-muted) !important; }

    [data-testid="stVerticalBlockBorderWrapper"] {
      border: 1px solid rgba(0, 0, 0, 0.08) !important;
      border-radius: 16px !important;
      box-shadow: var(--mf-shadow-2) !important;
      background: #FFFFFF !important;
      padding: 24px !important;
      min-height: auto !important;
      display: flex !important;
      flex-direction: column !important;
      height: 100% !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] > div {
      display: flex !important;
      flex-direction: column !important;
    }
    [data-testid="stMetric"] {
      border-radius: 12px !important;
      border: 1px solid rgba(0, 0, 0, 0.08) !important;
      box-shadow: var(--mf-shadow-2) !important;
      padding: 16px !important;
    }
    [data-testid="stMetricLabel"] p {
      font-size: 11px !important;
      font-weight: 500;
      color: var(--mf-text-muted) !important;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 8px !important;
    }
    [data-testid="stMetricValue"] { 
      font-size: 28px !important;
      font-weight: 500 !important;
      letter-spacing: -0.04em; 
      color: var(--mf-text) !important;
    }

    .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
      border-radius: 12px !important;
      min-height: 40px !important;
      font-weight: 500 !important;
      font-size: 14px !important;
      letter-spacing: -0.01em !important;
      transition: all 0.2s ease !important;
      border: none !important;
    }
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"] {
      background: var(--mf-plum) !important;
      border: none !important;
      color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"] p, .stFormSubmitButton > button[kind="primaryFormSubmit"] p {
      color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primaryFormSubmit"]:hover {
      background: var(--mf-plum-dark) !important;
    }
    .stButton > button[kind="secondary"] {
      border: 1px solid var(--mf-border-strong) !important;
      color: var(--mf-text) !important;
      background: transparent !important;
    }
    .stButton > button[kind="secondary"]:hover {
      border-color: var(--mf-plum) !important;
      color: var(--mf-plum) !important;
    }
    .stButton > button:disabled {
      opacity: 0.5 !important;
      cursor: not-allowed !important;
    }
    .stButton {
      width: 100% !important;
    }
    .stButton > button {
      width: 100% !important;
      max-width: 100% !important;
      display: flex !important;
      justify-content: center !important;
      align-items: center !important;
    }

    [data-baseweb="tab-list"] { 
      gap: 28px !important;
      border-bottom: 1px solid var(--mf-border) !important;
      padding: 0 !important;
    }
    [data-baseweb="tab"] { 
      height: 44px !important;
      padding: 0 !important;
      letter-spacing: -0.01em !important;
      color: var(--mf-text-muted) !important;
      font-weight: 500 !important;
    }
    [data-baseweb="tab"][aria-selected="true"] { 
      color: var(--mf-plum) !important;
    }
    [data-baseweb="tab-highlight"] { 
      background: var(--mf-plum) !important;
      height: 3px !important;
    }

    textarea, input, [data-testid="stTextInputWrapper"] input {
      border-radius: 12px !important;
      border: 1px solid var(--mf-border) !important;
      background: #FFFFFF !important;
      color: var(--mf-text) !important;
      font-family: 'Helvetica Now for Monks', Helvetica, Arial, sans-serif !important;
    }
    textarea:focus, input:focus, [data-testid="stTextInputWrapper"] input:focus {
      border-color: var(--mf-plum) !important;
      box-shadow: 0 0 0 2px rgba(79, 36, 238, 0.1) !important;
    }
    
    [data-testid="stFileUploaderDropzone"] {
      background: var(--mf-plum-light) !important;
      border: 2px dashed rgba(79, 36, 238, 0.35) !important;
      border-radius: 12px !important;
      padding: 16px 20px !important;
    }
    [data-testid="stAlertContainer"] { 
      border-radius: 12px !important;
      border: 1px solid rgba(0, 0, 0, 0.08) !important;
    }
    [data-testid="stAlertContainer"] p, [data-testid="stAlertContainer"] span { 
      letter-spacing: -0.01em !important;
    }
    
    hr {
      border: none !important;
      border-top: 1px solid var(--mf-border) !important;
      margin: 12px 0 !important;
    }

    .mf-topbar {
      display: flex;
      align-items: center;
      gap: 12px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--mf-border);
      margin-bottom: 24px;
    }
    .mf-mark {
      width: 36px; height: 36px;
      border-radius: 10px;
      background: var(--mf-plum);
      color: #FFFFFF;
      display: flex; align-items: center; justify-content: center;
      font-size: 16px; font-weight: 500; letter-spacing: -0.01em;
      flex-shrink: 0;
    }
    .mf-wordmark { 
      font-size: 16px; 
      font-weight: 500; 
      letter-spacing: -0.01em; 
      color: var(--mf-text); 
      flex: 1;
    }
    .mf-eyebrow {
      font-size: 11px; 
      font-weight: 500; 
      letter-spacing: 0.08em;
      text-transform: uppercase; 
      color: var(--mf-text-muted);
      display: block;
      margin-bottom: 4px;
    }
    .mf-avatar {
      width: 40px; height: 40px;
      border-radius: 12px;
      background: var(--mf-plum-light);
      border: 1px solid rgba(79, 36, 238, 0.18);
      color: var(--mf-plum);
      display: flex; align-items: center; justify-content: center;
      font-size: 13px; 
      font-weight: 500;
      flex-shrink: 0;
    }
    </style>
    """
)


def initialize_state() -> None:
    st.session_state.setdefault("view", "home")
    st.session_state.setdefault("client_id", None)
    st.session_state.setdefault("analysis_result", None)
    st.session_state.setdefault("analysis_client_id", None)


def navigate(view: str, client_id: str | None = None) -> None:
    st.session_state.view = view
    st.session_state.client_id = client_id
    if view != "workspace":
        st.session_state.analysis_result = None
        st.session_state.analysis_client_id = None


def client_initials(name: str) -> str:
    words = [word for word in name.split() if word]
    return "".join(word[0].upper() for word in words[:2]) or "CL"


def shorten(text: str, limit: int = 88) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip(" ,.;") + "…"


def extract_uploaded_text(uploaded_file) -> str:
    raw = uploaded_file.getvalue()
    is_pdf = uploaded_file.type == "application/pdf" or uploaded_file.name.lower().endswith(".pdf")
    if is_pdf:
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    return raw.decode("utf-8", errors="replace").strip()


def render_topbar(show_back: bool = False) -> None:
    brand, action = st.columns([5, 2], vertical_alignment="center")
    with brand:
        st.html(
            '<div class="mf-topbar">'
            '<span class="mf-mark">M</span>'
            '<span class="mf-wordmark">Media QA Copilot</span>'
            "</div>"
        )
    with action:
        if show_back:
            st.button(
                "← Volver a clientes",
                on_click=navigate,
                args=("home",),
                use_container_width=True,
            )


def render_client_card(client: dict) -> None:
    sources = client.get("sources", {})
    labels = {"cm360": "CM360"}
    with st.container(border=True):
        logo_path = client.get("logo_path")
        absolute_logo = dm.ROOT / logo_path if logo_path else None
        if absolute_logo and absolute_logo.exists():
            st.image(str(absolute_logo), width=40)
        else:
            st.html(f'<div class="mf-avatar">{client_initials(client["name"])}</div>')
        st.markdown(f"**{client['name']}**")
        st.caption(shorten(client.get("description") or "No business context loaded."))
        with st.container(horizontal=True, gap="small"):
            for key, label in labels.items():
                st.badge(label, color="green" if sources.get(key) else "gray")
        st.divider()
        st.button(
            "Open workspace →",
            key=f"open_{client['id']}",
            on_click=navigate,
            args=("workspace", client["id"]),
            use_container_width=True,
        )


def render_home() -> None:
    render_topbar()
    heading, action = st.columns([5, 2], vertical_alignment="bottom")
    with heading:
        st.html('<span class="mf-eyebrow">Portfolio</span>')
        st.title("Clients")
        st.caption("Active workspaces, integrations and business context.")
    with action:
        st.button(
            "+ New Client",
            type="primary",
            on_click=navigate,
            args=("new_client",),
            use_container_width=True,
        )

    st.space("small")
    clients = dm.list_clients()
    if not clients:
        st.info("No clients configured yet.", icon=":material/domain_add:")
        return

    for row_start in range(0, len(clients), 3):
        columns = st.columns(3, gap="medium")
        for column, client in zip(columns, clients[row_start : row_start + 3]):
            with column:
                render_client_card(client)


def render_new_client() -> None:
    render_topbar(show_back=True)
    st.html('<span class="mf-eyebrow">Onboarding</span>')
    st.title("New Client")
    st.caption("Define your workspace identity before connecting data sources.")
    st.space("small")

    form_column, _ = st.columns([3, 2])
    with form_column:
        with st.form("new_client_form", border=True):
            name = st.text_input("Client Name", placeholder="Northstar Athletic")
            description = st.text_area(
                "Brief Description",
                placeholder="Industry, markets, and main investment objective.",
                height=96,
            )
            logo = st.file_uploader("Logo", type=["png", "jpg", "jpeg", "webp", "svg"])
            submitted = st.form_submit_button(
                "Create Workspace",
                type="primary",
            )
        if submitted:
            if not name.strip():
                st.error("Enter the client name.", icon=":material/error:")
                return
            client = dm.create_client(name, description)
            if logo:
                dm.store_logo(client["id"], logo.name, logo.getvalue())
            navigate("workspace", client["id"])
            st.rerun()


def connect_source(client_id: str, source: str, label: str) -> None:
    with st.spinner(f"Initiating handshake with {label} API..."):
        time.sleep(0.9)
    with st.spinner("Syncing entities..."):
        time.sleep(0.9)
    with st.spinner("Downloading reports..."):
        dm.read_source(source)
        time.sleep(0.9)
    dm.set_source_connected(client_id, source, True)
    st.toast("Connection established", icon=":material/check_circle:")


def render_source_card(
    client: dict,
    source: str,
    title: str,
    description: str,
    required: bool = False,
) -> None:
    # Define metrics for each source
    metrics_map = {
        "cm360": "Conversiones verificadas, Solapamiento entre canales",
        "google_ads": "Campañas, Grupos de anuncios, Audiencias, Conversiones",
        "meta": "Conjuntos de anuncios, Audiencias, Conversiones, Performance",
    }
    
    connected = bool(client.get("sources", {}).get(source))
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            if connected:
                st.badge("Connected", icon=":material/check:", color="green")
            else:
                st.badge("Required" if required else "Optional", color="orange" if required else "gray")
            st.markdown(f"**{title}**")
            st.caption(description)
        with col2:
            if connected:
                st.metric("Entidades", len(dm.read_source(source)))
        
        if not connected:
            st.divider()
            st.button(
                "Connect",
                key=f"connect_{source}",
                type="primary" if required else "secondary",
                use_container_width=True,
                on_click=lambda: connect_source(client["id"], source, title),
            )
        else:
            # Show available metrics when connected
            st.divider()
            st.caption("📊 **Available Metrics:**")
            st.caption(metrics_map.get(source, "Available Data"))


def render_data_sources(client: dict) -> None:
    st.space("small")
    title_col, action_col = st.columns([4, 1], vertical_alignment="center")
    with title_col:
        st.subheader("Data Sources")
    with action_col:
        # Check if CM360 is connected
        sources = client.get("sources", {})
        has_cm360 = bool(sources.get("cm360"))
        
        if st.button(
            "🚀 Get Report",
            type="primary",
            disabled=not has_cm360,
            use_container_width=True,
            key="get_insights_header",
        ):
            st.session_state.view = "analysis"
            st.rerun()
    
    st.caption("Campaign Manager 360 is the primary data source for analysis.")
    st.space("small")
    
    # Show only CM360 source card
    render_source_card(
        client,
        "cm360",
        "Campaign Manager 360",
        "Conversion verification, costs, and cross-channel overlap analysis.",
        required=True,
    )


def render_media_plan(client: dict) -> None:
    st.space("small")
    st.subheader("📋 Business Context (Optional)")
    
    st.markdown("""
This document provides **strategic context to the Insights Agent** to guide its analysis:
- Campaign objectives and expected KPIs
- Investment guidelines and budget
- Optimization criteria
- Any relevant context for interpreting data

Overlap analysis works without this document, but recommendations will be more accurate with this context.
    """)
    st.space("small")

    plan_key = f"plan_text_{client['id']}"
    st.session_state.setdefault(plan_key, client.get("media_plan", ""))

    # Step 1: Import Media Strategy
    with st.container(border=True):
        st.markdown("**Import Media Strategy**")
        st.caption("Upload a TXT or PDF document with your objectives and guidelines.")
        uploaded = st.file_uploader(
            label="File",
            type=["txt", "pdf"],
            key=f"plan_file_{client['id']}",
            label_visibility="collapsed",
            accept_multiple_files=False,
        )
        if uploaded and st.session_state.get("loaded_plan_file") != uploaded.name:
            try:
                st.session_state[plan_key] = extract_uploaded_text(uploaded)
                st.session_state.loaded_plan_file = uploaded.name
                st.rerun()
            except Exception:
                st.error("Could not read the file.", icon=":material/error:")
    
    st.space("small")
    
    # Step 2: Extracted objectives + Additional context
    col_main, col_status = st.columns([3, 1], gap="medium")
    
    with col_main:
        with st.container(border=True):
            st.markdown("**Extracted objectives and context**")
            st.caption("Objectives are extracted from the document. Optionally add additional comments.")
            st.text_area(
                "Analysis Context",
                value="",
                key=plan_key,
                height=220,
                placeholder="Quarter objectives, investment guidelines, optimization criteria, and any other relevant context.",
                label_visibility="collapsed",
            )
            st.space("small")
            if st.button(
                "💾 Save Context",
                type="primary",
                disabled=not bool(st.session_state[plan_key].strip()),
                use_container_width=True,
            ):
                dm.update_client(client["id"], media_plan=st.session_state[plan_key].strip())
                st.toast("Context updated", icon=":material/check_circle:")
                st.rerun()
    
    with col_status:
        with st.container(border=True):
            st.markdown("**Status**")
            saved = client.get("media_plan", "")
            if saved:
                st.badge("Saved", icon=":material/check:", color="green")
                st.caption(f"{len(saved.split())} words")
            else:
                st.badge("Not Saved", color="orange")
                st.caption("Optional")




def render_daily_platform_activity() -> None:
    """Render multi-series time-series chart of daily platform activity."""
    from business_logic import get_daily_platform_activity
    
    st.subheader("Daily Platform Activity")
    st.caption("Daily touches and platform engagement over the reporting period.")
    
    # Get data
    activity_data = get_daily_platform_activity()
    
    if activity_data.empty:
        st.info("No platform activity data available for this period.")
        return
    
    # Pivot data for line chart (dates as index, platforms as columns)
    chart_data = activity_data.pivot(index="date", columns="platform", values="daily_touches")
    
    # Create line chart with Streamlit
    st.line_chart(
        chart_data,
        use_container_width=True,
        height=350,
        color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"],  # Professional color palette
    )
    
    # Chart legend and info
    st.caption(
        "Hover over the chart to see exact values. "
        "Peaks and troughs indicate daily performance variation."
    )


def render_path_mix() -> None:
    """Render vertical bar chart of mid-funnel vs search path mix."""
    from business_logic import get_path_mix_data
    
    st.subheader("Search vs Mid-Funnel Path Mix")
    st.caption("Distribution of conversions by attribution path type.")
    
    # Get data
    mix_data = get_path_mix_data()
    
    # Create DataFrame for bar chart
    chart_df = pd.DataFrame({
        "Path Type": mix_data["categories"],
        "Conversions": mix_data["absolute"],
        "% of Total": mix_data["percentage"],
    })
    
    # Create two columns for dual metrics display
    col1, col2 = st.columns(2)
    
    with col1:
        path_length_df = pd.DataFrame({
            "Path Type": mix_data["categories"],
            "Conversions": mix_data["absolute"],
        }).set_index("Path Type")
        
        st.bar_chart(
            path_length_df,
            use_container_width=True,
            height=300,
            color=["#4F24EE"],
        )
        st.caption("Absolute conversions by path type")
    
    with col2:
        pct_df = pd.DataFrame({
            "Path Type": mix_data["categories"],
            "Percentage": mix_data["percentage"],
        }).set_index("Path Type")
        
        st.bar_chart(
            pct_df,
            use_container_width=True,
            height=300,
            color=["#FF7F0E"],
        )
        st.caption("Percentage of total conversions")
    
    # Display supporting metrics and interpretation
    st.space("small")
    metric_cols = st.columns(len(mix_data["categories"]))
    for idx, (category, abs_val, pct_val) in enumerate(
        zip(mix_data["categories"], mix_data["absolute"], mix_data["percentage"])
    ):
        with metric_cols[idx]:
            st.metric(
                category,
                f"{abs_val:,}",
                f"{pct_val:.1f}%",
                border=True,
            )
    
    # Display interpretation
    st.space("medium")
    st.markdown("#### Path Analysis Insights")
    st.markdown(mix_data["description"])




def render_journey_length() -> None:
    """Render conversion journey length metrics with dual bar charts and supporting table."""
    from business_logic import get_journey_length_data
    
    st.subheader("Conversion Journey Length")
    st.caption("Path complexity and time-to-conversion metrics by journey type.")
    
    # Get data
    journey_data = get_journey_length_data()
    
    # Create two columns for dual bar charts
    col1, col2 = st.columns(2)
    
    with col1:
        path_length_df = pd.DataFrame({
            "Journey Type": journey_data["groups"],
            "Avg Path Length": journey_data["avg_path_length"],
        }).set_index("Journey Type")
        
        st.bar_chart(
            path_length_df,
            use_container_width=True,
            height=300,
            color=["#4F24EE"],
        )
        st.caption("Average number of touches to conversion")
    
    with col2:
        days_to_convert_df = pd.DataFrame({
            "Journey Type": journey_data["groups"],
            "Avg Days": journey_data["avg_days_to_convert"],
        }).set_index("Journey Type")
        
        st.bar_chart(
            days_to_convert_df,
            use_container_width=True,
            height=300,
            color=["#FF7F0E"],
        )
        st.caption("Average days from first touch to conversion")
    
    # Supporting comparison table
    st.space("medium")
    st.markdown("#### Journey Comparison Table")
    
    table_df = pd.DataFrame(journey_data["table_data"])
    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Journey Type": st.column_config.TextColumn("Journey Type"),
            "Avg Path Length": st.column_config.NumberColumn("Avg Path Length", format="%.1f"),
            "Avg Days to Convert": st.column_config.NumberColumn("Avg Days to Convert", format="%.1f"),
            "Conversions": st.column_config.NumberColumn("Conversions", format="%d"),
            "Total Touches": st.column_config.NumberColumn("Total Touches", format="%d"),
        },
    )
    
    # Display interpretation
    st.space("medium")
    st.markdown("#### Journey Analysis Insights")
    st.markdown(journey_data["description"])




def render_analysis(client: dict, auto_run: bool = False) -> None:
    sources = client.get("sources", {})
    cm360_connected = bool(sources.get("cm360"))
    ready = cm360_connected

    st.space("small")
    heading, action = st.columns([5, 2], vertical_alignment="bottom")
    with heading:
        st.subheader("Path to Conversion Report")
        st.caption("Comprehensive conversion path analysis and attribution insights.")
    with action:
        if auto_run:
            run_analysis = True
        else:
            run_analysis = st.button(
                "✨ Get Report",
                type="primary",
                disabled=not ready,
                use_container_width=True,
            )

    st.divider()
    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        st.badge(
            "✓ CM360" if sources.get("cm360") else "CM360 pending",
            color="green" if sources.get("cm360") else "orange",
        )
    with col2:
        st.badge(
            "✓ Data loaded" if cm360_connected else "Data pending",
            color="green" if cm360_connected else "gray",
        )
    with col3:
        st.badge(
            "✓ Context" if client.get("media_plan") else "Context (optional)",
            color="green" if client.get("media_plan") else "gray",
        )
    st.space("small")

    if run_analysis:
        result = run_copilot_analysis(client["media_plan"])
        st.session_state.analysis_result = result
        st.session_state.analysis_client_id = client["id"]

    result = (
        st.session_state.analysis_result
        if st.session_state.analysis_client_id == client["id"]
        else None
    )
    if not result:
        st.space("small")
        if not ready:
            st.caption("Connect CM360 and load data to enable analysis.")
        return

    st.space("medium")
    
    # ==================== SECTION 1: EXECUTIVE SUMMARY ====================
    from business_logic import (
        get_executive_summary_data, get_methodology_data, get_top_converting_paths_data,
        get_platform_transition_data, get_platform_breakdown_data, 
        get_first_last_touch_data, get_funnel_velocity_data, get_conclusions_data
    )
    
    exec_summary = get_executive_summary_data()
    st.subheader("1. Executive Summary")
    st.markdown(exec_summary["introductory_paragraph"])
    
    st.markdown("**Key Findings:**")
    for finding in exec_summary["key_findings"]:
        st.markdown(f"- {finding}")
    
    kpis = exec_summary["kpis"]
    kpi_cols = st.columns(5, gap="medium")
    with kpi_cols[0]:
        st.metric("Attributed Conversions", f"{kpis['attributed_conversions']:,}", border=True)
    with kpi_cols[1]:
        st.metric("Mid-Funnel Touched", f"{kpis['mid_funnel_touched_pct']:.1f}%", border=True)
    with kpi_cols[2]:
        st.metric("Search-Only", f"{kpis['search_only_pct']:.1f}%", border=True)
    with kpi_cols[3]:
        st.metric("Mixed Paths", f"{kpis['mixed_paths_pct']:.1f}%", border=True)
    with kpi_cols[4]:
        st.metric("Median Conversion Lag", f"{kpis['median_conversion_lag_days']:.1f}d", border=True)
    
    st.text_area("Summary (Editable)", value=exec_summary["editable_summary"], height=80, label_visibility="collapsed")
    
    # ==================== SECTION 2: METHODOLOGY & DATA NOTES ====================
    st.space("medium")
    st.subheader("2. Methodology & Data Notes")
    
    methodology = get_methodology_data()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Data Source:** {methodology['data_source']}")
        st.markdown(f"**Analysed Period:** {methodology['analysed_period']}")
    with col2:
        st.markdown(f"**Attribution Coverage:** {methodology['attribution_coverage']}")
        st.markdown(f"**Classification:** {methodology['classification_methodology']}")
    with col3:
        st.markdown(f"**Lookback Window:** {methodology['lookback_window']}")
    
    st.markdown("**📋 Assumptions:**")
    for assumption in methodology["assumptions"]:
        st.markdown(f"• {assumption}")
    
    st.markdown("**⚠️ Limitations:**")
    for limitation in methodology["limitations"]:
        st.markdown(f"• {limitation}")
    
    st.markdown("**🚨 Warnings:**")
    for warning in methodology["warnings"]:
        st.markdown(f"• {warning}")
    
    # ==================== SECTION 3: DAILY PLATFORM ACTIVITY ====================
    st.space("medium")
    render_daily_platform_activity()
    
    # ==================== SECTION 4: MID-FUNNEL VS SEARCH PATH MIX ====================
    st.space("medium")
    render_path_mix()
    
    # ==================== SECTION 5: TOP CONVERTING PATHS ====================
    st.space("medium")
    st.subheader("5. Top Converting Paths")
    
    paths_data = get_top_converting_paths_data()
    st.markdown("**Most Common Conversion Journeys:**")
    
    # Display paths in rows of 3 for better responsiveness
    for i in range(0, len(paths_data["paths"]), 3):
        path_cols = st.columns(3, gap="medium")
        for j, col in enumerate(path_cols):
            if i + j < len(paths_data["paths"]):
                path_info = paths_data["paths"][i + j]
                with col:
                    st.metric(path_info["path"], f"{path_info['percentage']:.1f}%", border=True)
    
    st.markdown("**📊 Detailed Path Table:**")
    path_df = pd.DataFrame(paths_data["table_data"])
    st.dataframe(path_df, use_container_width=True, hide_index=True)
    
    st.text_area("Path Insights (Editable)", value=paths_data["editable_insights"], height=80, label_visibility="collapsed")
    
    # ==================== SECTION 6: PLATFORM TRANSITION FLOW ====================
    st.space("medium")
    st.subheader("6. Platform Transition Flow")
    
    transition_data = get_platform_transition_data()
    transition_df = pd.DataFrame(
        transition_data["transition_matrix"],
        index=transition_data["platforms"],
        columns=transition_data["platforms"]
    )
    
    st.markdown("**Transition Probability Heatmap (Row → Column):**")
    # Format as percentages
    transition_df_display = transition_df.applymap(lambda x: f"{x:.0%}")
    st.dataframe(transition_df_display, use_container_width=True)
    
    st.text_area("Transition Insights (Editable)", value=transition_data["editable_insights"], height=80, label_visibility="collapsed")
    
    # ==================== SECTION 7: CONVERSION JOURNEY LENGTH ====================
    st.space("medium")
    render_journey_length()
    
    # ==================== SECTION 8: PLATFORM BREAKDOWN & PATH POSITION ====================
    st.space("medium")
    st.subheader("8. Platform Breakdown & Path Position")
    
    platform_data = get_platform_breakdown_data()
    platform_df = pd.DataFrame(platform_data["platform_table"])
    st.markdown("**Platform Performance Summary:**")
    st.dataframe(platform_df, use_container_width=True, hide_index=True)
    
    st.markdown("**Path Position Distribution (%):**")
    position_df = pd.DataFrame(platform_data["path_position_data"]).T
    st.bar_chart(position_df, use_container_width=True, height=300)
    
    # ==================== SECTION 9: FIRST TOUCH → CONVERTING TOUCH ====================
    st.space("medium")
    st.subheader("9. First Touch → Converting Touch")
    
    flow_data = get_first_last_touch_data()
    st.markdown("**Conversion Flow Volume (First Touch → Converting Touch):**")
    flow_df = pd.DataFrame(flow_data["first_touch_flows"])
    flow_summary = flow_df.groupby("from")["conversions"].sum().sort_values(ascending=False)
    st.bar_chart(flow_summary, use_container_width=True, height=300)
    
    # ==================== SECTION 10: FUNNEL VELOCITY ====================
    st.space("medium")
    st.subheader("10. Funnel Velocity")
    
    velocity_data = get_funnel_velocity_data()
    st.markdown("**Days to Conversion Distribution:**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Median Days", f"{velocity_data['median_days']:.1f}d", border=True)
    with col2:
        st.metric("Mean Days", f"{velocity_data['mean_days']:.1f}d", border=True)
    with col3:
        st.metric("Sample Size", f"{velocity_data['sample_size']:,}", border=True)
    
    velocity_df = pd.DataFrame({
        "Days": velocity_data["histogram_data"]["bins"],
        "Conversions": velocity_data["histogram_data"]["counts"]
    })
    st.bar_chart(velocity_df.set_index("Days"), use_container_width=True, height=300)
    
    st.text_area("Velocity Insights (Editable)", value=velocity_data["editable_interpretation"], height=80, label_visibility="collapsed")
    
    # ==================== SECTION 11: CONCLUSIONS & RECOMMENDATIONS ====================
    st.space("medium")
    st.subheader("11. Conclusions & Recommendations")
    
    conclusions_data = get_conclusions_data()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Conclusions:**")
        for conclusion in conclusions_data["conclusions"]:
            st.markdown(f"• {conclusion}")
    
    with col2:
        st.markdown("**Recommendations:**")
        for recommendation in conclusions_data["recommendations"]:
            st.markdown(f"• {recommendation}")
    
    with col3:
        st.markdown("**Limitations:**")
        for limitation in conclusions_data["limitations"]:
            st.markdown(f"• {limitation}")


def render_workspace() -> None:
    client = dm.get_client(st.session_state.client_id)
    if not client:
        navigate("home")
        st.rerun()

    render_topbar(show_back=True)
    st.html('<span class="mf-eyebrow">Workspace</span>')
    st.title(client["name"])
    if client.get("description"):
        st.caption(client["description"])

    # Show data sources and context
    render_data_sources(client)
    st.space("medium")
    render_media_plan(client)


def render_insights_analysis() -> None:
    """Dedicated page for Path to Conversion Report - Professional Report Review Interface"""
    client = dm.get_client(st.session_state.client_id)
    if not client:
        navigate("home")
        st.rerun()

    render_topbar(show_back=True)
    
    # Header with metadata
    st.html('<span class="mf-eyebrow">Report</span>')
    st.title(client["name"])
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption("Path to Conversion Report — Media Waste Detection Analysis")
    
    st.divider()
    
    # Show the analysis section with auto-run enabled
    render_analysis(client, auto_run=True)


initialize_state()
if st.session_state.view == "home":
    render_home()
elif st.session_state.view == "new_client":
    render_new_client()
elif st.session_state.view == "analysis":
    render_insights_analysis()
else:
    render_workspace()
