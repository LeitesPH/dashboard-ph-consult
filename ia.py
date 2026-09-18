"""Integracao com a API da Anthropic para a Fabrica de Ideias."""

from __future__ import annotations

from dataclasses import dataclass, field

import anthropic

MODELO_PADRAO = "claude-opus-5"
MAX_TOKENS = 16000

# Beta que habilita o fallback de servidor: se um pedido for recusado por um
# classificador de seguranca, a API responde com um modelo alternativo em vez de
# devolver a recusa. Contas sem o beta liberado respondem 400 -- ver `_gerar`.
BETA_FALLBACK = "server-side-fallback-2026-07-01"

SYSTEM_PROMPT = """Voce e um copywriter e estrategista de conteudo senior. Seu objetivo e adaptar o tom de voz perfeitamente ao nicho do cliente, seja ele um perfil corporativo, um executivo de negocios ou uma profissional da area medica.

Abaixo esta o documento de estrategia de posicionamento do cliente:
<estrategia_do_cliente>
{texto_do_pdf_extraido}
</estrategia_do_cliente>

Com base nisso e na referencia enviada pelo usuario, gere 3 ideias de conteudo (ex: Reels ou Carrossel). Para cada ideia, entregue obrigatoriamente: 1. Gancho (visual/falado), 2. Desenvolvimento logico cruzando com a referencia, 3. Call to Action focada em autoridade.

Formate a resposta em Markdown, com um titulo de nivel 3 por ideia (incluindo o formato sugerido entre parenteses) e os tres itens em subtitulos. Escreva em portugues do Brasil. Nao invente dados, numeros ou casos que nao estejam na estrategia ou na referencia."""


@dataclass
class ResultadoIA:
    """Resposta da geracao de ideias."""

    texto: str = ""
    sucesso: bool = False
    erro: str = ""
    modelo: str = ""
    tokens_entrada: int = 0
    tokens_saida: int = 0
    cache_lido: int = 0
    avisos: list[str] = field(default_factory=list)


def _montar_system(texto_pdf: str) -> list[dict]:
    """Bloco de sistema com a estrategia do cliente, marcado para cache.

    A estrategia e identica entre uma geracao e outra do mesmo cliente, entao o
    cache de prompt evita pagar o PDF inteiro a cada clique no botao.
    """
    estrategia = texto_pdf.strip() or (
        "(Nenhum documento de estrategia foi encontrado para este cliente. "
        "Trabalhe apenas com a referencia enviada pelo usuario e sinalize, ao "
        "final, que a estrategia nao estava disponivel.)"
    )
    return [
        {
            "type": "text",
            "text": SYSTEM_PROMPT.format(texto_do_pdf_extraido=estrategia),
            "cache_control": {"type": "ephemeral"},
        }
    ]


def _montar_mensagem(referencia: str, nome_cliente: str) -> list[dict]:
    conteudo = (
        f"Cliente: {nome_cliente}\n\n"
        "Referencias, links e ideias brutas enviadas pelo usuario:\n"
        f"<referencia>\n{referencia.strip()}\n</referencia>\n\n"
        "Gere as 3 ideias de conteudo seguindo exatamente a estrutura pedida."
    )
    return [{"role": "user", "content": conteudo}]


def gerar_sugestoes(
    api_key: str,
    texto_pdf: str,
    referencia: str,
    nome_cliente: str,
    modelo: str = MODELO_PADRAO,
) -> ResultadoIA:
    """Gera 3 ideias de conteudo a partir da estrategia do cliente + referencia.

    Nunca levanta excecao: erros de API viram `ResultadoIA(sucesso=False, erro=...)`
    para a interface exibir uma mensagem util.
    """
    if not api_key:
        return ResultadoIA(erro="Informe a chave da API da Anthropic na barra lateral.")
    if not referencia.strip():
        return ResultadoIA(erro="Cole ao menos uma referencia, link ou ideia bruta.")

    cliente = anthropic.Anthropic(api_key=api_key)
    system = _montar_system(texto_pdf)
    mensagens = _montar_mensagem(referencia, nome_cliente)

    try:
        resposta, avisos = _gerar(cliente, modelo, system, mensagens)
    except anthropic.AuthenticationError:
        return ResultadoIA(erro="Chave da API invalida ou sem permissao (401).")
    except anthropic.PermissionDeniedError:
        return ResultadoIA(erro="Esta chave nao tem permissao para usar este modelo (403).")
    except anthropic.NotFoundError:
        return ResultadoIA(erro=f"O modelo '{modelo}' nao esta disponivel para esta conta (404).")
    except anthropic.RateLimitError:
        return ResultadoIA(erro="Limite de requisicoes atingido (429). Tente de novo em alguns segundos.")
    except anthropic.APIStatusError as exc:
        return ResultadoIA(erro=f"A API respondeu com erro {exc.status_code}: {exc.message}")
    except anthropic.APIConnectionError:
        return ResultadoIA(erro="Nao foi possivel conectar a API da Anthropic. Verifique a internet.")

    if resposta.stop_reason == "refusal":
        return ResultadoIA(
            erro=(
                "O modelo recusou este pedido. Revise a referencia enviada e tente "
                "novamente com outro enquadramento."
            )
        )

    texto = "\n\n".join(
        bloco.text for bloco in resposta.content if getattr(bloco, "type", "") == "text"
    ).strip()

    if not texto:
        return ResultadoIA(erro="A API respondeu sem texto. Tente novamente.")

    if resposta.stop_reason == "max_tokens":
        avisos.append("A resposta atingiu o limite de tamanho e pode estar incompleta.")

    uso = resposta.usage
    return ResultadoIA(
        texto=texto,
        sucesso=True,
        modelo=getattr(resposta, "model", modelo),
        tokens_entrada=getattr(uso, "input_tokens", 0) or 0,
        tokens_saida=getattr(uso, "output_tokens", 0) or 0,
        cache_lido=getattr(uso, "cache_read_input_tokens", 0) or 0,
        avisos=avisos,
    )


def _gerar(cliente: anthropic.Anthropic, modelo: str, system: list[dict], mensagens: list[dict]):
    """Chama a API em streaming, com fallback de servidor quando disponivel.

    Streaming evita estourar o timeout HTTP em respostas longas; `get_final_message()`
    devolve a mensagem completa sem precisar tratar evento por evento.
    """
    avisos: list[str] = []
    try:
        with cliente.beta.messages.stream(
            model=modelo,
            max_tokens=MAX_TOKENS,
            betas=[BETA_FALLBACK],
            fallbacks="default",
            system=system,
            messages=mensagens,
            thinking={"type": "adaptive"},
        ) as stream:
            return stream.get_final_message(), avisos
    except anthropic.BadRequestError as exc:
        # Contas sem o beta de fallback liberado recusam o header. Nesse caso
        # repetimos na rota estavel em vez de falhar a geracao.
        if "anthropic-beta" not in str(exc).lower():
            raise
        avisos.append(
            "O fallback automatico de modelo nao esta habilitado nesta conta; "
            "a geracao seguiu sem ele."
        )

    with cliente.messages.stream(
        model=modelo,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=mensagens,
        thinking={"type": "adaptive"},
    ) as stream:
        return stream.get_final_message(), avisos
