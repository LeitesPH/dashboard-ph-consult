"""Graficos do relatorio.

REGRA CENTRAL: todo grafico e pintado com a Cor Primaria e a Cor Secundaria do
`config.json` do cliente ativo -- nenhuma paleta generica do Plotly aparece aqui.

As demais decisoes de leitura seguem o mesmo padrao em todos os graficos:
um unico eixo por grafico (nunca dois eixos y), grade recessiva, legenda sempre
que houver duas series, rotulo direto nas barras (a identidade nao depende so da
cor) e hover ativo.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

import cores
import utils

SUPERFICIE = "#ffffff"
FONTE = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"


class Tema:
    """Cores da marca do cliente ativo, aplicadas a todos os graficos."""

    def __init__(self, config: dict):
        self.primaria = cores.normalizar_hex(
            config.get("cor_primaria"), cores.COR_PRIMARIA_PADRAO
        )
        self.secundaria = cores.normalizar_hex(
            config.get("cor_secundaria"), cores.COR_SECUNDARIA_PADRAO
        )

    @property
    def sequencia(self) -> list[str]:
        return [self.primaria, self.secundaria]


def _aplicar_tema(fig: go.Figure, titulo: str, titulo_y: str, com_legenda: bool) -> go.Figure:
    fig.update_layout(
        title={
            "text": titulo,
            "font": {"size": 17, "color": cores.TINTA_PRIMARIA, "family": FONTE},
            "x": 0,
            "xanchor": "left",
            "pad": {"b": 12},
        },
        font={"family": FONTE, "color": cores.TINTA_SECUNDARIA, "size": 13},
        paper_bgcolor=SUPERFICIE,
        plot_bgcolor=SUPERFICIE,
        margin={"l": 8, "r": 8, "t": 64, "b": 8},
        separators=",.",  # 1.234,5 -- padrao pt-BR
        hoverlabel={"font": {"family": FONTE, "size": 13}, "bgcolor": SUPERFICIE},
        showlegend=com_legenda,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.0,
            "xanchor": "left",
            "x": 0,
            "title": {"text": ""},
            "font": {"color": cores.TINTA_SECUNDARIA},
        },
        bargap=0.34,
        bargroupgap=0.08,  # respiro entre barras vizinhas
    )
    fig.update_xaxes(
        showgrid=False,
        showline=False,
        zeroline=False,
        ticks="",
        title_text="",
        tickfont={"color": cores.TINTA_SECUNDARIA},
    )
    fig.update_yaxes(
        title_text=titulo_y,
        title_font={"color": cores.TINTA_SUAVE, "size": 12},
        gridcolor=cores.GRADE,
        griddash="dot",
        showline=False,
        zeroline=True,
        zerolinecolor=cores.GRADE,
        ticks="",
        tickfont={"color": cores.TINTA_SUAVE},
        rangemode="tozero",
    )
    return fig


def _eixo_semanas(df: pd.DataFrame) -> list[str]:
    return [f"Semana {int(s)}" for s in df["semana"]]


def _sem_dados(titulo: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text="Sem dados para o periodo selecionado",
        showarrow=False,
        font={"family": FONTE, "size": 14, "color": cores.TINTA_SUAVE},
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _aplicar_tema(fig, titulo, "", com_legenda=False)


def _barras_duplas(
    df: pd.DataFrame,
    tema: Tema,
    col_a: str,
    col_b: str,
    titulo: str,
    titulo_y: str,
) -> go.Figure:
    """Duas metricas comparaveis, mesmo eixo, barras agrupadas por semana."""
    if df.empty:
        return _sem_dados(titulo)

    eixo = _eixo_semanas(df)
    fig = go.Figure()
    for coluna, cor in ((col_a, tema.primaria), (col_b, tema.secundaria)):
        fig.add_bar(
            x=eixo,
            y=df[coluna],
            name=utils.ROTULOS_METRICAS[coluna],
            marker_color=cor,
            marker_line_width=0,
            text=df[coluna],
            texttemplate="%{text:,}",
            textposition="outside",
            textfont={"color": cores.TINTA_SECUNDARIA, "size": 12},
            cliponaxis=False,
            hovertemplate=f"<b>{utils.ROTULOS_METRICAS[coluna]}</b><br>%{{x}}: %{{y:,}}<extra></extra>",
        )

    fig.update_traces(marker_cornerradius=4)
    fig.update_layout(barmode="group")
    return _aplicar_tema(fig, titulo, titulo_y, com_legenda=True)


def grafico_alcance_visualizacoes(df: pd.DataFrame, tema: Tema) -> go.Figure:
    return _barras_duplas(
        df, tema, "alcance", "visualizacoes", "Alcance x Visualizacoes por semana", "Contas"
    )


def grafico_metrica_semanal(
    df: pd.DataFrame,
    tema: Tema,
    metrica: str,
    usar_secundaria: bool = False,
) -> go.Figure:
    """Uma metrica por semana, em barras, com a escala so dela.

    Interacoes e cliques no link ficam em graficos separados de proposito: os
    volumes sao muito diferentes (milhares contra centenas) e, num mesmo eixo, a
    serie menor viraria uma faixa rente ao zero -- o leitor perderia a tendencia
    justamente da metrica mais ligada a conversao. Um segundo eixo y resolveria
    o encaixe visual as custas da comparacao, entao a saida e dar a cada metrica
    o seu proprio grafico.
    """
    titulo = f"{utils.ROTULOS_METRICAS[metrica]} por semana"
    if df.empty:
        return _sem_dados(titulo)

    cor = tema.secundaria if usar_secundaria else tema.primaria
    fig = go.Figure()
    fig.add_bar(
        x=_eixo_semanas(df),
        y=df[metrica],
        marker_color=cor,
        marker_line_width=0,
        text=df[metrica],
        texttemplate="%{text:,}",
        textposition="outside",
        textfont={"color": cores.TINTA_SECUNDARIA, "size": 12},
        cliponaxis=False,
        hovertemplate="%{x}: %{y:,}<extra></extra>",
    )
    fig.update_traces(marker_cornerradius=4)
    # Serie unica: o titulo identifica a metrica, entao nao ha caixa de legenda.
    return _aplicar_tema(fig, titulo, utils.ROTULOS_METRICAS[metrica], com_legenda=False)


def grafico_seguidores(df: pd.DataFrame, tema: Tema) -> go.Figure:
    """Crescimento de seguidores: acumulado no mes + ganho de cada semana.

    As duas series estao na mesma unidade (seguidores), entao dividem um unico
    eixo -- dois eixos y transformariam a comparacao numa ilusao de escala.
    """
    if df.empty:
        return _sem_dados("Crescimento de seguidores")

    eixo = _eixo_semanas(df)
    acumulado = df["novos_seguidores"].cumsum()

    fig = go.Figure()
    fig.add_scatter(
        x=eixo,
        y=acumulado,
        name="Acumulado no periodo",
        mode="lines+markers+text",
        line={"color": tema.primaria, "width": 2, "shape": "spline", "smoothing": 0.4},
        marker={"color": tema.primaria, "size": 9, "line": {"color": SUPERFICIE, "width": 2}},
        fill="tozeroy",
        fillcolor=cores.com_alfa(tema.primaria, 0.10),
        text=acumulado,
        texttemplate="%{text:,}",
        textposition="top center",
        textfont={"color": cores.TINTA_SECUNDARIA, "size": 12},
        hovertemplate="<b>Acumulado</b>: %{y:,}<extra></extra>",
    )
    fig.add_scatter(
        x=eixo,
        y=df["novos_seguidores"],
        name="Novos na semana",
        mode="lines+markers",
        line={"color": tema.secundaria, "width": 2, "dash": "dot"},
        marker={"color": tema.secundaria, "size": 8, "line": {"color": SUPERFICIE, "width": 2}},
        hovertemplate="<b>Novos na semana</b>: %{y:,}<extra></extra>",
    )
    fig.update_layout(hovermode="x unified")
    return _aplicar_tema(fig, "Crescimento de seguidores", "Seguidores", com_legenda=True)


def grafico_taxa_engajamento(df: pd.DataFrame, tema: Tema) -> go.Figure:
    """Interacoes dividido por alcance, semana a semana. Serie unica."""
    if df.empty:
        return _sem_dados("Taxa de engajamento sobre o alcance")

    alcance = df["alcance"].replace(0, pd.NA)
    taxa = (df["interacoes"] / alcance * 100).astype(float)

    fig = go.Figure()
    fig.add_scatter(
        x=_eixo_semanas(df),
        y=taxa,
        mode="lines+markers+text",
        name="Taxa de engajamento",
        line={"color": tema.primaria, "width": 2},
        marker={"color": tema.primaria, "size": 9, "line": {"color": SUPERFICIE, "width": 2}},
        text=taxa,
        texttemplate="%{text:.1f}%",
        textposition="top center",
        textfont={"color": cores.TINTA_SECUNDARIA, "size": 12},
        connectgaps=True,
        hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
    )
    fig.update_yaxes(ticksuffix="%")
    # Serie unica: o titulo ja diz o que a linha e, entao nao ha caixa de legenda.
    return _aplicar_tema(fig, "Taxa de engajamento sobre o alcance", "% do alcance", com_legenda=False)


def grafico_evolucao_mensal(df: pd.DataFrame, tema: Tema, metrica: str) -> go.Figure:
    """Total da metrica escolhida mes a mes, somando as semanas de cada mes."""
    titulo = f"{utils.ROTULOS_METRICAS[metrica]} - evolucao mensal"
    if df.empty:
        return _sem_dados(titulo)

    mensal = df.groupby("mes_referencia", as_index=False)[metrica].sum()
    mensal = mensal.sort_values("mes_referencia")
    rotulos = [utils.rotulo_mes(m) for m in mensal["mes_referencia"]]

    fig = go.Figure()
    fig.add_bar(
        x=rotulos,
        y=mensal[metrica],
        marker_color=tema.primaria,
        marker_line_width=0,
        text=mensal[metrica],
        texttemplate="%{text:,}",
        textposition="outside",
        textfont={"color": cores.TINTA_SECUNDARIA, "size": 12},
        cliponaxis=False,
        hovertemplate="%{x}: %{y:,}<extra></extra>",
    )
    fig.update_traces(marker_cornerradius=4)
    return _aplicar_tema(fig, titulo, utils.ROTULOS_METRICAS[metrica], com_legenda=False)
