"""Pagina 2 -- insercao semanal e visualizacao mensal das metricas."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import cores
import graficos
import utils


def _formulario_semanal(cliente: str) -> None:
    st.subheader("Inserir dados da semana")

    hoje = date.today()
    with st.form("form_metricas", clear_on_submit=False):
        col_a, col_b, col_c = st.columns([2, 1, 1])
        mes = col_a.selectbox("Mes de referencia", utils.MESES, index=hoje.month - 1)
        ano = col_b.number_input("Ano", min_value=2020, max_value=2100, value=hoje.year, step=1)
        semana = col_c.selectbox("Semana", [1, 2, 3, 4], index=0)

        col_1, col_2, col_3 = st.columns(3)
        alcance = col_1.number_input("Alcance", min_value=0, step=100, value=0)
        visualizacoes = col_2.number_input("Visualizacoes", min_value=0, step=100, value=0)
        interacoes = col_3.number_input("Interacoes", min_value=0, step=10, value=0)

        col_4, col_5 = st.columns(2)
        cliques = col_4.number_input("Cliques no link", min_value=0, step=1, value=0)
        seguidores = col_5.number_input("Novos seguidores", min_value=0, step=1, value=0)

        substituir = st.checkbox(
            "Substituir os dados caso esta semana ja esteja registrada",
            value=False,
        )
        enviado = st.form_submit_button("Salvar semana", type="primary", icon=":material/save:")

    if not enviado:
        return

    registro = {
        "mes_referencia": utils.chave_mes(mes, int(ano)),
        "semana": int(semana),
        "alcance": int(alcance),
        "visualizacoes": int(visualizacoes),
        "interacoes": int(interacoes),
        "cliques_link": int(cliques),
        "novos_seguidores": int(seguidores),
    }

    gravado = utils.salvar_metrica(cliente, registro, substituir=substituir)
    if gravado:
        st.success(
            f"Semana {semana} de {mes}/{int(ano)} salva em `metricas.csv`.",
            icon=":material/check_circle:",
        )
        st.rerun()
    else:
        st.warning(
            f"A semana {semana} de {mes}/{int(ano)} ja esta registrada. Marque "
            "'Substituir os dados...' para sobrescrever.",
            icon=":material/warning:",
        )


def _cartoes_resumo(df_mes: pd.DataFrame, df_anterior: pd.DataFrame) -> None:
    """Totais do mes com a variacao sobre o mes anterior."""
    colunas = st.columns(len(utils.COLUNAS_NUMERICAS))
    for coluna, metrica in zip(colunas, utils.COLUNAS_NUMERICAS):
        total = int(df_mes[metrica].sum())
        delta = None
        if not df_anterior.empty:
            anterior = int(df_anterior[metrica].sum())
            if anterior:
                delta = f"{(total - anterior) / anterior * 100:+.1f}%"
            elif total:
                delta = "novo"
        coluna.metric(utils.ROTULOS_METRICAS[metrica], f"{total:,}".replace(",", "."), delta)


def _tabela(df_mes: pd.DataFrame) -> None:
    tabela = df_mes.assign(semana=df_mes["semana"].map(lambda s: f"Semana {int(s)}"))
    tabela = tabela[["semana", *utils.COLUNAS_NUMERICAS]].rename(
        columns={"semana": "Periodo", **utils.ROTULOS_METRICAS}
    )
    total = {"Periodo": "Total do mes"}
    total.update({utils.ROTULOS_METRICAS[c]: int(df_mes[c].sum()) for c in utils.COLUNAS_NUMERICAS})
    tabela = pd.concat([tabela, pd.DataFrame([total])], ignore_index=True)
    st.dataframe(tabela, width="stretch", hide_index=True)


def _remover_semana(cliente: str, df_mes: pd.DataFrame, mes_selecionado: str) -> None:
    with st.expander("Corrigir um lancamento"):
        semana = st.selectbox(
            "Semana a remover",
            sorted(int(s) for s in df_mes["semana"]),
            format_func=lambda s: f"Semana {s}",
            key="remover_semana",
        )
        if st.button("Remover semana", icon=":material/delete:"):
            if utils.excluir_metrica(cliente, mes_selecionado, int(semana)):
                st.success("Lancamento removido.", icon=":material/check_circle:")
                st.rerun()
            else:
                st.warning("Nada foi removido.", icon=":material/warning:")


def render(cliente: str) -> None:
    config = utils.carregar_config(cliente)
    tema = graficos.Tema(config)

    st.title(f"Relatorios — {config['nome']}")
    st.markdown(
        f"""
        <div style="display:flex;gap:8px;align-items:center;margin:-8px 0 14px 0;">
          <span style="display:inline-block;width:14px;height:14px;border-radius:4px;
                       background:{tema.primaria};"></span>
          <span style="display:inline-block;width:14px;height:14px;border-radius:4px;
                       background:{tema.secundaria};"></span>
          <span style="color:{cores.TINTA_SUAVE};font-size:.82rem;">
            graficos pintados com as cores da marca deste cliente
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _formulario_semanal(cliente)
    st.divider()

    df = utils.carregar_metricas(cliente)
    if df.empty:
        st.info(
            "Nenhuma metrica registrada ainda. Preencha o formulario acima para "
            "comecar o historico deste cliente.",
            icon=":material/info:",
        )
        return

    st.subheader("Visualizacao mensal")
    meses = sorted(df["mes_referencia"].unique(), reverse=True)
    col_mes, col_download = st.columns([3, 1])
    mes_selecionado = col_mes.selectbox(
        "Mes", meses, format_func=utils.rotulo_mes, key="mes_relatorio"
    )
    col_download.download_button(
        "Baixar CSV",
        data=utils.caminho_metricas(cliente).read_bytes(),
        file_name=f"metricas-{cliente}.csv",
        mime="text/csv",
        icon=":material/download:",
        width="stretch",
    )

    df_mes = df[df["mes_referencia"] == mes_selecionado]
    indice = meses.index(mes_selecionado)
    df_anterior = (
        df[df["mes_referencia"] == meses[indice + 1]] if indice + 1 < len(meses) else df.iloc[0:0]
    )

    _cartoes_resumo(df_mes, df_anterior)
    st.caption(
        f"Variacao percentual comparada a {utils.rotulo_mes(meses[indice + 1])}."
        if not df_anterior.empty
        else "Primeiro mes registrado -- ainda nao ha base de comparacao."
    )

    _tabela(df_mes)

    col_1, col_2 = st.columns(2)
    with col_1:
        st.plotly_chart(
            graficos.grafico_alcance_visualizacoes(df_mes, tema), width="stretch"
        )
    with col_2:
        st.plotly_chart(graficos.grafico_seguidores(df_mes, tema), width="stretch")

    # Interacoes e cliques tem ordens de grandeza diferentes: cada um no seu
    # grafico, com a propria escala.
    col_3, col_4 = st.columns(2)
    with col_3:
        st.plotly_chart(
            graficos.grafico_metrica_semanal(df_mes, tema, "interacoes"),
            width="stretch",
        )
    with col_4:
        st.plotly_chart(
            graficos.grafico_metrica_semanal(df_mes, tema, "cliques_link", usar_secundaria=True),
            width="stretch",
        )

    st.plotly_chart(graficos.grafico_taxa_engajamento(df_mes, tema), width="stretch")

    if len(meses) > 1:
        st.divider()
        st.subheader("Comparativo entre meses")
        metrica = st.selectbox(
            "Metrica",
            utils.COLUNAS_NUMERICAS,
            format_func=lambda c: utils.ROTULOS_METRICAS[c],
            key="metrica_mensal",
        )
        st.plotly_chart(
            graficos.grafico_evolucao_mensal(df, tema, metrica), width="stretch"
        )

    _remover_semana(cliente, df_mes, mes_selecionado)
