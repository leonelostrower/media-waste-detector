"""Streamlit entry point for Media QA Copilot."""

from __future__ import annotations

import io
import os
import time

import pandas as pd
import streamlit as st
from pypdf import PdfReader

import data_manager as dm
import ptc_agents as agents
import ptc_charts as charts
import ptc_narrative as narrative
import ptc_pipeline as ptc
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
      --mf-plum-50: #F7F6FE;
      --mf-text: #3C3C3E;
      --mf-muted: #787C96;
      --mf-border: rgba(0, 0, 0, 0.12);
      --mf-border-soft: rgba(0, 0, 0, 0.08);
    }
    html, body, .stApp, [class*="st-"] {
      font-family: 'Helvetica Now for Monks', Helvetica, Arial, sans-serif;
    }
    .stApp { background: #FFFFFF; color: var(--mf-text); }
    header[data-testid="stHeader"] { background: transparent; height: 0; }
    .block-container {
      max-width: 1160px;
      padding: 1.75rem 1.5rem 4rem;
    }
    h1 { font-size: 36px !important; line-height: 44px !important; letter-spacing: -0.04em !important; font-weight: 400 !important; margin: 0 0 4px !important; }
    h2 { font-size: 24px !important; line-height: 32px !important; letter-spacing: -0.04em !important; font-weight: 400 !important; margin: 0 0 4px !important; padding: 0 !important; }
    h3 { font-size: 20px !important; line-height: 28px !important; letter-spacing: -0.04em !important; font-weight: 500 !important; margin: 0 0 4px !important; padding: 0 !important; }
    p, li, label, .stMarkdown { letter-spacing: -0.01em; }

    [data-testid="stVerticalBlockBorderWrapper"] {
      border: 1px solid var(--mf-border-soft) !important;
      border-radius: 16px;
      box-shadow: 0 2px 7px rgba(0, 0, 0, 0.06);
      background: #FFFFFF;
    }
    [data-testid="stMetric"] {
      border-radius: 12px;
      border-color: var(--mf-border-soft) !important;
    }
    [data-testid="stMetricLabel"] p {
      font-size: 12px !important;
      font-weight: 500;
      color: var(--mf-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    [data-testid="stMetricValue"] { font-size: 28px; letter-spacing: -0.04em; }

    .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {
      border-radius: 12px;
      min-height: 40px;
      font-weight: 500;
      letter-spacing: -0.01em;
      transition: all 0.2s ease;
    }
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"] {
      background: var(--mf-plum);
      border-color: var(--mf-plum);
      color: #FFFFFF;
    }
    .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primaryFormSubmit"]:hover {
      background: var(--mf-plum-dark);
      border-color: var(--mf-plum-dark);
    }
    .stButton > button[kind="secondary"] {
      border-color: rgba(0, 0, 0, 0.19);
      color: var(--mf-text);
    }
    .stButton > button[kind="secondary"]:hover {
      border-color: var(--mf-plum);
      color: var(--mf-plum);
    }

    [data-baseweb="tab-list"] { gap: 28px; border-bottom: 1px solid var(--mf-border); }
    [data-baseweb="tab"] { height: 46px; padding: 0 !important; letter-spacing: -0.01em; }
    [data-baseweb="tab"][aria-selected="true"] { color: var(--mf-plum) !important; }
    [data-baseweb="tab-highlight"] { background: var(--mf-plum) !important; }

    textarea, input, [data-testid="stFileUploaderDropzone"] {
      border-radius: 12px !important;
    }
    [data-testid="stFileUploaderDropzone"] {
      background: var(--mf-plum-50);
      border: 1px dashed rgba(79, 36, 238, 0.35);
      padding: 1rem 1.25rem;
    }
    [data-testid="stAlertContainer"] { border-radius: 12px; }
    [data-testid="stAlertContainer"] p { letter-spacing: -0.01em; }

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
    }
    .mf-wordmark { font-size: 16px; font-weight: 500; letter-spacing: -0.01em; color: var(--mf-text); }
    .mf-eyebrow {
      font-size: 12px; font-weight: 500; letter-spacing: 0.08em;
      text-transform: uppercase; color: var(--mf-muted);
    }
    .mf-avatar {
      width: 40px; height: 40px;
      border-radius: 12px;
      background: var(--mf-plum-50);
      border: 1px solid rgba(79, 36, 238, 0.18);
      color: var(--mf-plum);
      display: flex; align-items: center; justify-content: center;
      font-size: 14px; font-weight: 500;
      margin-bottom: 4px;
    }
    </style>
    """
)


def initialize_state() -> None:
    st.session_state.setdefault("view", "home")
    st.session_state.setdefault("client_id", None)
    st.session_state.setdefault("analysis_result", None)
    st.session_state.setdefault("analysis_client_id", None)
    st.session_state.setdefault("ptc_report", None)
    st.session_state.setdefault("ptc_report_client_id", None)


def navigate(view: str, client_id: str | None = None) -> None:
    st.session_state.view = view
    st.session_state.client_id = client_id
    if view in {"home", "new_client"}:
        st.session_state.analysis_result = None
        st.session_state.analysis_client_id = None
        st.session_state.ptc_report = None
        st.session_state.ptc_report_client_id = None


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


def render_topbar(
    show_back: bool = False,
    back_label: str = "Volver a clientes",
    back_args: tuple = ("home",),
) -> None:
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
                back_label,
                icon=":material/arrow_back:",
                on_click=navigate,
                args=back_args,
                width="stretch",
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
        st.button(
            "Abrir workspace",
            icon=":material/arrow_forward:",
            key=f"open_{client['id']}",
            on_click=navigate,
            args=("workspace", client["id"]),
            width="stretch",
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
            "Nuevo cliente",
            icon=":material/add:",
            type="primary",
            on_click=navigate,
            args=("new_client",),
            width="stretch",
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
                icon=":material/add_business:",
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
    st.rerun()


def render_source_card(
    client: dict,
    source: str,
    title: str,
    description: str,
    required: bool = False,
) -> None:
    connected = bool(client.get("sources", {}).get(source))
    with st.container(border=True):
        if connected:
            st.badge("Conectado", icon=":material/check:", color="green")
        else:
            st.badge("Requerido" if required else "Opcional", color="orange" if required else "gray")
        st.markdown(f"**{title}**")
        st.caption(shorten(description, 72))
        if connected:
            st.metric("Entidades", len(dm.read_source(source)))
        else:
            st.space("small")
            if st.button(
                "Conectar",
                key=f"connect_{source}",
                type="primary" if required else "secondary",
                icon=":material/cable:",
                width="stretch",
            ):
                connect_source(client["id"], source, title)


def render_cm360_card(client: dict) -> None:
    """CM360 is the mandatory source and the input to the path-to-conversion
    pipeline, so it takes a real export rather than a simulated handshake."""
    export = client.get("ptc_export") or {}
    with st.container(border=True):
        if export:
            st.badge("Cargado", icon=":material/check:", color="green")
        else:
            st.badge("Requerido", color="orange")
        st.markdown("**Campaign Manager 360**")
        st.caption("Export Path to Conversion. Base del reporte y de la verificación.")

        if export:
            st.metric("Filas del export", f"{export.get('rows', 0):,}")
            st.caption(f"{shorten(export.get('filename', 'export.csv'), 40)}")
            if st.button(
                "Reemplazar export",
                key="replace_ptc",
                icon=":material/delete:",
                width="stretch",
            ):
                dm.clear_ptc_export(client["id"])
                dm.set_source_connected(client["id"], "cm360", False)
                st.session_state.ptc_report = None
                st.rerun()
            return

        uploaded = st.file_uploader(
            "Export CM360",
            type=["csv"],
            key=f"ptc_upload_{client['id']}",
            label_visibility="collapsed",
        )
        if uploaded is None:
            return
        raw = uploaded.getvalue()
        try:
            summary = inspect_export(raw)
        except Exception as error:
            st.error(f"No fue posible leer el export: {error}", icon=":material/error:")
            return
        if not summary["campaigns"] and not summary["sites"]:
            st.error(
                "El archivo no contiene interacciones de CM360.",
                icon=":material/error:",
            )
            return
        record = dm.store_ptc_export(client["id"], uploaded.name, raw)
        dm.update_client(
            client["id"], ptc_export={**record, "rows": int(summary["n_rows"])}
        )
        dm.set_source_connected(client["id"], "cm360", True)
        st.toast("Export cargado", icon=":material/check_circle:")
        st.rerun()


def render_data_sources(client: dict) -> None:
    st.space("small")
    st.subheader("Fuentes de datos")
    st.caption("CM360 es obligatorio para verificar duplicación de conversiones.")
    st.space("small")
    columns = st.columns(3, gap="medium")
    with columns[0]:
        render_cm360_card(client)
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
            st.text_area(
                "Estrategia de medios y objetivos",
                key=plan_key,
                height=260,
                placeholder="Objetivos del trimestre, lineamientos de inversión y criterios de optimización.",
            )
            if st.button(
                "Guardar contexto",
                icon=":material/save:",
                type="primary",
                disabled=not bool(st.session_state[plan_key].strip()),
            ):
                dm.update_client(client["id"], media_plan=st.session_state[plan_key].strip())
                st.toast("Contexto actualizado", icon=":material/check_circle:")
                st.rerun()
    with side:
        with st.container(border=True):
            st.markdown("**Importar documento**")
            st.caption("Formatos TXT o PDF.")
            uploaded = st.file_uploader(
                "Media plan",
                type=["txt", "pdf"],
                key=f"plan_file_{client['id']}",
                label_visibility="collapsed",
            )
            if uploaded and st.session_state.get("loaded_plan_file") != uploaded.name:
                try:
                    st.session_state[plan_key] = extract_uploaded_text(uploaded)
                    st.session_state.loaded_plan_file = uploaded.name
                    st.rerun()
                except Exception:
                    st.error("No fue posible leer el archivo.", icon=":material/error:")
        with st.container(border=True):
            saved = client.get("media_plan", "")
            st.markdown("**Estado**")
            if saved:
                st.badge("Contexto guardado", icon=":material/check:", color="green")
                st.caption(f"{len(saved.split())} palabras indexadas para recuperación semántica.")
            else:
                st.badge("Sin guardar", color="orange")
                st.caption("Guarda el contexto para habilitar el análisis.")


# ----------------------------------------------------------------------------
# Path to Conversion pipeline
# ----------------------------------------------------------------------------

CHANNEL_OPTIONS = [ptc.SEARCH, ptc.MID_FUNNEL, ptc.OTHER]


@st.cache_data(show_spinner=False)
def inspect_export(raw: bytes) -> dict:
    return ptc.inspect_export(raw)


@st.cache_data(show_spinner=False)
def propose_taxonomy(raw: bytes) -> agents.TaxonomyProposal:
    summary = inspect_export(raw)
    return agents.propose_taxonomy(
        summary["campaigns"], summary["sites"], summary["pairs"], summary["export_meta"]
    )


@st.cache_data(show_spinner=False)
def run_pipeline(raw: bytes, taxonomy_payload: dict, steady_state: pd.Timestamp | None):
    taxonomy = ptc.Taxonomy.from_dict(taxonomy_payload)
    return ptc.run_pipeline(raw, taxonomy, steady_state)


@st.cache_data(show_spinner=False)
def default_steady_state(raw: bytes, taxonomy_payload: dict) -> pd.Timestamp | None:
    taxonomy = ptc.Taxonomy.from_dict(taxonomy_payload)
    header_row = ptc.read_preamble(raw)[1]
    touches = ptc.build_touches(ptc.load_data(raw, header_row), taxonomy)
    return ptc.derive_steady_state(touches, taxonomy)


def taxonomy_from_editors(
    campaign_frame: pd.DataFrame,
    site_frame: pd.DataFrame,
    pairs: pd.DataFrame,
) -> ptc.Taxonomy:
    taxonomy = ptc.Taxonomy(
        channel_map={
            str(row["Campaña"]): str(row["Canal"]) for _, row in campaign_frame.iterrows()
        },
        platform_map={
            str(row["Site (CM360)"]): str(row["Plataforma"]).strip() or ptc.OTHER
            for _, row in site_frame.iterrows()
        },
    )
    taxonomy.platform_channel = agents.resolve_platform_channel(taxonomy, pairs)
    return taxonomy


def build_report(raw: bytes, taxonomy: ptc.Taxonomy, steady_state, language: str) -> dict:
    result = run_pipeline(raw, taxonomy.to_dict(), steady_state)
    figures, top_paths_rows, transition_matrix = charts.build_figures(result)
    sections = narrative.build_sections(result.metrics, top_paths_rows, transition_matrix)
    fact_sheet = narrative.build_fact_sheet(result.metrics)
    review = agents.rewrite_narrative(sections, fact_sheet, language=language)
    return {
        "result": result,
        "figures": figures,
        "sections": review.sections,
        "review": review,
        "fact_sheet": fact_sheet,
    }


def render_taxonomy_step(client: dict, raw: bytes, summary: dict) -> None:
    saved = ptc.Taxonomy.from_dict(client.get("ptc_taxonomy"))
    proposal_key = f"ptc_proposal_{client['id']}"

    if saved is None and proposal_key not in st.session_state:
        with st.spinner("Clasificando campañas y sites..."):
            st.session_state[proposal_key] = propose_taxonomy(raw)

    proposal = st.session_state.get(proposal_key)
    base = saved or (proposal.taxonomy if proposal else agents.heuristic_taxonomy(
        summary["campaigns"], summary["sites"]
    ))

    st.markdown("**Taxonomía del export**")
    if saved is not None:
        st.caption("Mapeo guardado para este cliente. Editable en cualquier momento.")
    elif proposal and proposal.source == "agent":
        st.caption("Propuesto por el agente a partir de los nombres de campañas y sites.")
    else:
        st.caption(
            "Propuesto por reglas de nombres. Configura GEMINI_API_KEY para que lo "
            "clasifique el agente."
        )
    if proposal and proposal.notes:
        st.caption(proposal.notes)

    campaign_column, site_column = st.columns(2, gap="medium")
    with campaign_column:
        campaign_frame = st.data_editor(
            pd.DataFrame(
                [
                    {"Campaña": campaign, "Canal": base.channel_for(campaign)}
                    for campaign in summary["campaigns"]
                ]
            ),
            hide_index=True,
            width="stretch",
            disabled=["Campaña"],
            column_config={
                "Canal": st.column_config.SelectboxColumn(options=CHANNEL_OPTIONS, required=True)
            },
            key=f"ptc_campaigns_{client['id']}",
        )
    with site_column:
        site_frame = st.data_editor(
            pd.DataFrame(
                [
                    {"Site (CM360)": site, "Plataforma": base.platform_for(site)}
                    for site in summary["sites"]
                ]
            ),
            hide_index=True,
            width="stretch",
            disabled=["Site (CM360)"],
            key=f"ptc_sites_{client['id']}",
        )

    taxonomy = taxonomy_from_editors(campaign_frame, site_frame, summary["pairs"])
    mid = taxonomy.mid_funnel_platforms
    search = taxonomy.search_platforms
    with st.container(horizontal=True, gap="small"):
        st.badge(f"Search: {', '.join(search) or 'ninguna'}", color="blue")
        st.badge(f"Mid-funnel: {', '.join(mid) or 'ninguna'}", color="violet")

    if not mid:
        st.warning(
            "Ninguna plataforma quedó clasificada como mid-funnel; el reporte no podrá "
            "comparar Search contra mid-funnel.",
            icon=":material/warning:",
        )

    st.space("small")
    default_steady = default_steady_state(raw, taxonomy.to_dict()) or summary["date_min"]
    # A touch can predate the conversion window, so the first mid-funnel touch may
    # fall before the earliest conversion in the export.
    floor = min(default_steady, summary["date_min"])
    controls = st.columns([2, 2, 3], gap="medium", vertical_alignment="bottom")
    with controls[0]:
        steady_state = st.date_input(
            "Inicio de la ventana post-activación",
            value=default_steady.date(),
            min_value=floor.date(),
            max_value=summary["date_max"].date(),
            help="Primer día con actividad mid-funnel. Las conversiones previas se "
                 "excluyen para no diluir las métricas.",
            key=f"ptc_steady_{client['id']}",
        )
    with controls[1]:
        language = st.selectbox(
            "Idioma del reporte",
            ["English", "Español"],
            key=f"ptc_language_{client['id']}",
        )
    with controls[2]:
        generate = st.button(
            "Generar reporte",
            icon=":material/auto_awesome:",
            type="primary",
            width="stretch",
            disabled=not taxonomy.platform_map,
        )

    if not generate:
        return

    dm.update_client(client["id"], ptc_taxonomy=taxonomy.to_dict())
    with st.status("Analizando el export de CM360", expanded=True) as status:
        st.write("Reconstruyendo los paths de conversión")
        report = build_report(raw, taxonomy, pd.Timestamp(steady_state), language)
        st.write("Generando gráficos")
        st.write("Redactando la narrativa con el agente")
        status.update(label="Reporte generado", state="complete", expanded=False)

    st.session_state.ptc_report = report
    st.session_state.ptc_report_client_id = client["id"]
    st.session_state.pop("ptc_prose", None)
    navigate("report", client["id"])
    st.rerun()


def render_path_to_conversion(client: dict) -> None:
    st.space("small")
    st.subheader("Path to Conversion")
    st.caption(
        "Analiza el export de CM360 y arma el reporte con narrativa lista para el cliente."
    )
    st.space("small")

    raw = dm.read_ptc_export(client)
    if raw is None:
        st.info(
            "Carga el export Path to Conversion de CM360 en la pestaña Fuentes de datos "
            "para habilitar este reporte.",
            icon=":material/upload_file:",
        )
        return

    try:
        summary = inspect_export(raw)
    except Exception as error:
        st.error(f"No fue posible leer el export: {error}", icon=":material/error:")
        return

    metrics = st.columns(4, gap="medium")
    metrics[0].metric("Conversiones", f"{summary['n_rows']:,}", border=True)
    metrics[1].metric(
        "Ventana",
        f"{summary['date_min']:%d %b} - {summary['date_max']:%d %b}",
        border=True,
    )
    metrics[2].metric("Slots de interacción", summary["slots"], border=True)
    metrics[3].metric("Sites", len(summary["sites"]), border=True)

    st.space("medium")
    with st.container(border=True):
        render_taxonomy_step(client, raw, summary)

    if st.session_state.ptc_report_client_id == client["id"] and st.session_state.ptc_report:
        st.space("small")
        st.button(
            "Ver último reporte",
            icon=":material/description:",
            on_click=navigate,
            args=("report", client["id"]),
        )


# ----------------------------------------------------------------------------
# Report screen
# ----------------------------------------------------------------------------

def prose_key(section_id: str, index: int) -> str:
    return f"ptc_prose::{section_id}::{index}"


def render_narrative_block(block: narrative.Prose, key: str, editing: bool) -> None:
    if editing:
        st.text_area(
            "Narrativa",
            value=st.session_state.get(key, block.text),
            key=key,
            height=max(140, 26 * (block.text.count("\n") + 3)),
            label_visibility="collapsed",
        )
    else:
        st.markdown(st.session_state.get(key, block.text))


def render_table_block(block: narrative.TableBlock) -> None:
    st.dataframe(
        pd.DataFrame(block.rows, columns=block.headers),
        hide_index=True,
        width="stretch",
    )
    if block.caption:
        st.caption(block.caption)


def render_report() -> None:
    client = dm.get_client(st.session_state.client_id)
    report = st.session_state.ptc_report
    if not client or not report or st.session_state.ptc_report_client_id != client["id"]:
        navigate("workspace", st.session_state.client_id)
        st.rerun()

    metrics = report["result"].metrics
    review = report["review"]

    render_topbar(
        show_back=True,
        back_label="Volver al workspace",
        back_args=("workspace", client["id"]),
    )
    st.html('<span class="mf-eyebrow">Path to Conversion</span>')
    st.title(f"{client['name']}: reporte CM360")
    st.caption(
        f"{metrics.n_conversions:,} conversiones atribuidas · "
        f"{metrics.date_min:%d %b %Y} - {metrics.date_max:%d %b %Y} · "
        f"actividad {shorten(str(metrics.activity_name), 60)}"
    )

    st.space("small")
    headline = st.columns(4, gap="medium")
    headline[0].metric(
        "Tocadas por mid-funnel", narrative.pct(metrics.pct_mf_touched), border=True
    )
    headline[1].metric("Paths mixtos", narrative.pct(metrics.pct_mixed), border=True)
    headline[2].metric(
        "Patrón clásico", narrative.pct(metrics.pct_classic), border=True
    )
    headline[3].metric(
        "Lag mediano", f"{narrative.dec(metrics.lag_median)} días", border=True
    )

    st.space("small")
    controls = st.columns([3, 2, 2], gap="medium", vertical_alignment="center")
    with controls[0]:
        with st.container(horizontal=True, gap="small"):
            if review.source == "agent":
                st.badge("Narrativa del agente", icon=":material/smart_toy:", color="green")
            else:
                st.badge("Narrativa calculada", icon=":material/functions:", color="gray")
            if review.rejected:
                st.badge(
                    f"{len(review.rejected)} bloques rechazados", color="orange"
                )
    with controls[1]:
        editing = st.toggle("Editar narrativa", key="ptc_editing")
    with controls[2]:
        approve = st.button(
            "Aprobar narrativa",
            icon=":material/check_circle:",
            type="primary",
            width="stretch",
        )

    if review.rejected:
        st.warning(
            "El agente usó cifras que no están en los datos, así que esos bloques "
            "conservan el texto calculado: "
            + "; ".join(f"{item['section']} ({item['numbers']})" for item in review.rejected),
            icon=":material/rule:",
        )
    for flag in review.flags:
        st.info(f"**{flag['section']}**: {flag['issue']}", icon=":material/flag:")

    if approve:
        approved = {}
        for section in report["sections"]:
            for index, block in enumerate(section.blocks):
                if isinstance(block, narrative.Prose):
                    key = prose_key(section.id, index)
                    approved[key] = st.session_state.get(key, block.text)
        dm.update_client(
            client["id"],
            ptc_narrative={
                "approved_at": pd.Timestamp.now().isoformat(timespec="seconds"),
                "blocks": approved,
            },
        )
        st.toast("Narrativa aprobada", icon=":material/check_circle:")

    st.space("medium")
    for section in report["sections"]:
        st.divider()
        st.subheader(section.heading)
        for index, block in enumerate(section.blocks):
            if isinstance(block, narrative.Prose):
                render_narrative_block(block, prose_key(section.id, index), editing)
            elif isinstance(block, narrative.TableBlock):
                render_table_block(block)
            elif isinstance(block, narrative.FigureBlock):
                figure = report["figures"].get(block.key)
                if figure is not None:
                    st.plotly_chart(figure, width="stretch", key=f"fig_{section.id}_{index}")
                if block.caption:
                    st.caption(block.caption)

    st.divider()
    with st.expander("Fact sheet verificado"):
        st.caption(
            "Todas las cifras calculadas del export. El agente sólo puede citar estos valores."
        )
        st.dataframe(
            pd.DataFrame(
                sorted(report["fact_sheet"].items()), columns=["Métrica", "Valor"]
            ),
            hide_index=True,
            width="stretch",
        )


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
            "Ejecutar análisis",
            icon=":material/auto_awesome:",
            type="primary",
            disabled=not ready,
            width="stretch",
        )

    with st.container(horizontal=True, gap="small"):
        st.badge(
            "CM360" if sources.get("cm360") else "CM360 pendiente",
            icon=":material/check:" if sources.get("cm360") else None,
            color="green" if sources.get("cm360") else "orange",
        )
        st.badge(
            "Red de medios" if network_connected else "Red pendiente",
            icon=":material/check:" if network_connected else None,
            color="green" if network_connected else "gray",
        )
        st.badge(
            "Contexto" if has_plan else "Contexto pendiente",
            icon=":material/check:" if has_plan else None,
            color="green" if has_plan else "gray",
        )

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

    sources_tab, report_tab, context_tab, analysis_tab = st.tabs(
        ["Fuentes de datos", "Path to Conversion", "Contexto de negocio", "QA & Insights"]
    )
    with sources_tab:
        render_data_sources(client)
    with report_tab:
        render_path_to_conversion(client)
    with context_tab:
        render_media_plan(client)
    with analysis_tab:
        render_analysis(client)


initialize_state()
if st.session_state.view == "home":
    render_home()
elif st.session_state.view == "new_client":
    render_new_client()
elif st.session_state.view == "report":
    render_report()
else:
    render_workspace()
