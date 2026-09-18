"""Schemas das entregas da Fabrica de Ideias.

Os repositorios de referencia (ai-shorts-generator) provam o ponto: pedir texto
solto e depois tentar interpretar com regex e fragil. Eles declaram o formato da
resposta num schema e deixam a API garantir que ela chega valida.

Aqui a mesma ideia, com os campos espelhando 1 para 1 a estrutura que os prompts
em `prompts/` exigem. O roteiro chega estruturado, entao a interface consegue
montar o carrossel slide a slide e o Reels como tabela -- e o usuario copia cada
pedaco separado, que e como esse material e usado na pratica.
"""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

# Nota sobre os limites de lista abaixo: structured outputs nao aceita restricoes
# complexas de array, entao o SDK remove `minItems`/`maxItems` do schema enviado
# e passa a validar no cliente. Um limite apertado demais aqui nao faria o modelo
# obedecer -- so transformaria uma resposta boa em erro de validacao. Por isso as
# faixas sao largas: quem cobra as 7 telas e a estrutura obrigatoria do prompt.

# ---------------------------------------------------------------------------
# Carrossel
# ---------------------------------------------------------------------------
PapelSlide = Literal["HOOK", "AGITACAO", "SOLUCAO", "AUTORIDADE", "CTA"]


class SlideCarrossel(BaseModel):
    """Um slide do carrossel, com o papel que ele cumpre no roteiro."""

    numero: int = Field(..., description="Posicao do slide, comecando em 1")
    papel: PapelSlide = Field(
        ...,
        description=(
            "Funcao do slide na estrutura obrigatoria: HOOK (slide 1), "
            "AGITACAO (slide 2), SOLUCAO (slides 3 a 5, um passo por slide), "
            "AUTORIDADE (slide 6) e CTA (slide 7)."
        ),
    )
    titulo: str = Field(
        ...,
        description=(
            "Frase curta que aparece em destaque no slide, do jeito que vai para a "
            "arte. No slide 1 e o hook, com no maximo 10 palavras."
        ),
    )
    texto: str = Field(
        "",
        description=(
            "Texto de apoio do slide, em leitura rapida estilo fio do Twitter. "
            "Pode ficar vazio quando o titulo ja entrega a mensagem sozinho."
        ),
    )


class Carrossel(BaseModel):
    """Roteiro completo de um carrossel de Instagram."""

    tema: str = Field(..., description="O angulo escolhido, em uma linha")
    slides: List[SlideCarrossel] = Field(
        ...,
        min_length=3,
        max_length=7,
        description=(
            "Os slides na ordem, seguindo a estrutura obrigatoria (7 slides no "
            "roteiro completo: hook, agitacao, tres passos, autoridade e CTA)"
        ),
    )
    legenda: str = Field(
        ...,
        description="Legenda do post, pronta para colar no Instagram",
    )
    hashtags: List[str] = Field(
        default_factory=list,
        description="De 4 a 8 hashtags relevantes, sem o caractere #",
    )


# ---------------------------------------------------------------------------
# Reels
# ---------------------------------------------------------------------------
class CenaReels(BaseModel):
    """Uma linha da tabela do roteiro: o que aparece e o que se fala."""

    tempo: str = Field(
        ...,
        description="Faixa de tempo da cena, por exemplo '0-3s' ou '4-8s'",
    )
    visual: str = Field(
        ...,
        description=(
            "Coluna 'Visual (O que aparece na tela)': enquadramento, acao e o "
            "B-roll de apoio sugerido para este trecho."
        ),
    )
    audio: str = Field(
        ...,
        description=(
            "Coluna 'Audio (O que sera falado)': a fala exata, sem introducao do "
            "tipo 'Ola, meu nome e'."
        ),
    )


class Reels(BaseModel):
    """Roteiro completo de um Reels, com o fechamento em looping."""

    titulo_legenda: str = Field(
        ..., description="Titulo sugerido para a legenda do Reels"
    )
    cenas: List[CenaReels] = Field(
        ...,
        min_length=3,
        max_length=16,
        description="As linhas da tabela, em ordem cronologica",
    )
    explicacao_loop: str = Field(
        ...,
        description=(
            "Uma frase explicando como a ultima fala se conecta a primeira palavra "
            "do video, para o editor conferir o corte do looping."
        ),
    )
