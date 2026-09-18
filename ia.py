"""Integracao com a API da Anthropic para a Fabrica de Ideias.

Arquitetura inspirada no `ai-shorts-generator`, que resolve bem dois problemas:

1. **Prompt de sistema fora do codigo.** Cada modo de geracao carrega o seu
   arquivo em `prompts/`. Dava para embutir a string no Python, mas ai toda
   mudanca de copy vira commit de codigo -- e quem ajusta esse texto e o
   estrategista, nao o programador.
2. **Formato garantido por schema.** Em vez de pedir texto e interpretar depois
   com regex, a resposta e validada contra um modelo Pydantic (`modelos.py`).
   O repositorio de referencia faz isso com `response_format` da OpenAI; o
   equivalente na Anthropic e `messages.parse(output_format=...)`.

Os prompts em `prompts/carrossel.md` e `prompts/reels.md` estao exatamente como
foram escritos pelo estrategista. O que o codigo acrescenta e apenas a nota de
entrega abaixo, que explica como despejar aquela mesma estrutura nos campos do
schema -- nenhuma regra de conteudo, tom ou retencao e alterada aqui.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import anthropic
import pydantic

import modelos

MODELO_PADRAO = "claude-opus-5"
BASE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"

# Beta que habilita o fallback de servidor: se um pedido for recusado por um
# classificador de seguranca, a API responde com um modelo alternativo em vez de
# devolver a recusa. Contas sem o beta liberado respondem 400 -- ver `_chamar`.
BETA_FALLBACK = "server-side-fallback-2026-07-01"

# Roteiros sao entregas curtas (um carrossel passa longe de 2 mil tokens), entao
# este teto e folgado e mantem a requisicao bem abaixo do timeout HTTP.
MAX_TOKENS_ROTEIRO = 8000
MAX_TOKENS_IDEIAS = 16000

MODOS = {
    "ideias": "3 ideias de conteudo",
    "carrossel": "Roteiro de carrossel",
    "reels": "Roteiro de Reels",
}

SYSTEM_IDEIAS = """Você é um copywriter e estrategista de conteúdo sênior. Seu objetivo é adaptar o tom de voz perfeitamente ao nicho do cliente, seja ele um perfil corporativo, um executivo de negócios ou uma profissional da área médica.

Com base na estratégia do cliente e na referência enviada pelo usuário, gere 3 ideias de conteúdo (ex: Reels ou Carrossel). Para cada ideia, entregue obrigatoriamente: 1. Gancho (visual/falado), 2. Desenvolvimento lógico cruzando com a referência, 3. Call to Action focada em autoridade.

Formate a resposta em Markdown, com um título de nível 3 por ideia (incluindo o formato sugerido entre parênteses) e os três itens em subtítulos. Escreva em português do Brasil. Não invente dados, números ou casos que não estejam na estratégia ou na referência."""

# Notas de entrega: traduzem a estrutura pedida no prompt para os campos do
# schema. O conteudo exigido e o mesmo -- muda so o involucro.
_ENTREGA_CARROSSEL = """

# Formato da entrega
Devolva a estrutura obrigatoria acima nos campos do schema, um slide por item de `slides`:
- `[SLIDE 1 - HOOK]` -> primeiro item, com `papel` = "HOOK".
- `[SLIDE 2 - AGITACAO]` -> `papel` = "AGITACAO".
- `[SLIDE 3 a 5 - SOLUCAO]` -> tres itens com `papel` = "SOLUCAO", um passo curto em cada.
- `[SLIDE 6 - AUTORIDADE]` -> `papel` = "AUTORIDADE".
- `[SLIDE 7 - CTA]` -> `papel` = "CTA".
Em cada slide, `titulo` e a frase em destaque na arte e `texto` e o apoio (pode ficar vazio).
Preencha tambem `legenda` (a legenda do post) e `hashtags`. Escreva em portugues do Brasil."""

_ENTREGA_REELS = """

# Formato da entrega
Devolva a tabela pedida acima nos campos do schema: cada linha da tabela vira um item de `cenas`, com `visual` (a coluna "Visual (O que aparece na tela)"), `audio` (a coluna "Audio (O que sera falado)") e `tempo` (a faixa de segundos daquele trecho, por exemplo "0-3s").
`titulo_legenda` recebe o titulo sugerido para a legenda.
Em `explicacao_loop`, escreva uma frase dizendo como a ultima fala se conecta a primeira palavra do video -- e a unica linha de explicacao permitida, e existe para o editor conferir o corte. Escreva em portugues do Brasil."""


@dataclass
class Resultado:
    """Resposta de qualquer um dos modos de geracao."""

    tipo: str = "ideias"
    texto: str = ""
    carrossel: modelos.Carrossel | None = None
    reels: modelos.Reels | None = None
    sucesso: bool = False
    erro: str = ""
    modelo: str = ""
    tokens_entrada: int = 0
    tokens_saida: int = 0
    cache_lido: int = 0
    avisos: list[str] = field(default_factory=list)


def carregar_prompt(nome: str) -> str:
    """Le o prompt de sistema de `prompts/<nome>.md`."""
    caminho = PROMPTS_DIR / f"{nome}.md"
    try:
        return caminho.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise FileNotFoundError(
            f"Prompt '{nome}' nao encontrado em {caminho}. O arquivo faz parte do "
            "projeto e precisa existir para este gerador funcionar."
        ) from exc


def _montar_system(prompt_base: str, texto_pdf: str, nota_entrega: str = "") -> list[dict]:
    """Blocos de sistema: estrategia do cliente primeiro, instrucoes depois.

    A ordem importa para o cache: a estrategia e o bloco grande e identico entre
    uma geracao e outra (e entre os tres modos), entao ela vem primeiro e recebe
    o `cache_control`. Se o prompt do modo viesse antes, trocar de carrossel para
    Reels invalidaria o prefixo e o PDF seria cobrado de novo.
    """
    estrategia = texto_pdf.strip() or (
        "(Nenhum documento de estrategia foi encontrado para este cliente. "
        "Trabalhe apenas com a referencia enviada pelo usuario e sinalize, ao "
        "final, que a estrategia nao estava disponivel.)"
    )
    return [
        {
            "type": "text",
            "text": (
                "Documento de estrategia de posicionamento do cliente:\n"
                f"<estrategia_do_cliente>\n{estrategia}\n</estrategia_do_cliente>"
            ),
            "cache_control": {"type": "ephemeral"},
        },
        {"type": "text", "text": prompt_base + nota_entrega},
    ]


def _montar_mensagem(referencia: str, nome_cliente: str, pedido: str) -> list[dict]:
    conteudo = (
        f"Cliente: {nome_cliente}\n\n"
        "Referencias, links e ideias brutas enviadas pelo usuario:\n"
        f"<referencia>\n{referencia.strip()}\n</referencia>\n\n"
        f"{pedido}"
    )
    return [{"role": "user", "content": conteudo}]


def _validar_entrada(api_key: str, referencia: str) -> str:
    if not api_key:
        return "Informe a chave da API da Anthropic na barra lateral."
    if not referencia.strip():
        return "Cole ao menos uma referencia, link ou ideia bruta."
    return ""


def _erro_amigavel(exc: Exception, modelo: str) -> str:
    """Traduz a excecao do SDK para uma frase que o usuario consegue agir."""
    if isinstance(exc, pydantic.ValidationError):
        return (
            "A resposta veio fora do formato esperado (o roteiro pode ter chegado "
            "incompleto). Gere novamente."
        )
    if isinstance(exc, anthropic.AuthenticationError):
        return "Chave da API invalida ou sem permissao (401)."
    if isinstance(exc, anthropic.PermissionDeniedError):
        return "Esta chave nao tem permissao para usar este modelo (403)."
    if isinstance(exc, anthropic.NotFoundError):
        return f"O modelo '{modelo}' nao esta disponivel para esta conta (404)."
    if isinstance(exc, anthropic.RateLimitError):
        return "Limite de requisicoes atingido (429). Tente de novo em alguns segundos."
    if isinstance(exc, anthropic.APIConnectionError):
        return "Nao foi possivel conectar a API da Anthropic. Verifique a internet."
    if isinstance(exc, anthropic.APIStatusError):
        return f"A API respondeu com erro {exc.status_code}: {exc.message}"
    return f"Falha inesperada na geracao: {exc}"


def _chamar(
    cliente: anthropic.Anthropic,
    modelo: str,
    system: list[dict],
    mensagens: list[dict],
    max_tokens: int,
    output_format=None,
):
    """Chama a API com fallback de servidor quando a conta tem o beta liberado.

    Com `output_format`, usa `parse` e a resposta ja volta validada contra o
    schema; sem ele, e uma geracao de texto comum.
    """
    avisos: list[str] = []
    comum = dict(
        model=modelo,
        max_tokens=max_tokens,
        system=system,
        messages=mensagens,
        thinking={"type": "adaptive"},
    )
    if output_format is not None:
        comum["output_format"] = output_format

    chamada = cliente.beta.messages.parse if output_format is not None else cliente.beta.messages.create
    try:
        return chamada(betas=[BETA_FALLBACK], fallbacks="default", **comum), avisos
    except anthropic.BadRequestError as exc:
        # Contas sem o beta de fallback liberado recusam o header. Nesse caso
        # repetimos na rota estavel em vez de falhar a geracao.
        if "anthropic-beta" not in str(exc).lower():
            raise
        avisos.append(
            "O fallback automatico de modelo nao esta habilitado nesta conta; "
            "a geracao seguiu sem ele."
        )

    estavel = cliente.messages.parse if output_format is not None else cliente.messages.create
    return estavel(**comum), avisos


def _preencher_uso(resultado: Resultado, resposta, modelo: str) -> Resultado:
    uso = resposta.usage
    resultado.modelo = getattr(resposta, "model", modelo)
    resultado.tokens_entrada = getattr(uso, "input_tokens", 0) or 0
    resultado.tokens_saida = getattr(uso, "output_tokens", 0) or 0
    resultado.cache_lido = getattr(uso, "cache_read_input_tokens", 0) or 0
    return resultado


def _recusa(resposta) -> bool:
    return getattr(resposta, "stop_reason", "") == "refusal"


MSG_RECUSA = (
    "O modelo recusou este pedido. Revise a referencia enviada e tente novamente "
    "com outro enquadramento."
)


# ---------------------------------------------------------------------------
# Modo 1 -- 3 ideias de conteudo (texto livre em Markdown)
# ---------------------------------------------------------------------------
def gerar_sugestoes(
    api_key: str,
    texto_pdf: str,
    referencia: str,
    nome_cliente: str,
    modelo: str = MODELO_PADRAO,
) -> Resultado:
    """Gera 3 ideias de conteudo a partir da estrategia + referencia."""
    erro = _validar_entrada(api_key, referencia)
    if erro:
        return Resultado(tipo="ideias", erro=erro)

    cliente = anthropic.Anthropic(api_key=api_key)
    system = _montar_system(SYSTEM_IDEIAS, texto_pdf)
    mensagens = _montar_mensagem(
        referencia, nome_cliente, "Gere as 3 ideias de conteudo seguindo a estrutura pedida."
    )

    try:
        resposta, avisos = _chamar(
            cliente, modelo, system, mensagens, MAX_TOKENS_IDEIAS
        )
    except Exception as exc:  # noqa: BLE001 - a mensagem vai para a interface
        return Resultado(tipo="ideias", erro=_erro_amigavel(exc, modelo))

    if _recusa(resposta):
        return Resultado(tipo="ideias", erro=MSG_RECUSA)

    texto = "\n\n".join(
        b.text for b in resposta.content if getattr(b, "type", "") == "text"
    ).strip()
    if not texto:
        return Resultado(tipo="ideias", erro="A API respondeu sem texto. Tente novamente.")

    if getattr(resposta, "stop_reason", "") == "max_tokens":
        avisos.append("A resposta atingiu o limite de tamanho e pode estar incompleta.")

    return _preencher_uso(
        Resultado(tipo="ideias", texto=texto, sucesso=True, avisos=avisos), resposta, modelo
    )


# ---------------------------------------------------------------------------
# Modo 2 -- roteiro de carrossel
# ---------------------------------------------------------------------------
def gerar_carrossel(
    api_key: str,
    texto_pdf: str,
    referencia: str,
    nome_cliente: str,
    modelo: str = MODELO_PADRAO,
) -> Resultado:
    """Gera o roteiro de carrossel seguindo `prompts/carrossel.md`."""
    erro = _validar_entrada(api_key, referencia)
    if erro:
        return Resultado(tipo="carrossel", erro=erro)

    cliente = anthropic.Anthropic(api_key=api_key)
    system = _montar_system(carregar_prompt("carrossel"), texto_pdf, _ENTREGA_CARROSSEL)
    mensagens = _montar_mensagem(
        referencia,
        nome_cliente,
        "Escreva o roteiro do carrossel seguindo a estrutura obrigatoria.",
    )

    try:
        resposta, avisos = _chamar(
            cliente, modelo, system, mensagens, MAX_TOKENS_ROTEIRO, modelos.Carrossel
        )
    except Exception as exc:  # noqa: BLE001
        return Resultado(tipo="carrossel", erro=_erro_amigavel(exc, modelo))

    if _recusa(resposta):
        return Resultado(tipo="carrossel", erro=MSG_RECUSA)

    carrossel = getattr(resposta, "parsed_output", None)
    if carrossel is None:
        return Resultado(
            tipo="carrossel",
            erro="A resposta nao veio no formato esperado. Tente gerar novamente.",
        )

    return _preencher_uso(
        Resultado(tipo="carrossel", carrossel=carrossel, sucesso=True, avisos=avisos),
        resposta,
        modelo,
    )


# ---------------------------------------------------------------------------
# Modo 3 -- roteiro de Reels
# ---------------------------------------------------------------------------
def gerar_reels(
    api_key: str,
    texto_pdf: str,
    referencia: str,
    nome_cliente: str,
    modelo: str = MODELO_PADRAO,
) -> Resultado:
    """Gera o roteiro de Reels seguindo `prompts/reels.md`."""
    erro = _validar_entrada(api_key, referencia)
    if erro:
        return Resultado(tipo="reels", erro=erro)

    cliente = anthropic.Anthropic(api_key=api_key)
    system = _montar_system(carregar_prompt("reels"), texto_pdf, _ENTREGA_REELS)
    mensagens = _montar_mensagem(
        referencia,
        nome_cliente,
        "Escreva o roteiro do Reels seguindo as regras de retencao e o efeito de looping.",
    )

    try:
        resposta, avisos = _chamar(
            cliente, modelo, system, mensagens, MAX_TOKENS_ROTEIRO, modelos.Reels
        )
    except Exception as exc:  # noqa: BLE001
        return Resultado(tipo="reels", erro=_erro_amigavel(exc, modelo))

    if _recusa(resposta):
        return Resultado(tipo="reels", erro=MSG_RECUSA)

    reels = getattr(resposta, "parsed_output", None)
    if reels is None:
        return Resultado(
            tipo="reels",
            erro="A resposta nao veio no formato esperado. Tente gerar novamente.",
        )

    return _preencher_uso(
        Resultado(tipo="reels", reels=reels, sucesso=True, avisos=avisos), resposta, modelo
    )


GERADORES = {
    "ideias": gerar_sugestoes,
    "carrossel": gerar_carrossel,
    "reels": gerar_reels,
}


# ---------------------------------------------------------------------------
# Exportacao
# ---------------------------------------------------------------------------
def para_markdown(resultado: Resultado, nome_cliente: str = "") -> str:
    """Versao em Markdown da entrega, para baixar ou colar em outro lugar."""
    if resultado.tipo == "ideias":
        return resultado.texto

    cabecalho = f"# {MODOS[resultado.tipo]}" + (f" — {nome_cliente}" if nome_cliente else "")

    if resultado.tipo == "carrossel" and resultado.carrossel:
        c = resultado.carrossel
        linhas = [cabecalho, "", f"**Tema:** {c.tema}", ""]
        for slide in c.slides:
            linhas.append(f"### Slide {slide.numero} — {slide.papel}")
            linhas.append(f"**{slide.titulo}**")
            if slide.texto:
                linhas.append("")
                linhas.append(slide.texto)
            linhas.append("")
        linhas += ["---", "", "## Legenda", "", c.legenda, ""]
        if c.hashtags:
            linhas.append(" ".join(f"#{h.lstrip('#')}" for h in c.hashtags))
        return "\n".join(linhas)

    if resultado.tipo == "reels" and resultado.reels:
        r = resultado.reels
        linhas = [
            cabecalho,
            "",
            f"**Titulo da legenda:** {r.titulo_legenda}",
            "",
            "| Tempo | Visual (O que aparece na tela) | Áudio (O que será falado) |",
            "|---|---|---|",
        ]
        for cena in r.cenas:
            visual = cena.visual.replace("|", "\\|").replace("\n", " ")
            audio = cena.audio.replace("|", "\\|").replace("\n", " ")
            linhas.append(f"| {cena.tempo} | {visual} | {audio} |")
        linhas += ["", f"**Looping:** {r.explicacao_loop}"]
        return "\n".join(linhas)

    return resultado.texto
