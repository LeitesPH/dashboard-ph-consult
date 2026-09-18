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
| `cores.py` | Conversoes de cor e diagnostico de legibilidade do par de cores |
| `ia.py` | Chamada a API da Anthropic e o prompt de sistema |
| `views/` | Uma pagina por arquivo |

> A pasta se chama `views/` e nao `pages/` de proposito: o Streamlit trata
> `pages/` como navegacao automatica, o que brigaria com o menu da barra lateral.

## Decisoes que valem saber

**As cores do cliente mandam nos graficos.** Toda serie e pintada com a Cor
Primaria ou a Secundaria do `config.json` — nenhuma paleta padrao do Plotly
aparece no relatorio.

**O cadastro avisa quando o par de cores nao funciona.** Como as cores sao
escolhidas livremente, a tela de cadastro mede a distancia entre elas (inclusive
sob daltonismo) e o contraste com o fundo, mostrando uma previa do grafico. O
aviso nao bloqueia o cadastro — a marca do cliente continua sendo a marca dele.

**Cada metrica no seu proprio grafico quando as escalas sao diferentes.**
Interacoes (milhares) e cliques no link (centenas) aparecem separados: no mesmo
eixo, a serie menor viraria uma faixa rente ao zero. Nenhum grafico usa dois
eixos y.

**A estrategia do cliente vai em cache de prompt.** O PDF e identico entre uma
geracao e outra, entao ele e marcado como prefixo cacheavel — o custo por clique
cai bastante depois da primeira geracao. O rodape mostra quantos tokens vieram
do cache.

## Modelo usado

`claude-opus-5`, via streaming. A geracao pede o fallback de servidor quando a
conta tem o recurso liberado e, quando nao tem, repete a chamada sem ele — os
dois caminhos estao em `ia.py`.
