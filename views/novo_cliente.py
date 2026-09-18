"""Pagina 1 -- cadastro de um novo cliente."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import cores
import graficos
import utils

_DEMO = pd.DataFrame(
    {
        "semana": [1, 2, 3, 4],
        "alcance": [12400, 15800, 14200, 19100],
        "visualizacoes": [18900, 24300, 21050, 28800],
    }
)


def _previa_cores(primaria: str, secundaria: str) -> None:
    """Mostra como as cores escolhidas vao aparecer nos relatorios."""
    diagnostico = cores.diagnosticar_par(primaria, secundaria)

    st.markdown(
        f"""
        <div style="display:flex;gap:10px;align-items:center;margin:4px 0 12px 0;">
          <span style="display:inline-block;width:46px;height:46px;border-radius:10px;
                       background:{primaria};border:1px solid rgba(0,0,0,.08);"></span>
          <span style="display:inline-block;width:46px;height:46px;border-radius:10px;
                       background:{secundaria};border:1px solid rgba(0,0,0,.08);"></span>
          <span style="color:{cores.TINTA_SECUNDARIA};font-size:.86rem;">
            {primaria} &nbsp;/&nbsp; {secundaria}
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tema = graficos.Tema({"cor_primaria": primaria, "cor_secundaria": secundaria})
    figura = graficos.grafico_alcance_visualizacoes(_DEMO, tema)
    figura.update_layout(height=260, title_text="Previa com dados de exemplo")
    st.plotly_chart(figura, width="stretch", config={"displayModeBar": False})

    for aviso in diagnostico["avisos"]:
        if diagnostico["status"] == "critico":
            st.error(aviso, icon=":material/error:")
        else:
            st.warning(aviso, icon=":material/warning:")

    if diagnostico["status"] == "ok":
        st.success(
            "As duas cores se distinguem bem, inclusive para leitores com daltonismo.",
            icon=":material/check_circle:",
        )

    for observacao in diagnostico["observacoes"]:
        st.caption(f":material/info: {observacao}")


def _clientes_cadastrados() -> None:
    """Ajustes pos-cadastro: trocar cores ou substituir o PDF de estrategia."""
    lista = utils.listar_clientes()
    if not lista:
        return

    st.divider()
    st.subheader("Clientes cadastrados")
    st.caption(
        "Use esta area para corrigir as cores da marca ou enviar uma nova versao "
        "do documento de estrategia."
    )

    for identificador in lista:
        config = utils.carregar_config(identificador)
        pdf = utils.caminho_pdf(identificador)
        metricas = utils.carregar_metricas(identificador)
        with st.expander(f"{config['nome']}  —  `clientes/{identificador}/`"):
            st.markdown(
                f"- Estrategia: **{pdf.name if pdf else 'nenhum PDF na pasta'}**\n"
                f"- Semanas registradas: **{len(metricas)}**"
            )
            col_a, col_b = st.columns(2)
            nova_primaria = col_a.color_picker(
                "Cor primaria", config["cor_primaria"], key=f"edit_p_{identificador}"
            )
            nova_secundaria = col_b.color_picker(
                "Cor secundaria", config["cor_secundaria"], key=f"edit_s_{identificador}"
            )
            novo_pdf = st.file_uploader(
                "Substituir o PDF de estrategia (opcional)",
                type=["pdf"],
                key=f"edit_pdf_{identificador}",
            )
            if st.button("Salvar alteracoes", key=f"edit_btn_{identificador}"):
                config["cor_primaria"] = cores.normalizar_hex(nova_primaria)
                config["cor_secundaria"] = cores.normalizar_hex(
                    nova_secundaria, cores.COR_SECUNDARIA_PADRAO
                )
                utils.salvar_config(identificador, config)
                if novo_pdf is not None:
                    utils.substituir_pdf(identificador, novo_pdf)
                st.success(f"'{config['nome']}' atualizado.", icon=":material/check_circle:")
                st.rerun()


def render() -> None:
    st.title("Novo cliente")
    st.caption(
        "Cada cliente vira uma pasta em `clientes/`, com o PDF de estrategia, as "
        "cores da marca (`config.json`) e o historico de metricas (`metricas.csv`)."
    )

    nome = st.text_input(
        "Nome do cliente",
        placeholder="Ex.: Clinica Aurora",
        help="Usado nos relatorios. A pasta recebe uma versao sem acentos nem espacos.",
    )

    arquivo_pdf = st.file_uploader(
        "Documento de estrategia (PDF)",
        type=["pdf"],
        help="E a base da Fabrica de Ideias: posicionamento, tom de voz, publico.",
    )

    col_a, col_b = st.columns(2)
    cor_primaria = col_a.color_picker("Cor primaria da marca", cores.COR_PRIMARIA_PADRAO)
    cor_secundaria = col_b.color_picker("Cor secundaria da marca", cores.COR_SECUNDARIA_PADRAO)

    _previa_cores(cor_primaria, cor_secundaria)

    if st.button("Salvar cliente", type="primary", icon=":material/save:"):
        if not nome.strip():
            st.error("Informe o nome do cliente.", icon=":material/error:")
            return
        if arquivo_pdf is None:
            st.error(
                "Envie o PDF de estrategia -- ele alimenta a Fabrica de Ideias.",
                icon=":material/error:",
            )
            return

        try:
            identificador = utils.criar_cliente(nome, arquivo_pdf, cor_primaria, cor_secundaria)
        except (ValueError, OSError) as exc:
            st.error(str(exc), icon=":material/error:")
            return

        st.session_state["cliente_ativo"] = identificador
        st.success(
            f"Cliente '{nome.strip()}' criado em `clientes/{identificador}/` "
            "com o PDF, o config.json e o metricas.csv. Ele ja esta selecionado "
            "como Cliente Ativo na barra lateral.",
            icon=":material/check_circle:",
        )
        st.balloons()

    _clientes_cadastrados()
