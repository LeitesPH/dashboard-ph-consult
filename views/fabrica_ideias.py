"""Pagina 3 -- geracao de ideias de conteudo a partir da estrategia do cliente."""

from __future__ import annotations

import streamlit as st

import ia
import utils


def _estado_pdf(cliente: str, texto: str) -> None:
    caminho = utils.caminho_pdf(cliente)
    if caminho is None:
        st.warning(
            "Este cliente nao tem PDF de estrategia na pasta. Envie um em "
            "'Novo cliente' > 'Clientes cadastrados' para a IA trabalhar com o "
            "posicionamento certo.",
            icon=":material/warning:",
        )
        return

    if not texto:
        st.warning(
            f"Nao foi possivel extrair texto de `{caminho.name}`. O arquivo pode "
            "ser um PDF escaneado (imagem), que precisaria de OCR.",
            icon=":material/warning:",
        )
        return

    st.caption(
        f"Estrategia carregada: **{caminho.name}** — {len(texto):,} caracteres "
        "enviados como contexto.".replace(",", ".")
    )
    with st.expander("Ver o texto extraido do PDF"):
        st.text_area("Texto da estrategia", texto, height=260, disabled=True)


def render(cliente: str) -> None:
    config = utils.carregar_config(cliente)
    st.title(f"Fabrica de ideias — {config['nome']}")
    st.caption(
        "A estrategia do cliente entra como contexto fixo; a referencia abaixo e "
        "o que muda a cada geracao."
    )

    texto_pdf = utils.extrair_texto_pdf(cliente)
    _estado_pdf(cliente, texto_pdf)

    referencia = st.text_area(
        "Cole aqui suas referencias, links ou ideias brutas",
        height=200,
        placeholder=(
            "Ex.: Reel de um concorrente falando sobre prevencao; uma materia sobre "
            "o aumento de casos na regiao; um comentario recorrente dos seguidores..."
        ),
        key="referencia_bruta",
    )

    api_key = utils.resolver_api_key()
    if not api_key:
        st.info(
            "Informe a chave da API da Anthropic na barra lateral para gerar sugestoes.",
            icon=":material/key:",
        )

    gerar = st.button(
        "Gerar sugestoes de conteudo",
        type="primary",
        icon=":material/auto_awesome:",
        disabled=not api_key,
    )

    if gerar:
        with st.spinner("Cruzando a estrategia do cliente com a sua referencia..."):
            resultado = ia.gerar_sugestoes(
                api_key=api_key,
                texto_pdf=texto_pdf,
                referencia=referencia,
                nome_cliente=config["nome"],
            )
        st.session_state[f"ideias_{cliente}"] = resultado

    resultado = st.session_state.get(f"ideias_{cliente}")
    if resultado is None:
        return

    if not resultado.sucesso:
        st.error(resultado.erro, icon=":material/error:")
        return

    for aviso in resultado.avisos:
        st.warning(aviso, icon=":material/warning:")

    st.divider()
    st.markdown(resultado.texto)

    st.download_button(
        "Baixar as ideias (.md)",
        data=resultado.texto,
        file_name=f"ideias-{cliente}.md",
        mime="text/markdown",
        icon=":material/download:",
    )
    st.caption(
        f"{resultado.modelo} — {resultado.tokens_entrada:,} tokens de entrada "
        f"({resultado.cache_lido:,} lidos do cache) e {resultado.tokens_saida:,} "
        "de saida.".replace(",", ".")
    )
