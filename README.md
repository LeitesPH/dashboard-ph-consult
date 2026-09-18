# Dashboard de Midias Sociais — multi-tenant, local

Dashboard em Streamlit para gestao de midias sociais (foco em Instagram) com
multiplos clientes. Nao usa banco de dados: cada cliente e uma pasta em
`clientes/`, nesta maquina.

## O que ele faz

1. **Novo Cliente** — cadastra o cliente com o PDF de estrategia e as cores da marca.
2. **Relatorios** — lancamento semanal de metricas e leitura mensal em graficos
   pintados com as cores daquele cliente.
3. **Fabrica de Ideias** — cruza o PDF de estrategia com as suas referencias e
   gera 3 ideias de conteudo usando a API da Anthropic.

## Instalacao

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Chave da API (opcional — da para digitar na barra lateral):

```bash
cp .env.example .env               # e preencha ANTHROPIC_API_KEY
```

## Execucao

```bash
streamlit run app.py
```

O navegador abre em `http://localhost:8501`.

## Como os dados ficam em disco

```
clientes/
└── nome-do-cliente/
    ├── estrategia.pdf     # documento de posicionamento
    ├── config.json        # nome de exibicao + cores da marca
    └── metricas.csv       # uma linha por semana
```

O nome da pasta e uma versao sem acentos nem espacos do nome digitado; o nome
original fica no `config.json` e e o que aparece na interface.

`metricas.csv` tem as colunas: `data_registro`, `mes_referencia` (`AAAA-MM`),
`semana` (1 a 4), `alcance`, `visualizacoes`, `interacoes`, `cliques_link` e
`novos_seguidores`. E um CSV comum — da para abrir no Excel ou editar a mao.

A pasta `clientes/` esta no `.gitignore`: os dados dos clientes ficam na sua
maquina e nao vao para o repositorio.

## Estrutura do codigo

| Arquivo | Responsabilidade |
|---|---|
| `app.py` | Ponto de entrada: barra lateral (Cliente Ativo, navegacao, chave da API) e roteamento |
| `utils.py` | Pastas, `config.json`, `metricas.csv` e extracao de texto do PDF |
| `graficos.py` | Graficos Plotly, sempre com as cores da marca do cliente |
| `cores.py` | Paleta da PH Consult, conversoes de cor e diagnostico de legibilidade |
| `estilo.py` | Identidade visual da interface (CSS, logo, tipografia) |
| `ia.py` | Chamada a API da Anthropic e o prompt de sistema |
| `modelos.py` | Schemas das entregas (carrossel e Reels) validados na resposta da API |
| `prompts/` | Prompts de sistema de cada gerador, em Markdown editavel |
| `views/` | Uma pagina por arquivo |
| `assets/` | Logo da PH Consult (versao da barra lateral e icone da aba) |

> A pasta se chama `views/` e nao `pages/` de proposito: o Streamlit trata
> `pages/` como navegacao automatica, o que brigaria com o menu da barra lateral.

## Identidade visual

As cores foram tiradas diretamente da logo (a montanha com a bandeira) e vivem
em `cores.py`:

| Cor | Hex | Onde aparece |
|---|---|---|
| Marinho | `#1b3a5c` | corpo da montanha — texto, titulos e botao primario |
| Coral | `#ff6f61` | a bandeira no cume — acentos, em doses pequenas |
| Creme | `#f2f0e6` | a neve — barra lateral e superficies de apoio |
| Azul medio / claro | `#3d6189` / `#5c7da5` | faces iluminadas do pico |

O marinho tem 11,6:1 de contraste no branco, entao carrega o texto sem esforco.
O coral tem 2,7:1 — otimo como acento e como serie de grafico (que sempre traz o
numero ao lado), mas nunca como fundo de texto pequeno.

Esse par tambem e a sugestao inicial de cores para um cliente novo: a separacao
entre marinho e coral sob daltonismo e de 29,8 (o alvo do criterio e 8). O
usuario troca pelas cores do cliente no cadastro.

## Decisoes que valem saber

**As cores do cliente mandam nos graficos.** Toda serie e pintada com a Cor
Primaria ou a Secundaria do `config.json` — nenhuma paleta padrao do Plotly
aparece no relatorio.

**O cadastro avisa quando o par de cores nao funciona.** Como as cores sao
escolhidas livremente, a tela de cadastro mede a distancia entre elas (inclusive
sob daltonismo) e o contraste com o fundo, mostrando uma previa do grafico. O
aviso nao bloqueia o cadastro — a marca do cliente continua sendo a marca dele.
Contraste suave vira observacao, e nao alerta: os graficos sempre imprimem o
numero ao lado da barra, entao a leitura nao depende do preenchimento. So quando
a cor praticamente some do fundo (abaixo de 1,6:1) e que vira aviso de verdade.

**Cada metrica no seu proprio grafico quando as escalas sao diferentes.**
Interacoes (milhares) e cliques no link (centenas) aparecem separados: no mesmo
eixo, a serie menor viraria uma faixa rente ao zero. Nenhum grafico usa dois
eixos y.

**A estrategia do cliente vai em cache de prompt.** O PDF e identico entre uma
geracao e outra, entao ele e marcado como prefixo cacheavel — o custo por clique
cai bastante depois da primeira geracao. O rodape mostra quantos tokens vieram
do cache.

## Os tres geradores

A Fabrica de Ideias tem tres modos, todos partindo do mesmo par (estrategia em
PDF + referencia colada):

| Modo | Entrega |
|---|---|
| Ideias de conteudo | 3 ideias para escolher um caminho antes de escrever |
| Carrossel | Roteiro de ate 7 slides: hook, agitacao, 3 passos, autoridade e CTA |
| Reels | Roteiro de 30 a 45s em tabela (visual/audio), com B-rolls e looping |

**Os prompts ficam em `prompts/*.md`, nao no codigo.** Quem ajusta esse texto e
o estrategista, entao mudar o tom de voz de um gerador e editar um Markdown --
nao mexer em Python. Os arquivos estao exatamente como foram escritos.

**A resposta vem validada por schema.** Em vez de pedir texto e interpretar com
regex, os modos Carrossel e Reels declaram o formato em `modelos.py` e a API
devolve a estrutura ja validada (`messages.parse`). E por isso que a tela
consegue montar o carrossel slide a slide e o Reels como tabela de gravacao,
com cada pedaco pronto para copiar.

**Cada geracao fica salva** em `clientes/<cliente>/conteudos/`, entao fechar a
aba nao joga fora um roteiro que custou uma chamada de API.

## Modelo usado

`claude-opus-5`, via streaming. A geracao pede o fallback de servidor quando a
conta tem o recurso liberado e, quando nao tem, repete a chamada sem ele — os
dois caminhos estao em `ia.py`.
