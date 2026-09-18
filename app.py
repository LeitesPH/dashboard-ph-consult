"""Dashboard de gestao de midias sociais -- multi-tenant, 100% local.

Execute com:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

import utils
from views import fabrica_ideias, novo_cliente, relatorios

PAGINAS = ["1. Novo Cliente", "2. Relatorios", "3. Fabrica de Ideias"]

st.set_page_config(
    page_title="Dashboard de Midias Sociais",
    page_icon=":material/insights:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _seletor_cliente(clientes: list[str]) -> str | None:
    """Selectbox 'Cliente Ativo', persistente entre as paginas."""
    st.sidebar.markdown("### Cliente ativo")

    if not clientes:
        st.sidebar.selectbox(
            "Cliente ativo", ["Nenhum cliente cadastrado"], disabled=True, label_visibility="collapsed"
        )
        return None

    anterior = st.session_state.get("cliente_ativo")
    indice = clientes.index(anterior) if anterior in clientes else 0
    escolhido = st.sidebar.selectbox(
        "Cliente ativo",
        clientes,
        index=indice,
        format_func=utils.nome_exibicao,
        label_visibility="collapsed",
        key="seletor_cliente",
    )
    st.session_state["cliente_ativo"] = escolhido
    return escolhido


def _campo_api_key() -> None:
    """Pede a chave da API so quando ela nao veio do ambiente/.env."""
    st.sidebar.divider()
    origem = utils.origem_api_key()

    if origem == "ambiente":
        st.sidebar.caption(":material/key: Chave da Anthropic carregada do `.env`.")
        return

    st.sidebar.text_input(
        "Chave da API da Anthropic",
        type="password",
        key="api_key_manual",
        placeholder="sk-ant-...",
        help=(
            "Nao foi encontrada a variavel ANTHROPIC_API_KEY. A chave digitada "
            "aqui vale apenas para esta sessao e nao e gravada em disco."
        ),
    )
    if utils.origem_api_key() == "ausente":
        st.sidebar.caption(
            ":material/info: Sem a chave, a Fabrica de Ideias fica indisponivel."
        )


def main() -> None:
    utils.garantir_estrutura()
    clientes = utils.listar_clientes()

    st.sidebar.title("Midias Sociais")
    cliente_ativo = _seletor_cliente(clientes)

    st.sidebar.divider()
    st.sidebar.markdown("### Navegacao")
    pagina = st.sidebar.radio(
        "Navegacao", PAGINAS, label_visibility="collapsed", key="pagina_atual"
    )

    if not clientes:
        st.sidebar.warning(
            "Nenhum cliente cadastrado. Va ate a aba **1. Novo Cliente** para criar o primeiro.",
            icon=":material/warning:",
        )

    _campo_api_key()
    st.sidebar.divider()
    st.sidebar.caption("Os dados ficam na pasta `clientes/`, nesta maquina.")

    if pagina == PAGINAS[0]:
        novo_cliente.render()
        return

    if cliente_ativo is None:
        st.title(pagina[3:])
        st.warning(
            "Nenhum cliente cadastrado ainda. Abra a aba **1. Novo Cliente** na "
            "barra lateral para criar o primeiro e liberar esta pagina.",
            icon=":material/warning:",
        )
        return

    if pagina == PAGINAS[1]:
        relatorios.render(cliente_ativo)
    else:
        fabrica_ideias.render(cliente_ativo)


if __name__ == "__main__":
    main()
