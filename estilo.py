"""Identidade visual da PH Consult aplicada a interface do Streamlit.

As cores vem todas de `cores.py`, que por sua vez foram tiradas da logo -- a
montanha marinho com a bandeira coral. A ideia e simples: marinho carrega o
texto e a estrutura, creme forma as superficies de apoio, e o coral aparece em
doses pequenas, do mesmo jeito que a bandeirinha aparece na logo.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

import cores

BASE_DIR = Path(__file__).resolve().parent
LOGO = BASE_DIR / "assets" / "logo-ph-consult.png"
ICONE = BASE_DIR / "assets" / "icone-ph-consult.png"

NOME_MARCA = "PH Consult"
TAGLINE = "Gestao de midias sociais"

# Fonte com fallback de sistema: se a maquina estiver sem internet, a interface
# cai para a fonte nativa do SO em vez de ficar sem estilo.
_FONTE = (
    "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif"
)


def icone_pagina() -> str | Path:
    """Icone da aba do navegador: a logo quando existe, senao um emoji."""
    return ICONE if ICONE.is_file() else ":material/insights:"


def _css() -> str:
    c = cores
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, .stApp {{ font-family: {_FONTE}; }}
    .stApp button, .stApp input, .stApp textarea, .stApp select {{
        font-family: inherit;
    }}

    /* Os icones do Streamlit sao uma fonte de ligaduras: se herdarem a fonte da
       interface, o nome do icone vaza como texto ("save", "download"...). */
    [data-testid="stIconMaterial"],
    .material-symbols-rounded,
    span[class*="material-symbols"],
    [data-testid="stExpanderToggleIcon"],
    [data-testid="stFileUploaderDropzone"] span[class*="material"] {{
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important;
        font-feature-settings: 'liga';
    }}

    /* ---------- Barra lateral: a "neve" da logo ---------- */
    [data-testid="stSidebar"] {{
        background: {c.CREME};
        border-right: 1px solid {c.CREME_BORDA};
    }}
    [data-testid="stSidebar"] * {{ color: {c.MARINHO}; }}
    [data-testid="stSidebar"] hr {{
        border-color: {c.CREME_BORDA};
        margin: 1.1rem 0;
    }}

    /* Bloco da marca no topo da barra lateral */
    .ph-marca {{
        font-weight: 700;
        font-size: 1.32rem;
        letter-spacing: .02em;
        color: {c.MARINHO};
        line-height: 1.1;
        margin-top: .1rem;
    }}
    .ph-marca span {{
        font-weight: 400;
        color: {c.TINTA_SECUNDARIA};
        margin-left: .28rem;
    }}
    .ph-tagline {{
        font-size: .76rem;
        color: {c.TINTA_SECUNDARIA};
        margin-top: .2rem;
        padding-bottom: .5rem;
        border-bottom: 2px solid {c.CORAL};
        display: inline-block;
    }}
    .ph-rotulo {{
        font-size: .72rem;
        font-weight: 600;
        letter-spacing: .09em;
        text-transform: uppercase;
        color: {c.TINTA_SECUNDARIA};
        margin: .2rem 0 .35rem 0;
    }}

    /* ---------- Titulos: regua coral, como a bandeira no cume ---------- */
    h1 {{
        color: {c.MARINHO};
        font-weight: 700;
        letter-spacing: -.02em;
        padding-bottom: .45rem;
        margin-bottom: .7rem;
        position: relative;
    }}
    h1::after {{
        content: "";
        position: absolute;
        left: 0; bottom: 0;
        width: 54px; height: 4px;
        background: {c.CORAL};
        border-radius: 3px;
    }}
    h2, h3 {{ color: {c.MARINHO}; font-weight: 600; letter-spacing: -.01em; }}

    /* ---------- Cartoes de metrica ---------- */
    [data-testid="stMetric"] {{
        background: {c.CREME};
        border: 1px solid {c.CREME_BORDA};
        border-radius: 12px;
        padding: .85rem 1rem .9rem 1rem;
        position: relative;
        overflow: hidden;
    }}
    [data-testid="stMetric"]::before {{
        content: "";
        position: absolute;
        left: 0; top: 0; bottom: 0;
        width: 3px;
        background: {c.CORAL};
    }}
    [data-testid="stMetricLabel"] p {{
        color: {c.TINTA_SECUNDARIA};
        font-size: .78rem;
        font-weight: 600;
        letter-spacing: .04em;
        text-transform: uppercase;
    }}
    [data-testid="stMetricValue"] {{
        color: {c.MARINHO};
        font-weight: 700;
        /* Cinco cartoes lado a lado: o valor acompanha a largura em vez de
           ser cortado com reticencias quando o numero tem 6 digitos. */
        font-size: clamp(1.1rem, 1.7vw, 1.75rem);
        white-space: nowrap;
    }}
    [data-testid="stMetricValue"] div {{ overflow: visible; }}

    /* ---------- Botoes ---------- */
    .stButton button[kind="primary"],
    .stFormSubmitButton button[kind="primary"],
    .stDownloadButton button[kind="primary"] {{
        background: {c.MARINHO};
        border: 1px solid {c.MARINHO};
        color: #ffffff;
        font-weight: 600;
        border-radius: 9px;
    }}
    .stButton button[kind="primary"]:hover,
    .stFormSubmitButton button[kind="primary"]:hover,
    .stDownloadButton button[kind="primary"]:hover {{
        background: {c.MARINHO_ESCURO};
        border-color: {c.MARINHO_ESCURO};
        color: #ffffff;
    }}
    /* Botao desabilitado nao pode parecer clicavel: o CSS da marca pinta o
       fundo, entao o estado desabilitado precisa ser redeclarado aqui. */
    .stButton button:disabled,
    .stFormSubmitButton button:disabled,
    .stDownloadButton button:disabled,
    .stButton button[kind="primary"]:disabled,
    .stButton button[kind="primary"]:disabled:hover {{
        background: {c.GRADE};
        border-color: {c.GRADE};
        color: {c.TINTA_SUAVE};
        cursor: not-allowed;
    }}

    .stButton button[kind="secondary"],
    .stDownloadButton button[kind="secondary"] {{
        border: 1px solid {c.CREME_BORDA};
        color: {c.MARINHO};
        border-radius: 9px;
        font-weight: 500;
    }}
    .stButton button[kind="secondary"]:hover,
    .stDownloadButton button[kind="secondary"]:hover {{
        border-color: {c.CORAL};
        color: {c.MARINHO};
    }}

    /* ---------- Formularios, tabelas e blocos ---------- */
    [data-testid="stForm"] {{
        background: #ffffff;
        border: 1px solid {c.CREME_BORDA};
        border-radius: 14px;
        padding: 1.15rem 1.2rem .5rem 1.2rem;
    }}
    [data-testid="stExpander"] details {{
        border: 1px solid {c.CREME_BORDA};
        border-radius: 11px;
        background: #ffffff;
    }}
    [data-testid="stFileUploaderDropzone"] {{
        background: {c.CREME};
        border: 1px dashed {c.CREME_BORDA};
        border-radius: 12px;
    }}
    hr {{ border-color: {c.GRADE}; }}

    /* Rodape discreto do Streamlit */
    [data-testid="stToolbar"] {{ color: {c.TINTA_SUAVE}; }}
    </style>
    """


def aplicar() -> None:
    """Injeta o CSS da marca. Chamar uma vez, logo apos `set_page_config`."""
    st.markdown(_css(), unsafe_allow_html=True)


def marca_sidebar() -> None:
    """Logo + nome da PH Consult no topo da barra lateral."""
    if LOGO.is_file():
        st.sidebar.image(str(LOGO), width=118)
    st.sidebar.markdown(
        f"<div class='ph-marca'>PH<span>CONSULT</span></div>"
        f"<div class='ph-tagline'>{TAGLINE}</div>",
        unsafe_allow_html=True,
    )


def rotulo(texto: str) -> None:
    """Rotulo de secao da barra lateral, em caixa alta e discreto."""
    st.sidebar.markdown(f"<div class='ph-rotulo'>{texto}</div>", unsafe_allow_html=True)
