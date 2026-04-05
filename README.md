# 📋 Documentação — jiraAPI

> Pipeline de dados que busca cards do Jira com status **"Concluído"** no dia atual, salva na camada **Bronze** (CSV local) e envia para a AWS S3. As camadas **Silver** e **Gold** são processadas automaticamente via **AWS Lambda**, formando uma arquitetura medalhão completa.

---

## 🏗️ Arquitetura Geral

```
python main.py  (execução manual, uma vez por dia)
  │
  └─ Busca cards concluídos HOJE no Jira
       └─ Salva: stories_bronze_YYYY-MM-DD.csv
            └─ Upload → s3://bronze-gp02/bronze/stories_bronze_YYYY-MM-DD.csv
                 │
                 └─ [Trigger automático] Lambda: bronze-to-silver
                      └─ Processa e salva → s3://silver-gp02/silver/stories_silver_YYYY-MM-DD.csv
                           │
                           └─ [Trigger automático] Lambda: silver-to-gold
                                └─ Enriquece e salva → s3://gold-gp02/gold/stories_gold_YYYY-MM-DD.csv
```

---

## ☁️ Infraestrutura AWS necessária

### 1. Buckets S3

Crie os três buckets abaixo na AWS antes de rodar a aplicação:

| Bucket | Finalidade |
|---|---|
| `bronze-gp02` | Recebe o CSV bruto gerado pelo `main.py` |
| `silver-gp02` | Recebe o CSV tratado pelo Lambda Silver |
| `gold-gp02` | Recebe o CSV enriquecido pelo Lambda Gold |

---

### 2. Funções Lambda

Crie duas funções Lambda com **Python 3.12**, **arquitetura x86_64** e **timeout de 30 segundos**:

#### Lambda 1 — `bronze-to-silver`
- **Código:** `lambda/lambda_function.py`
- **Trigger:** S3 → bucket `bronze-gp02`, prefix `bronze/stories_bronze_`, suffix `.csv`
- **Permissões:** `s3:GetObject` em `bronze-gp02` + `s3:PutObject` em `silver-gp02`
- **Layer:** `AWSSDKPandas-Python314` (ou Python312)

#### Lambda 2 — `silver-to-gold`
- **Código:** `lambda/lambda_gold.py`
- **Trigger:** S3 → bucket `silver-gp02`, prefix `silver/stories_silver_`, suffix `.csv`
- **Permissões:** `s3:GetObject` em `silver-gp02` + `s3:PutObject` em `gold-gp02`
- **Layer:** `AWSSDKPandas-Python314` (ou Python312)

> ⚠️ **Timeout mínimo recomendado: 30 segundos.** Com 1s a função será encerrada antes de concluir.

---

### 3. Credenciais AWS

As credenciais precisam estar configuradas no arquivo `.env` do projeto local.

> 📌 **Conta AWS Academy (Learner Lab):** as credenciais são **temporárias** e expiram a cada ~4 horas. Sempre que for rodar, atualize o `.env` com as credenciais do portal do Learner Lab (**AWS Details → Show**).

---

## 🚀 Passo a Passo — Como configurar e rodar

### 1. Pré-requisitos

- Python **3.10+** instalado
- Conta no Jira com acesso à API
- Um **API Token** gerado em: https://id.atlassian.com/manage-profile/security/api-tokens
- Conta AWS com os 3 buckets S3 e 2 Lambdas configurados (ver seção acima)

---

### 2. Instalar as dependências

```bash
pip install -r requirements.txt
```

| Biblioteca | Para que serve |
|---|---|
| `requests` | Chamadas HTTP para a API do Jira |
| `python-dotenv` | Carrega variáveis do arquivo `.env` |
| `pydantic` | Valida e tipifica os dados do Jira |
| `pandas` | Manipula e salva os dados em CSV |
| `boto3` | Faz upload dos arquivos para o S3 |

---

### 3. Configurar o arquivo `.env`

Crie (ou edite) o arquivo `.env` na raiz do projeto:

```env
# ── Jira ──────────────────────────────────
JIRA_URL=https://sua-empresa.atlassian.net
JIRA_EMAIL=seu-email@empresa.com
JIRA_API_TOKEN=seu_token_aqui
JIRA_PROJECT_KEY=SCRUM

# ── AWS S3 ────────────────────────────────
AWS_ACCESS_KEY_ID=ASIA...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...        # Obrigatório para AWS Academy
AWS_REGION=us-east-1
AWS_S3_BUCKET=bronze-gp02
```

> ⚠️ **Nunca suba o `.env` para o repositório.** Ele já está no `.gitignore`.

---

### 4. Rodar a aplicação

```bash
python main.py
```

A aplicação executa **uma única vez**, buscando todos os cards concluídos **no dia atual**, e encerra automaticamente após o upload para o S3.

**Exemplo de saída esperada:**

```
INFO | main.py | [Main] Buscando cards concluídos em 05/04/2026...
INFO | monitor.py | NOVO CARD NO STATUS 'CONCLUÍDO': 10042
INFO | bronze.py | Arquivo 'stories_bronze_2026-04-05.csv' criado com sucesso.
INFO | main.py | [Main] Iniciando upload → s3://bronze-gp02/bronze/stories_bronze_2026-04-05.csv
INFO | s3_uploader.py | [S3] Upload concluído com sucesso!
INFO | main.py | [Main] ✅ Pipeline concluída com sucesso!
```

---

## 🗂️ Estrutura do Projeto

```
jiraAPI/
│
├── main.py                      # Ponto de entrada — roda manualmente uma vez por dia
├── requirements.txt             # Dependências Python
├── .env                         # Variáveis de ambiente (não versionar)
│
├── config/
│   └── config.py                # Centraliza e valida variáveis do .env (Jira + AWS)
│
├── pipeline/
│   ├── bronze.py                # Camada Bronze: salva CSV com data no nome
│   ├── silver.py                # Camada Silver: limpeza e padronização
│   └── enrich_JIRA.py           # Camada Gold: enriquecimento e métricas analíticas
│
├── service/
│   ├── jira_client.py           # Comunicação com a API REST do Jira
│   ├── monitor.py               # Orquestra a busca de cards (JQL filtrado para hoje)
│   └── s3_uploader.py           # Upload de arquivos para o S3
│
├── lambda/
│   ├── lambda_function.py       # Lambda Bronze → Silver (cola no console AWS)
│   └── lambda_gold.py           # Lambda Silver → Gold (cola no console AWS)
│
├── models/
│   └── jira_models.py           # Modelos de dados Pydantic (Issue, Subtask)
│
└── util/
    ├── jira_util.py             # Parse do JSON do Jira + conversão de ADF para texto
    └── log.py                   # Sistema de logging centralizado
```

---

## 📁 Descrição dos Principais Arquivos

### `main.py` — Ponto de Entrada

Executado **manualmente uma vez por dia**. Realiza as seguintes etapas em sequência:

1. Valida as credenciais (Jira + AWS) carregadas do `.env`
2. Busca no Jira todos os cards com status `"Concluído"` **alterados hoje** (`statusCategoryChangedDate >= startOfDay()`)
3. Salva os dados em `stories_bronze_YYYY-MM-DD.csv`
4. Faz upload para `s3://bronze-gp02/bronze/stories_bronze_YYYY-MM-DD.csv`
5. Encerra a execução

---

### 📁 `pipeline/`

| Arquivo | Camada | O que faz |
|---|---|---|
| `bronze.py` | Bronze | Salva os dados brutos do Jira em CSV com a data no nome |
| `silver.py` | Silver | Normaliza datas, textos, assignee e deduplica por `card_id` |
| `enrich_JIRA.py` | Gold | Gera métricas de qualidade, lead time, score e complexidade textual |

---

### 📁 `lambda/`

| Arquivo | Trigger | Entrada | Saída |
|---|---|---|---|
| `lambda_function.py` | PutObject em `bronze-gp02` | `stories_bronze_YYYY-MM-DD.csv` | `stories_silver_YYYY-MM-DD.csv` em `silver-gp02` |
| `lambda_gold.py` | PutObject em `silver-gp02` | `stories_silver_YYYY-MM-DD.csv` | `stories_gold_YYYY-MM-DD.csv` em `gold-gp02` |

---

### 📁 `service/`

#### `s3_uploader.py`
Faz o upload de arquivos locais para o S3 usando `boto3`. Usa as credenciais definidas no `.env` (incluindo `AWS_SESSION_TOKEN` para contas Academy).

#### `monitor.py`
Monta a JQL e busca cards concluídos **apenas no dia atual**. Aciona `save_bronze()` para cada card novo encontrado.

#### `jira_client.py`
Comunicação direta com a API REST do Jira via `HTTPBasicAuth`.

---

### 📁 `util/`

#### `jira_util.py`
| Função | Descrição |
|---|---|
| `parse_issue(data)` | Converte o JSON bruto da API em um objeto `Issue` tipado |
| `adf_to_text(adf)` | Converte o formato ADF (Atlassian Document Format) para texto puro |

#### `log.py`
Sistema de logging centralizado com data/hora, nível, arquivo e linha.

---

## 🔄 Fluxo Detalhado de Execução

```
python main.py
  │
  ├─ Config.validate()
  │    └─ Verifica Jira + AWS credentials
  │
  ├─ JiraMonitor.process_new_cards()
  │    └─ JQL: status = "Concluído" AND statusCategoryChangedDate >= startOfDay()
  │         └─ Para cada card novo:
  │              ├─ get_issue_details() → JSON completo
  │              ├─ parse_issue()       → objeto Issue (Pydantic)
  │              └─ save_bronze()       → stories_bronze_YYYY-MM-DD.csv
  │
  └─ S3Uploader.upload_file()
       └─ s3://bronze-gp02/bronze/stories_bronze_YYYY-MM-DD.csv
            │
            └─ [AWS Event] Lambda bronze-to-silver dispara
                 └─ Lê bronze do S3 → aplica Silver → salva em silver-gp02
                      │
                      └─ [AWS Event] Lambda silver-to-gold dispara
                           └─ Lê silver do S3 → enriquece → salva em gold-gp02
```
