"""Utilitarios de cor para os graficos do dashboard.

O sistema obriga os graficos a usarem as cores da marca de cada cliente
(`config.json`). Como essas cores sao escolhidas livremente no cadastro, este
modulo tambem diagnostica se o par escolhido continua legivel quando as duas
cores aparecem lado a lado num grafico -- inclusive para quem tem daltonismo.

A matematica segue o padrao usado na validacao de paletas:
- distancia Delta E = distancia euclidiana no espaco OKLab, multiplicada por 100;
- simulacao de daltonismo por Machado, Oliveira & Fernandes (2009), severidade 1.0;
- contraste WCAG contra a superficie do grafico.
"""

from __future__ import annotations

import math
import re

# ---------------------------------------------------------------------------
# Limiares (mesma calibragem da simulacao Machado 2009)
# ---------------------------------------------------------------------------
CVD_ALVO = 8.0        # Delta E minimo desejado sob protanopia/deuteranopia
CVD_PISO = 6.0        # abaixo disso o par e considerado indistinguivel
PISO_VISAO_NORMAL = 15.0  # Delta E minimo sob visao normal
CONTRASTE_MIN = 3.0   # contraste WCAG minimo de uma marca contra o fundo
CONTRASTE_PISO = 1.6  # abaixo disso a marca some do fundo, mesmo com rotulo
SUPERFICIE_CLARA = "#ffffff"

# ---------------------------------------------------------------------------
# Marca PH Consult -- cores extraidas da logo (a montanha com a bandeira)
# ---------------------------------------------------------------------------
# Papel de cada uma, e o motivo:
#   MARINHO  corpo da montanha. Contraste 11.6:1 no branco -- e a cor de texto,
#            de titulo e de botao primario.
#   CORAL    a bandeira no cume. Croma alto, contraste 2.7:1 no branco -- otima
#            como acento e como serie de grafico (sempre com rotulo direto do
#            lado), nunca como fundo de texto pequeno.
#   CREME    a neve. Fundo da barra lateral e das superficies de apoio.
#   AZUL_*   as faces iluminadas do pico, para estados e realces intermediarios.
MARINHO = "#1b3a5c"
MARINHO_ESCURO = "#142c46"
AZUL_MEDIO = "#3d6189"
AZUL_CLARO = "#5c7da5"
CORAL = "#ff6f61"
CORAL_ESCURO = "#e85f52"
CREME = "#f2f0e6"
CREME_BORDA = "#e2ded0"

# Sugestao de cores para um cliente novo: o par da propria PH Consult.
# Separacao sob daltonismo de 29.8 (o alvo e 8), entao funciona como par de
# series desde o primeiro cadastro -- e o usuario troca pelas cores do cliente.
COR_PRIMARIA_PADRAO = MARINHO
COR_SECUNDARIA_PADRAO = CORAL

# Tinta do texto e elementos estruturais (nunca recebem a cor da serie).
# Todas puxadas para o azul da marca, para o grafico conversar com a interface.
TINTA_PRIMARIA = MARINHO
TINTA_SECUNDARIA = "#4a6480"   # 6.1:1 no branco
TINTA_SUAVE = "#7b8ea3"        # 3.4:1 -- so para rotulo de eixo e legenda fina
GRADE = "#dfe4ea"

_MACHADO = {
    "protan": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deutan": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
}

_HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")
_ESPACOS = (
    " \t\n\v\f\r         "
    "        　"
)


def normalizar_hex(valor: object, padrao: str = COR_PRIMARIA_PADRAO) -> str:
    """Devolve a cor no formato `#rrggbb` minusculo, ou `padrao` se for invalida.

    Toda cor vinda de arquivo ou formulario passa por aqui antes de qualquer
    conta: sem isso um `config.json` editado a mao propaga valores invalidos
    silenciosamente ate o grafico.
    """
    if not isinstance(valor, str):
        return padrao
    limpo = valor.strip(_ESPACOS)
    if not _HEX_RE.match(limpo):
        return padrao
    return "#" + limpo.lstrip("#").lower()


def _srgb(hexa: str) -> tuple[float, float, float]:
    h = hexa.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _para_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear(hexa: str) -> tuple[float, float, float]:
    r, g, b = _srgb(hexa)
    return _para_linear(r), _para_linear(g), _para_linear(b)


def _de_linear(c: float) -> float:
    c = min(1.0, max(0.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def _oklab(rgb_linear: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = rgb_linear
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def oklch(hexa: str) -> tuple[float, float]:
    """Luminosidade (L) e croma (C) da cor no espaco OKLCH."""
    _l, a, b = _oklab(_linear(hexa))
    return _l, math.hypot(a, b)


def _luminancia(hexa: str) -> float:
    r, g, b = _linear(hexa)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(cor_a: str, cor_b: str) -> float:
    """Razao de contraste WCAG entre duas cores (1.0 a 21.0)."""
    lum_a, lum_b = _luminancia(cor_a), _luminancia(cor_b)
    claro, escuro = max(lum_a, lum_b), min(lum_a, lum_b)
    return (claro + 0.05) / (escuro + 0.05)


def _simular(hexa: str, tipo: str) -> tuple[float, float, float]:
    r, g, b = _linear(hexa)
    m = _MACHADO[tipo]
    return tuple(  # type: ignore[return-value]
        min(1.0, max(0.0, linha[0] * r + linha[1] * g + linha[2] * b)) for linha in m
    )


def delta_e(cor_a: str, cor_b: str, tipo: str | None = None) -> float:
    """Distancia perceptual entre duas cores (OKLab x100).

    Com `tipo` ("protan" ou "deutan") a distancia e medida sob a visao simulada.
    """
    lab_a = _oklab(_simular(cor_a, tipo) if tipo else _linear(cor_a))
    lab_b = _oklab(_simular(cor_b, tipo) if tipo else _linear(cor_b))
    return 100 * math.dist(lab_a, lab_b)


def mesclar(cor_a: str, cor_b: str, t: float) -> str:
    """Mistura duas cores em espaco linear (`t=0` -> cor_a, `t=1` -> cor_b)."""
    t = min(1.0, max(0.0, t))
    a, b = _linear(cor_a), _linear(cor_b)
    canais = (_de_linear(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return "#" + "".join(f"{round(c * 255):02x}" for c in canais)


def clarear(hexa: str, fator: float = 0.5) -> str:
    """Versao mais clara da cor -- usada em areas de apoio, nunca em series."""
    return mesclar(hexa, "#ffffff", fator)


def com_alfa(hexa: str, alfa: float) -> str:
    """Converte `#rrggbb` para `rgba(...)` com a transparencia informada."""
    r, g, b = (int(hexa.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alfa:.3f})"


def diagnosticar_par(
    primaria: str,
    secundaria: str,
    superficie: str = SUPERFICIE_CLARA,
) -> dict:
    """Avalia se as duas cores da marca funcionam juntas num grafico.

    Devolve um dicionario com as metricas e um `status`:
    `ok`, `atencao` (legivel so com rotulo/apoio) ou `critico`.
    """
    primaria = normalizar_hex(primaria, COR_PRIMARIA_PADRAO)
    secundaria = normalizar_hex(secundaria, COR_SECUNDARIA_PADRAO)

    cvd = min(delta_e(primaria, secundaria, "protan"), delta_e(primaria, secundaria, "deutan"))
    normal = delta_e(primaria, secundaria)
    contraste_primaria = contraste(primaria, superficie)
    contraste_secundaria = contraste(secundaria, superficie)

    avisos: list[str] = []
    observacoes: list[str] = []
    status = "ok"

    if normal < PISO_VISAO_NORMAL:
        status = "critico"
        avisos.append(
            f"As duas cores sao muito parecidas entre si (Delta E {normal:.1f}; "
            f"minimo {PISO_VISAO_NORMAL:.0f}). Nos graficos com duas series elas "
            "vao se confundir mesmo para quem enxerga todas as cores."
        )
    if cvd < CVD_PISO:
        status = "critico"
        avisos.append(
            f"Sob daltonismo (protanopia/deuteranopia) as cores praticamente se "
            f"fundem (Delta E {cvd:.1f}; minimo {CVD_PISO:.0f})."
        )
    elif cvd < CVD_ALVO:
        status = "atencao" if status == "ok" else status
        avisos.append(
            f"Sob daltonismo as cores ficam proximas (Delta E {cvd:.1f}; ideal "
            f"{CVD_ALVO:.0f}). Os graficos ja trazem rotulo e legenda, entao a "
            "leitura continua possivel sem depender da cor."
        )

    # Contraste com o fundo. Os graficos deste dashboard sempre imprimem o valor
    # ao lado da marca e repetem os numeros na tabela, entao um contraste entre
    # CONTRASTE_PISO e CONTRASTE_MIN nao impede a leitura -- vira observacao.
    # Abaixo do piso a barra praticamente some do fundo, e ai e aviso mesmo.
    for nome, valor in (("primaria", contraste_primaria), ("secundaria", contraste_secundaria)):
        if valor < CONTRASTE_PISO:
            status = "atencao" if status == "ok" else status
            avisos.append(
                f"A cor {nome} quase desaparece no fundo branco ({valor:.1f}:1). "
                "Barras nessa cor somem na tela e no relatorio impresso."
            )
        elif valor < CONTRASTE_MIN:
            observacoes.append(
                f"A cor {nome} tem contraste suave com o fundo ({valor:.1f}:1). "
                "Como todo grafico aqui traz o numero ao lado da barra e a tabela "
                "logo acima, a leitura nao depende do preenchimento."
            )

    return {
        "primaria": primaria,
        "secundaria": secundaria,
        "delta_cvd": cvd,
        "delta_normal": normal,
        "contraste_primaria": contraste_primaria,
        "contraste_secundaria": contraste_secundaria,
        "status": status,
        "avisos": avisos,
        "observacoes": observacoes,
    }
