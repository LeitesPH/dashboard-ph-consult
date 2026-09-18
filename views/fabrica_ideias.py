"""Pagina 3 -- geradores de conteudo a partir da estrategia do cliente.

Tres modos, todos partindo do mesmo par (estrategia em PDF + referencia bruta):
ideias soltas, roteiro de carrossel e roteiro de Reels. Os dois ultimos chegam
estruturados (ver `modelos.py`), entao a tela consegue montar o carrossel slide
a slide e o Reels como tabela de gravacao, com cada pedaco pronto para copiar.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import cores
import ia
import utils

_ABAS = {
    "ideias": "Ideias de conteudo",
    "carrossel": "Carrossel",
    "reels": "Reels",
}

_EXPLICACAO = {
    "ideias": "Tres ideias soltas para escolher um caminho antes de escrever o roteiro.",
    "carrossel": (
        "Roteiro de ate 7 slides na estrutura de conversao: hook, agitacao, "
        "tres passos de solucao, autoridade e CTA."
    ),
    "reels": (
        "Roteiro de 30 a 45 segundos em tabela de gravacao (visual e audio), "
        "com B-rolls e fechamento em looping."
    ),
}

_CORES_PAPEL = {
    "HOOK": cores.CORAL,
    "AGITACAO": cores.CORAL_ESCURO,
    "SOLUCAO": cores.AZUL_MEDIO,
    "AUTORIDADE": cores.MARINHO,
    "CTA": cores.CORAL,
}

_ROTULO_PAPEL = {
    "HOOK": "Hook",
    "AGITACAO": "Agitacao",
    "SOLUCAO": "Solucao",
    "AUTORIDADE": "Autoridade",
    "CTA": "CTA",
}


# ---------------------------------------------------------------------------
# Blocos de apoio
# ---------------------------------------------------------------------------
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


def _rodape_uso(resultado: ia.Resultado) -> None:
    st.caption(
        f"{resultado.modelo} — {resultado.tokens_entrada:,} tokens de entrada "
        f"({resultado.cache_lido:,} lidos do cache) e {resultado.tokens_saida:,} "
        "de saida.".replace(",", ".")
    )


# ---------------------------------------------------------------------------
# Renderizacao de cada tipo de entrega
# ---------------------------------------------------------------------------
def _mostrar_carrossel(carrossel) -> None:
    st.markdown(f"**Tema:** {carrossel.tema}")
    st.caption(
        f"{len(carrossel.slides)} slides — copie o texto de cada um direto para a arte."
    )

    for slide in carrossel.slides:
        cor = _CORES_PAPEL.get(slide.papel, cores.MARINHO)
        rotulo = _ROTULO_PAPEL.get(slide.papel, slide.papel)
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:9px;margin:1.1rem 0 .4rem 0;">
              <span style="background:{cor};color:#ffffff;font-size:.68rem;font-weight:700;
                           letter-spacing:.07em;text-transform:uppercase;
                           padding:3px 9px;border-radius:999px;">{rotulo}</span>
              <span style="color:{cores.TINTA_SUAVE};font-size:.78rem;">
                Slide {slide.numero}
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='font-size:1.12rem;font-weight:600;color:{cores.MARINHO};"
            f"line-height:1.35;'>{slide.titulo}</div>",
            unsafe_allow_html=True,
        )
        if slide.texto:
            st.markdown(
                f"<div style='color:{cores.TINTA_SECUNDARIA};margin-top:.3rem;'>"
                f"{slide.texto}</div>",
                unsafe_allow_html=True,
            )

    st.divider()
    st.markdown("#### Legenda do post")
    st.code(carrossel.legenda, language=None, wrap_lines=True)
    if carrossel.hashtags:
        st.code(
            " ".join(f"#{h.lstrip('#')}" for h in carrossel.hashtags),
            language=None,
            wrap_lines=True,
        )


def _mostrar_reels(reels) -> None:
    st.markdown(f"**Titulo da legenda:** {reels.titulo_legenda}")
    st.caption(f"{len(reels.cenas)} cenas — esta e a tabela de gravacao.")

    tabela = pd.DataFrame(
        {
            "Tempo": [c.tempo for c in reels.cenas],
            "Visual (O que aparece na tela)": [c.visual for c in reels.cenas],
            "Audio (O que sera falado)": [c.audio for c in reels.cenas],
        }
    )
    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        column_config={
            "Tempo": st.column_config.TextColumn(width="small"),
            "Visual (O que aparece na tela)": st.column_config.TextColumn(width="large"),
            "Audio (O que sera falado)": st.column_config.TextColumn(width="large"),
        },
    )

    st.markdown(
        f"""
        <div style="background:{cores.CREME};border:1px solid {cores.CREME_BORDA};
                    border-left:3px solid {cores.CORAL};border-radius:10px;
                    padding:.75rem .95rem;margin-top:.6rem;">
          <div style="font-size:.7rem;font-weight:700;letter-spacing:.08em;
                      text-transform:uppercase;color:{cores.TINTA_SECUNDARIA};">
            Efeito de looping
          </div>
          <div style="color:{cores.MARINHO};margin-top:.25rem;">
            {reels.explicacao_loop}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Narracao corrida")
    st.code(" ".join(c.audio for c in reels.cenas), language=None, wrap_lines=True)


def _mostrar_resultado(resultado: ia.Resultado, cliente: str, nome_cliente: str) -> None:
    for aviso in resultado.avisos:
        st.warning(aviso, icon=":material/warning:")

    st.divider()
    if resultado.tipo == "carrossel" and resultado.carrossel:
        _mostrar_carrossel(resultado.carrossel)
    elif resultado.tipo == "reels" and resultado.reels:
        _mostrar_reels(resultado.reels)
    else:
        st.markdown(resultado.texto)

    markdown = ia.para_markdown(resultado, nome_cliente)
    st.download_button(
        "Baixar em Markdown",
        data=markdown,
        file_name=f"{resultado.tipo}-{cliente}.md",
        mime="text/markdown",
        icon=":material/download:",
        key=f"baixar_{resultado.tipo}",
    )
    _rodape_uso(resultado)


# ---------------------------------------------------------------------------
# Historico
# ---------------------------------------------------------------------------
def _historico(cliente: str) -> None:
    salvos = utils.listar_conteudos(cliente)
    if not salvos:
        return

    st.divider()
    st.subheader("Conteudos gerados")
    st.caption("Cada geracao fica salva na pasta do cliente e pode ser reaberta aqui.")

    for item in salvos[:20]:
        data = item.get("criado_em", "").replace("T", " ")
        titulo = item.get("resumo") or ia.MODOS.get(item.get("tipo", ""), "Conteudo")
        with st.expander(f"{ia.MODOS.get(item.get('tipo',''), 'Conteudo')} · {data} — {titulo}"):
            st.markdown(item.get("markdown", "_(sem conteudo)_"))
            col_a, col_b = st.columns([1, 4])
            col_a.download_button(
                "Baixar",
                data=item.get("markdown", ""),
                file_name=f"{item.get('tipo','conteudo')}-{item.get('id','')}.md",
                mime="text/markdown",
                key=f"dl_{item.get('id')}",
            )
            if col_b.button("Excluir", key=f"rm_{item.get('id')}", icon=":material/delete:"):
                utils.excluir_conteudo(cliente, item.get("id", ""))
                st.rerun()


def _resumo(resultado: ia.Resultado) -> str:
    """Primeira linha util da entrega, para identificar o item no historico."""
    if resultado.tipo == "carrossel" and resultado.carrossel:
        return resultado.carrossel.tema
    if resultado.tipo == "reels" and resultado.reels:
        return resultado.reels.titulo_legenda
    primeira = next(
        (l.strip("# ").strip() for l in resultado.texto.splitlines() if l.strip()), ""
    )
    return primeira[:80]


# ---------------------------------------------------------------------------
# Pagina
# ---------------------------------------------------------------------------
def render(cliente: str) -> None:
    config = utils.carregar_config(cliente)
    nome_cliente = config["nome"]

    st.title(f"Fabrica de ideias — {nome_cliente}")
    st.caption(
        "A estrategia do cliente entra como contexto fixo; a referencia abaixo e "
        "o que muda a cada geracao."
    )

    texto_pdf = utils.extrair_texto_pdf(cliente)
    _estado_pdf(cliente, texto_pdf)

    modo = st.radio(
        "O que voce quer gerar",
        list(_ABAS),
        format_func=lambda m: _ABAS[m],
        horizontal=True,
        key="modo_geracao",
    )
    st.caption(_EXPLICACAO[modo])

    referencia = st.text_area(
        "Cole aqui suas referencias, links ou ideias brutas",
        height=180,
        placeholder=(
            "Ex.: Reel de um concorrente falando sobre prevencao; uma materia sobre "
            "o aumento de casos na regiao; um comentario recorrente dos seguidores..."
        ),
        key="referencia_bruta",
    )

    api_key = utils.resolver_api_key()
    if not api_key:
        st.info(
            "Informe a chave da API da Anthropic na barra lateral para gerar conteudo.",
            icon=":material/key:",
        )

    rotulo_botao = {
        "ideias": "Gerar sugestoes de conteudo",
        "carrossel": "Gerar roteiro de carrossel",
        "reels": "Gerar roteiro de Reels",
    }[modo]

    if st.button(
        rotulo_botao,
        type="primary",
        icon=":material/auto_awesome:",
        disabled=not api_key,
    ):
        with st.spinner("Cruzando a estrategia do cliente com a sua referencia..."):
            resultado = ia.GERADORES[modo](
                api_key=api_key,
                texto_pdf=texto_pdf,
                referencia=referencia,
                nome_cliente=nome_cliente,
            )
        st.session_state[f"conteudo_{cliente}"] = resultado

        if resultado.sucesso:
            utils.salvar_conteudo(
                cliente,
                {
                    "tipo": resultado.tipo,
                    "resumo": _resumo(resultado),
                    "markdown": ia.para_markdown(resultado, nome_cliente),
                    "referencia": referencia.strip(),
                    "modelo": resultado.modelo,
                },
            )

    resultado = st.session_state.get(f"conteudo_{cliente}")
    if resultado is not None:
        if resultado.sucesso:
            _mostrar_resultado(resultado, cliente, nome_cliente)
        else:
            st.error(resultado.erro, icon=":material/error:")

    _historico(cliente)
