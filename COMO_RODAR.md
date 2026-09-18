# Como rodar o dashboard

## 1. Instalar (so na primeira vez)

Abra o terminal na pasta do projeto e rode:

```bash
python3 -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Rodar

```bash
streamlit run app.py
```

O navegador abre sozinho em http://localhost:8501

## 3. Usar

1. **Barra lateral** — cole sua chave da Anthropic no campo "Chave da API".
   (Para nao colar toda vez: crie um arquivo `.env` com `ANTHROPIC_API_KEY=sk-ant-...`)
2. **1. Novo Cliente** — cadastre o cliente com o PDF de estrategia e as duas
   cores da marca dele.
3. **2. Relatorios** — lance as metricas da semana e veja os graficos do mes.
4. **3. Fabrica de Ideias** — escolha o modo (Ideias, Carrossel ou Reels), cole
   a referencia e gere.

## Onde ficam os dados

Tudo em `clientes/<nome-do-cliente>/`:

- `estrategia.pdf` — o documento de posicionamento
- `config.json` — nome e cores da marca
- `metricas.csv` — o historico semanal
- `conteudos/` — cada roteiro gerado, salvo em JSON

Nada disso sai da sua maquina.
