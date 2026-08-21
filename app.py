"""Streamlit entry point for Media QA Copilot."""

from __future__ import annotations

import io
import os
import time

import pandas as pd
import streamlit as st
from pypdf import PdfReader

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
        if source == "cm360":
            dm.read_source("pacing")
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
    connected = bool(client.get("sources", {}).get(source))
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            if connected:
                st.badge("Conectado", icon=":material/check:", color="green")
            else:
                st.badge("Requerido" if required else "Opcional", color="orange" if required else "gray")
            st.markdown(f"**{title}**")
            st.caption(shorten(description, 72))
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


def render_data_sources(client: dict) -> None:
    st.space("small")
    st.subheader("Fuentes de datos")
    st.caption("CM360 es obligatorio para verificar duplicación de conversiones.")
    st.space("small")
    columns = st.columns(3, gap="medium")
    with columns[0]:
        render_source_card(
            client,
            "cm360",
            "Campaign Manager 360",
            "Verificación independiente de conversiones y costos.",
            required=True,
        )
    with columns[1]:
        render_source_card(
            client,
            "google_ads",
            "Google Ads",
            "Campañas, grupos de anuncios y audiencias.",
        )
    with columns[2]:
        render_source_card(
            client,
            "meta",
            "Meta Ads",
            "Conjuntos de anuncios y performance por audiencia.",
        )


def render_media_plan(client: dict) -> None:
    st.space("small")
    st.subheader("Contexto de negocio")
    st.caption("Estrategia de medios y objetivos que alimentan el razonamiento del copiloto.")
    st.space("small")

    plan_key = f"plan_text_{client['id']}"
    st.session_state.setdefault(plan_key, client.get("media_plan", ""))

    editor, side = st.columns([3, 2], gap="medium")
    with editor:
        with st.container(border=True):
            st.markdown("**Estrategia de medios y objetivos**")
            st.caption("Pega el plan o importa un documento.")
            st.text_area(
                "Plan",
                key=plan_key,
                height=220,
                placeholder="Objetivos del trimestre, lineamientos de inversión y criterios de optimización.",
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
    with side:
        with st.container(border=True):
            st.markdown("**Importar documento**")
            st.caption("TXT o PDF")
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
        with st.container(border=True):
            saved = client.get("media_plan", "")
            st.markdown("**Estado**")
            if saved:
                st.badge("Guardado", icon=":material/check:", color="green")
                st.caption(f"{len(saved.split())} palabras")
            else:
                st.badge("Sin guardar", color="orange")
                st.caption("Habilita análisis")


def render_alert(alert: dict) -> None:
    columns = st.columns(3, gap="medium")
    with columns[0]:
        st.metric("Solapamiento", f"{alert['confidence']:.0f}%", border=True)
    with columns[1]:
        st.metric("Conversiones duplicadas", alert["duplicated_conversions"], border=True)
    with columns[2]:
        st.metric("Impacto financiero", f"${alert['monthly_impact']:,.0f}/mes", border=True)

    st.space("small")
    st.warning(
        f"""🚨 ALERTA DE ALTA CONFIANZA
- Solapamiento detectado: {alert['confidence']:.0f}%
- Verificación CM360: {alert['duplicated_conversions']} conversiones duplicadas confirmadas.
- Impacto financiero: ${alert['monthly_impact']:,.0f}/mes
- Contexto Estratégico: {alert['strategic_context']}
- Acción Recomendada: {alert['recommended_action']}""",
        icon=":material/warning:",
    )


def render_overlap_table(overlaps: list) -> None:
    frame = pd.DataFrame(
        [
            {
                "Audiencia Meta": item.meta_audience,
                "Audiencia Google": item.google_audience,
                "Similitud semántica": item.semantic_similarity,
                "Solapamiento CM360": item.overlap_percentage / 100,
                "Conversiones duplicadas": item.duplicated_conversions,
                "Impacto mensual": item.monthly_impact,
            }
            for item in overlaps
        ]
    )
    st.dataframe(
        frame,
        hide_index=True,
        width="stretch",
        column_config={
            "Similitud semántica": st.column_config.NumberColumn(format="%.2f"),
            "Solapamiento CM360": st.column_config.ProgressColumn(
                format="percent", min_value=0, max_value=1
            ),
            "Impacto mensual": st.column_config.NumberColumn(format="dollar"),
        },
    )


def render_analysis(client: dict) -> None:
    sources = client.get("sources", {})
    network_connected = bool(sources.get("google_ads") or sources.get("meta"))
    has_plan = bool(client.get("media_plan"))
    ready = bool(sources.get("cm360")) and network_connected and has_plan

    st.space("small")
    heading, action = st.columns([5, 2], vertical_alignment="bottom")
    with heading:
        st.subheader("QA & Insights Engine")
        st.caption("Cruce de audiencias, verificación en CM360 y razonamiento sobre el media plan.")
    with action:
        run_analysis = st.button(
            "✨ Ejecutar análisis",
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
            "✓ Red de medios" if network_connected else "Red pendiente",
            color="green" if network_connected else "gray",
        )
    with col3:
        st.badge(
            "✓ Contexto" if has_plan else "Contexto pendiente",
            color="green" if has_plan else "gray",
        )
    st.space("small")

    if run_analysis:
        with st.status("Analizando inversión cross-platform", expanded=True) as status:
            st.write("Comparando taxonomías de audiencia")
            result = run_copilot_analysis(client["media_plan"])
            st.write("Validando conversiones con CM360")
            st.write("Contrastando hallazgos con el media plan")
            status.update(label="Análisis completado", state="complete", expanded=False)
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
            st.caption("Conecta CM360, una red de medios y guarda el contexto para habilitar el análisis.")
        return

    st.space("medium")
    alert = result.get("alert")
    if alert:
        render_alert(alert)
    else:
        st.success(
            "No se detectaron solapamientos por encima del umbral.",
            icon=":material/check_circle:",
        )

    pacing = result.get("pacing", [])
    if pacing:
        st.space("medium")
        st.subheader("Desvíos de pacing")
        columns = st.columns(min(len(pacing), 3), gap="medium")
        for column, finding in zip(columns, pacing):
            with column:
                st.metric(
                    shorten(finding.campaign_name, 34),
                    f"${finding.actual:,.0f}/día",
                    f"{finding.deviation:+.1f}% vs. plan",
                    delta_color="inverse",
                    border=True,
                )

    overlaps = result.get("overlaps", [])
    if overlaps:
        st.space("medium")
        st.subheader("Detalle de audiencias")
        render_overlap_table(overlaps)


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

    sources_tab, context_tab, analysis_tab = st.tabs(
        ["Fuentes de datos", "Contexto de negocio", "QA & Insights"]
    )
    with sources_tab:
        render_data_sources(client)
    with context_tab:
        render_media_plan(client)
    with analysis_tab:
        render_analysis(client)


initialize_state()
if st.session_state.view == "home":
    render_home()
elif st.session_state.view == "new_client":
    render_new_client()
else:
    render_workspace()
