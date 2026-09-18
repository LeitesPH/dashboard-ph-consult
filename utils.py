"""Camada de dados e integracoes do dashboard.

Tudo e local: cada cliente vive em `clientes/<slug>/` com tres itens --
o PDF de estrategia, o `config.json` (nome de exibicao + cores da marca) e o
`metricas.csv` (uma linha por semana).
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader

import cores

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CLIENTES_DIR = BASE_DIR / "clientes"

MODELO_PADRAO = "claude-opus-5"

COLUNAS_METRICAS = [
    "data_registro",
    "mes_referencia",
    "semana",
    "alcance",
    "visualizacoes",
    "interacoes",
    "cliques_link",
    "novos_seguidores",
]
COLUNAS_NUMERICAS = [
    "alcance",
    "visualizacoes",
    "interacoes",
    "cliques_link",
    "novos_seguidores",
]
ROTULOS_METRICAS = {
    "alcance": "Alcance",
    "visualizacoes": "Visualizacoes",
    "interacoes": "Interacoes",
    "cliques_link": "Cliques no link",
    "novos_seguidores": "Novos seguidores",
}

MESES = [
    "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


# ---------------------------------------------------------------------------
# Estrutura de pastas
# ---------------------------------------------------------------------------
def garantir_estrutura() -> None:
    CLIENTES_DIR.mkdir(parents=True, exist_ok=True)


def slug(nome: str) -> str:
    """Nome de pasta seguro, sem acentos nem separadores de caminho."""
    normalizado = unicodedata.normalize("NFKD", nome)
    sem_acento = "".join(c for c in normalizado if not unicodedata.combining(c))
    limpo = re.sub(r"[^A-Za-z0-9]+", "-", sem_acento).strip("-").lower()
    return limpo[:60]


def pasta_cliente(cliente: str) -> Path:
    """Pasta do cliente, garantindo que o caminho nao escape de `clientes/`."""
    destino = (CLIENTES_DIR / cliente).resolve()
    if destino.parent != CLIENTES_DIR.resolve():
        raise ValueError(f"Cliente invalido: {cliente!r}")
    return destino


def listar_clientes() -> list[str]:
    """Slugs dos clientes cadastrados, em ordem alfabetica pelo nome exibido."""
    garantir_estrutura()
    pastas = [p.name for p in CLIENTES_DIR.iterdir() if p.is_dir()]
    return sorted(pastas, key=lambda c: nome_exibicao(c).lower())


def nome_exibicao(cliente: str) -> str:
    """Nome que o usuario digitou no cadastro (cai no slug se faltar config)."""
    return carregar_config(cliente).get("nome", cliente)


# ---------------------------------------------------------------------------
# config.json
# ---------------------------------------------------------------------------
def caminho_config(cliente: str) -> Path:
    return pasta_cliente(cliente) / "config.json"


def carregar_config(cliente: str) -> dict:
    """Le o `config.json`. Nunca levanta excecao: devolve padroes se faltar."""
    padrao = {
        "nome": cliente,
        "cor_primaria": cores.COR_PRIMARIA_PADRAO,
        "cor_secundaria": cores.COR_SECUNDARIA_PADRAO,
        "arquivo_estrategia": "",
        "criado_em": "",
    }
    try:
        with caminho_config(cliente).open(encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, ValueError):
        return padrao

    if not isinstance(dados, dict):
        return padrao

    config = {**padrao, **dados}
    config["cor_primaria"] = cores.normalizar_hex(
        config.get("cor_primaria"), cores.COR_PRIMARIA_PADRAO
    )
    config["cor_secundaria"] = cores.normalizar_hex(
        config.get("cor_secundaria"), cores.COR_SECUNDARIA_PADRAO
    )
    return config


def salvar_config(cliente: str, config: dict) -> None:
    caminho = caminho_config(cliente)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump(config, arquivo, ensure_ascii=False, indent=2)


def criar_cliente(
    nome: str,
    arquivo_pdf,
    cor_primaria: str,
    cor_secundaria: str,
) -> str:
    """Cria `clientes/<slug>/` com o PDF, o `config.json` e o `metricas.csv`.

    Devolve o slug criado. Levanta `ValueError` se o nome for invalido ou se o
    cliente ja existir.
    """
    garantir_estrutura()
    identificador = slug(nome)
    if not identificador:
        raise ValueError("Informe um nome de cliente com letras ou numeros.")

    destino = pasta_cliente(identificador)
    if destino.exists():
        raise ValueError(f"Ja existe um cliente com o nome '{nome}'.")

    destino.mkdir(parents=True)
    nome_arquivo = ""
    if arquivo_pdf is not None:
        nome_arquivo = _nome_arquivo_seguro(arquivo_pdf.name)
        (destino / nome_arquivo).write_bytes(arquivo_pdf.getvalue())

    salvar_config(
        identificador,
        {
            "nome": nome.strip(),
            "cor_primaria": cores.normalizar_hex(cor_primaria, cores.COR_PRIMARIA_PADRAO),
            "cor_secundaria": cores.normalizar_hex(cor_secundaria, cores.COR_SECUNDARIA_PADRAO),
            "arquivo_estrategia": nome_arquivo,
            "criado_em": datetime.now().isoformat(timespec="seconds"),
        },
    )
    _criar_csv_vazio(identificador)
    return identificador


def _nome_arquivo_seguro(nome: str) -> str:
    base = Path(nome).name
    limpo = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._") or "estrategia.pdf"
    if not limpo.lower().endswith(".pdf"):
        limpo += ".pdf"
    return limpo


# ---------------------------------------------------------------------------
# PDF de estrategia
# ---------------------------------------------------------------------------
def caminho_pdf(cliente: str) -> Path | None:
    """Caminho do PDF de estrategia do cliente, ou `None` se nao houver."""
    config = carregar_config(cliente)
    pasta = pasta_cliente(cliente)

    indicado = config.get("arquivo_estrategia") or ""
    if indicado:
        candidato = pasta / Path(indicado).name
        if candidato.is_file():
            return candidato

    # Fallback: o PDF pode ter sido colocado na pasta manualmente.
    pdfs = sorted(pasta.glob("*.pdf"))
    return pdfs[0] if pdfs else None


def substituir_pdf(cliente: str, arquivo_pdf) -> str:
    """Troca o PDF de estrategia do cliente e atualiza o `config.json`."""
    pasta = pasta_cliente(cliente)
    anterior = caminho_pdf(cliente)
    nome_arquivo = _nome_arquivo_seguro(arquivo_pdf.name)
    (pasta / nome_arquivo).write_bytes(arquivo_pdf.getvalue())

    if anterior is not None and anterior.name != nome_arquivo:
        anterior.unlink(missing_ok=True)

    config = carregar_config(cliente)
    config["arquivo_estrategia"] = nome_arquivo
    salvar_config(cliente, config)
    return nome_arquivo


@st.cache_data(show_spinner=False)
def _extrair_texto(caminho: str, assinatura: tuple[int, float]) -> str:
    """Extrai o texto do PDF. `assinatura` (tamanho, mtime) invalida o cache."""
    del assinatura  # usado apenas como chave de cache
    leitor = PdfReader(caminho)
    paginas = []
    for pagina in leitor.pages:
        try:
            paginas.append(pagina.extract_text() or "")
        except Exception:  # noqa: BLE001 - pagina corrompida nao derruba o resto
            paginas.append("")
    return "\n\n".join(p.strip() for p in paginas if p.strip()).strip()


def extrair_texto_pdf(cliente: str) -> str:
    """Texto completo do PDF de estrategia do cliente ('' se nao houver)."""
    caminho = caminho_pdf(cliente)
    if caminho is None:
        return ""
    stat = caminho.stat()
    return _extrair_texto(str(caminho), (stat.st_size, stat.st_mtime))


# ---------------------------------------------------------------------------
# metricas.csv
# ---------------------------------------------------------------------------
def caminho_metricas(cliente: str) -> Path:
    return pasta_cliente(cliente) / "metricas.csv"


def _criar_csv_vazio(cliente: str) -> None:
    caminho = caminho_metricas(cliente)
    if not caminho.exists():
        pd.DataFrame(columns=COLUNAS_METRICAS).to_csv(caminho, index=False)


def carregar_metricas(cliente: str) -> pd.DataFrame:
    """Le o `metricas.csv` do cliente, ja tipado e ordenado por mes/semana."""
    caminho = caminho_metricas(cliente)
    if not caminho.exists():
        return pd.DataFrame(columns=COLUNAS_METRICAS)

    try:
        df = pd.read_csv(caminho, dtype={"mes_referencia": str})
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=COLUNAS_METRICAS)

    for coluna in COLUNAS_METRICAS:
        if coluna not in df.columns:
            df[coluna] = pd.NA

    df = df[COLUNAS_METRICAS].copy()
    df["mes_referencia"] = df["mes_referencia"].astype(str).str.strip()
    df["semana"] = pd.to_numeric(df["semana"], errors="coerce").astype("Int64")
    for coluna in COLUNAS_NUMERICAS:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0).astype(int)

    df = df.dropna(subset=["semana"])
    df = df[df["mes_referencia"].str.match(r"^\d{4}-\d{2}$", na=False)]
    return df.sort_values(["mes_referencia", "semana"]).reset_index(drop=True)


def salvar_metrica(cliente: str, registro: dict, substituir: bool = False) -> bool:
    """Grava uma semana no `metricas.csv` (append).

    Com `substituir=True`, uma semana ja registrada no mesmo mes e sobrescrita.
    Devolve `False` (sem gravar) quando a semana ja existe e `substituir` e falso.
    """
    df = carregar_metricas(cliente)
    duplicada = (
        not df.empty
        and (
            (df["mes_referencia"] == registro["mes_referencia"])
            & (df["semana"] == registro["semana"])
        ).any()
    )

    if duplicada:
        if not substituir:
            return False
        df = df[
            ~(
                (df["mes_referencia"] == registro["mes_referencia"])
                & (df["semana"] == registro["semana"])
            )
        ]

    linha = pd.DataFrame([{**registro, "data_registro": datetime.now().isoformat(timespec="seconds")}])
    atualizado = pd.concat([df, linha], ignore_index=True)[COLUNAS_METRICAS]
    atualizado = atualizado.sort_values(["mes_referencia", "semana"])
    atualizado.to_csv(caminho_metricas(cliente), index=False)
    return True


def excluir_metrica(cliente: str, mes_referencia: str, semana: int) -> bool:
    """Remove uma semana do `metricas.csv`. Devolve se algo foi removido."""
    df = carregar_metricas(cliente)
    if df.empty:
        return False
    mantidas = df[~((df["mes_referencia"] == mes_referencia) & (df["semana"] == semana))]
    if len(mantidas) == len(df):
        return False
    mantidas.to_csv(caminho_metricas(cliente), index=False)
    return True


def rotulo_mes(mes_referencia: str) -> str:
    """Converte '2026-09' em 'Setembro/2026'."""
    try:
        ano, mes = mes_referencia.split("-")
        return f"{MESES[int(mes) - 1]}/{ano}"
    except (ValueError, IndexError):
        return mes_referencia


def chave_mes(mes: str, ano: int) -> str:
    """Converte ('Setembro', 2026) em '2026-09'."""
    return f"{ano:04d}-{MESES.index(mes) + 1:02d}"


# ---------------------------------------------------------------------------
# Chave da API
# ---------------------------------------------------------------------------
def resolver_api_key() -> str:
    """Chave da Anthropic: primeiro a digitada na sidebar, depois o ambiente/.env."""
    da_sessao = st.session_state.get("api_key_manual", "")
    if isinstance(da_sessao, str) and da_sessao.strip():
        return da_sessao.strip()
    return (os.getenv("ANTHROPIC_API_KEY") or "").strip()


def origem_api_key() -> str:
    """De onde veio a chave em uso: 'sessao', 'ambiente' ou 'ausente'."""
    if str(st.session_state.get("api_key_manual", "")).strip():
        return "sessao"
    if (os.getenv("ANTHROPIC_API_KEY") or "").strip():
        return "ambiente"
    return "ausente"
