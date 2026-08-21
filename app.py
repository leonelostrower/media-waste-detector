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
    labels = {"cm360": "CM360", "google_ads": "Google Ads", "meta": "Meta"}
    with st.container(border=True):
        logo_path = client.get("logo_path")
        absolute_logo = dm.ROOT / logo_path if logo_path else None
        if absolute_logo and absolute_logo.exists():
            st.image(str(absolute_logo), width=40)
        else:
            st.html(f'<div class="mf-avatar">{client_initials(client["name"])}</div>')
        st.markdown(f"**{client['name']}**")
        st.caption(shorten(client.get("description") or "Sin contexto de negocio cargado."))
        with st.container(horizontal=True, gap="small"):
            for key, label in labels.items():
                st.badge(label, color="green" if sources.get(key) else "gray")
        st.divider()
        st.button(
            "Abrir workspace →",
            key=f"open_{client['id']}",
            on_click=navigate,
            args=("workspace", client["id"]),
            use_container_width=True,
        )


def render_home() -> None:
    render_topbar()
    heading, action = st.columns([5, 2], vertical_alignment="bottom")
    with heading:
        st.html('<span class="mf-eyebrow">Portafolio</span>')
        st.title("Clientes")
        st.caption("Workspaces activos, integraciones y contexto de negocio.")
    with action:
        st.button(
            "+ Nuevo cliente",
            type="primary",
            on_click=navigate,
            args=("new_client",),
            use_container_width=True,
        )

    st.space("small")
    clients = dm.list_clients()
    if not clients:
        st.info("Todavía no hay clientes configurados.", icon=":material/domain_add:")
        return

    for row_start in range(0, len(clients), 3):
        columns = st.columns(3, gap="medium")
        for column, client in zip(columns, clients[row_start : row_start + 3]):
            with column:
                render_client_card(client)


def render_new_client() -> None:
    render_topbar(show_back=True)
    st.html('<span class="mf-eyebrow">Onboarding</span>')
    st.title("Nuevo cliente")
    st.caption("Define la identidad del workspace antes de conectar las fuentes de datos.")
    st.space("small")

    form_column, _ = st.columns([3, 2])
    with form_column:
        with st.form("new_client_form", border=True):
            name = st.text_input("Nombre del cliente", placeholder="Northstar Athletic")
            description = st.text_area(
                "Descripción breve",
                placeholder="Industria, mercados y objetivo principal de inversión.",
                height=96,
            )
            logo = st.file_uploader("Logo", type=["png", "jpg", "jpeg", "webp", "svg"])
            submitted = st.form_submit_button(
                "Crear workspace",
                type="primary",
            )
        if submitted:
            if not name.strip():
                st.error("Ingresa el nombre del cliente.", icon=":material/error:")
                return
            client = dm.create_client(name, description)
            if logo:
                dm.store_logo(client["id"], logo.name, logo.getvalue())
            navigate("workspace", client["id"])
            st.rerun()


def connect_source(client_id: str, source: str, label: str) -> None:
    with st.spinner(f"Iniciando handshake con {label} API..."):
        time.sleep(0.9)
    with st.spinner("Sincronizando entidades..."):
        time.sleep(0.9)
    with st.spinner("Descargando reportes..."):
        dm.read_source(source)
        time.sleep(0.9)
    dm.set_source_connected(client_id, source, True)
    st.toast("Conexión establecida", icon=":material/check_circle:")


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
                st.badge("Conectado", icon=":material/check:", color="green")
            else:
                st.badge("Requerido" if required else "Opcional", color="orange" if required else "gray")
            st.markdown(f"**{title}**")
            st.caption(description)
        with col2:
            if connected:
                st.metric("Entidades", len(dm.read_source(source)))
        
        if not connected:
            st.divider()
            st.button(
                "Conectar",
                key=f"connect_{source}",
                type="primary" if required else "secondary",
                use_container_width=True,
                on_click=lambda: connect_source(client["id"], source, title),
            )
        else:
            # Show available metrics when connected
            st.divider()
            st.caption("📊 **Mediciones disponibles:**")
            st.caption(metrics_map.get(source, "Datos disponibles"))


def render_data_sources(client: dict) -> None:
    st.space("small")
    title_col, action_col = st.columns([4, 1], vertical_alignment="center")
    with title_col:
        st.subheader("Fuentes de datos")
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
    
    st.caption("Campaign Manager 360 es la fuente de datos principal para el análisis.")
    st.space("small")
    
    # Show only CM360 source card
    render_source_card(
        client,
        "cm360",
        "Campaign Manager 360",
        "Verificación de conversiones, costos y análisis de solapamientos entre canales.",
        required=True,
    )


def render_media_plan(client: dict) -> None:
    st.space("small")
    st.subheader("📋 Contexto de Negocio (Opcional)")
    
    st.markdown("""
Este documento proporciona **contexto estratégico al Agente de Insights** para orientar su análisis:
- Objetivos de campaña y KPIs esperados
- Lineamientos de inversión y presupuesto
- Criterios de optimización
- Cualquier contexto relevante para interpretar los datos

El análisis de solapamientos funciona sin este documento, pero sus recomendaciones serán más precisas si cuentan con este contexto.
    """)
    st.space("small")

    plan_key = f"plan_text_{client['id']}"
    st.session_state.setdefault(plan_key, client.get("media_plan", ""))

    # Step 1: Import Media Strategy
    with st.container(border=True):
        st.markdown("**Importar Estrategia de Medios**")
        st.caption("Carga un documento TXT o PDF con tus objetivos y lineamientos.")
        uploaded = st.file_uploader(
            label="Archivo",
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
                st.error("No fue posible leer el archivo.", icon=":material/error:")
    
    st.space("small")
    
    # Step 2: Extracted objectives + Additional context
    col_main, col_status = st.columns([3, 1], gap="medium")
    
    with col_main:
        with st.container(border=True):
            st.markdown("**Objetivos y contexto extraído**")
            st.caption("Los objetivos se extraen del documento. Opcionalmente agrega comentarios adicionales.")
            st.text_area(
                "Contexto del análisis",
                value="",
                key=plan_key,
                height=220,
                placeholder="Objetivos del trimestre, lineamientos de inversión, criterios de optimización y cualquier otro contexto relevante.",
                label_visibility="collapsed",
            )
            st.space("small")
            if st.button(
                "💾 Guardar contexto",
                type="primary",
                disabled=not bool(st.session_state[plan_key].strip()),
                use_container_width=True,
            ):
                dm.update_client(client["id"], media_plan=st.session_state[plan_key].strip())
                st.toast("Contexto actualizado", icon=":material/check_circle:")
                st.rerun()
    
    with col_status:
        with st.container(border=True):
            st.markdown("**Estado**")
            saved = client.get("media_plan", "")
            if saved:
                st.badge("Guardado", icon=":material/check:", color="green")
                st.caption(f"{len(saved.split())} palabras")
            else:
                st.badge("Sin guardar", color="orange")
                st.caption("Opcional")




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
        st.caption("Cruce de audiencias, verificación en CM360 y razonamiento sobre el media plan.")
    with action:
        # If auto_run is True, don't show button and run automatically
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
            "✓ CM360" if sources.get("cm360") else "CM360 pendiente",
            color="green" if sources.get("cm360") else "orange",
        )
    with col2:
        st.badge(
            "✓ Datos cargados" if cm360_connected else "Datos pendientes",
            color="green" if cm360_connected else "gray",
        )
    with col3:
        st.badge(
            "✓ Contexto" if client.get("media_plan") else "Contexto (opcional)",
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
            st.caption("Conecta CM360 y carga los datos para habilitar el análisis.")
        return

    st.space("medium")
    
    # Get overlaps early for summary
    overlaps = result.get("overlaps", [])
    
    # Summary section FIRST
    st.subheader("📋 Executive Summary")
    
    if overlaps:
        from business_logic import get_path_mix_data, get_journey_length_data
        
        # Get additional data for a comprehensive summary
        path_mix = get_path_mix_data()
        journey_data = get_journey_length_data()
        
        # Calculate totals
        total_overlaps = len(overlaps)
        avg_overlap = sum([item.overlap_percentage for item in overlaps]) / total_overlaps
        total_duplicated = sum([item.duplicated_conversions for item in overlaps])
        total_impact = sum([item.monthly_impact for item in overlaps])
        total_conversions = path_mix["total"]
        
        # Display metrics as cards
        metric_cols = st.columns(3, gap="medium")
        with metric_cols[0]:
            st.metric("Overlap", f"{avg_overlap:.0f}%", border=True)
        with metric_cols[1]:
            st.metric("Duplicate Conversions", total_duplicated, border=True)
        with metric_cols[2]:
            st.metric("Financial Impact", f"${total_impact:,.0f}/month", border=True)
        
        st.space("small")
        
        # Summary narrative
        summary_text = f"""
**Conversion Path Analysis:**
- **Total conversions analyzed:** {total_conversions:,} documented conversions
- **Path distribution:** {path_mix['percentage'][0]:.1f}% search-only, {path_mix['percentage'][1]:.1f}% mixed paths, {path_mix['percentage'][2]:.1f}% mid-funnel-only
- **Average complexity:** {journey_data['avg_path_length'][1]:.1f} touches for mixed paths, {journey_data['avg_days_to_convert'][1]:.1f} average days to convert
- **Audience pairs with overlap:** {total_overlaps} pairs detected with confirmed duplication in CM360
- **Recommendation:** Optimize conversion paths and implement exclusions to improve efficiency
        """
        st.markdown(summary_text)
    
    # Daily platform activity chart
    st.space("medium")
    render_daily_platform_activity()

    # Path mix chart
    st.space("medium")
    render_path_mix()

    # Journey length chart
    st.space("medium")
    render_journey_length()


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
