# 📋 Documentação — jiraAPI

> Monitor automático de cards do Jira que detecta issues com status **"Concluído"** e salva os dados em arquivos CSV (camada Bronze).

---

## 🚀 Passo a Passo — Como configurar e rodar o app

### 1. Pré-requisitos

- Python **3.10+** instalado
- Conta no Jira com acesso à API
- Um **API Token** gerado em: https://id.atlassian.com/manage-profile/security/api-tokens

---

### 2. Instalar as dependências

No terminal, dentro da pasta do projeto, execute:

```bash
pip install -r requirements.txt
```

As bibliotecas instaladas são:

| Biblioteca | Para que serve |
|---|---|
| `requests` | Fazer chamadas HTTP para a API do Jira |
| `python-dotenv` | Carregar variáveis de ambiente do arquivo `.env` |
| `pydantic` | Validar e tipificar os dados retornados pelo Jira |
| `pandas` | Manipular e salvar os dados em arquivos CSV |

---

### 3. Configurar o arquivo `.env`

Crie (ou edite) o arquivo `.env` na raiz do projeto com o seguinte conteúdo:

```env
# URL base da sua instância do Jira
JIRA_URL=https://sua-empresa.atlassian.net

# E-mail da conta usada para gerar o token
JIRA_EMAIL=seu-email@empresa.com

# Token de API gerado no painel da Atlassian
JIRA_API_TOKEN=seu_token_aqui

# Chave do projeto Jira a ser monitorado (ex: SCRUM, PROJ, DEV)
JIRA_PROJECT_KEY=SCRUM

# Intervalo, em segundos, entre cada verificação (padrão: 30)
POLL_INTERVAL=5
```

> ⚠️ **Nunca suba o `.env` para o repositório.** Certifique-se de que ele está listado no `.gitignore`.

---

### 4. Rodar a aplicação

```bash
python main.py
```

A aplicação vai iniciar o monitoramento e exibir logs no terminal. Para interromper, pressione **CTRL+C**.

**Exemplo de saída esperada:**

```
2025-01-01 12:00:00 | INFO | monitor.py:60 | [*] Iniciando monitoramento do Jira...
2025-01-01 12:00:00 | INFO | monitor.py:61 | [*] Status alvo: 'Concluído'
2025-01-01 12:00:00 | INFO | monitor.py:62 | [*] Intervalo: 5 segundos
2025-01-01 12:00:00 | INFO | monitor.py:63 | [*] Pressione CTRL+C para parar.
```

---

### 5. Verificar os dados gerados

Após detectar cards, dois arquivos CSV serão gerados (ou atualizados) na raiz do projeto:

| Arquivo | Conteúdo |
|---|---|
| `stories_bronze.csv` | Dados das histórias (cards) detectados |
| `subtasks_bronze.csv` | Subtasks relacionadas a cada card |

---

## 🗂️ Estrutura do Projeto

```
jiraAPI/
│
├── main.py                  # Ponto de entrada da aplicação
├── requirements.txt         # Dependências Python
├── .env                     # Variáveis de ambiente (não versionar)
├── stories_bronze.csv       # Saída: dados das histórias (gerado automaticamente)
├── subtasks_bronze.csv      # Saída: dados das subtasks (gerado automaticamente)
│
├── config/
│   └── config.py            # Centraliza e valida as variáveis de ambiente
│
├── jira/
│   ├── jira_client.py       # Comunicação direta com a API REST do Jira
│   └── monitor.py           # Orquestra o loop de monitoramento
│
├── models/
│   └── jira_models.py       # Modelos de dados (Pydantic)
│
├── pipeline/
│   └── bronze.py            # Camada Bronze: salva dados brutos em CSV
│
└── util/
    ├── jira_util.py         # Funções de parsing dos dados do Jira
    └── log.py               # Sistema de logging centralizado
```

---

## 📁 Descrição das Pastas e Arquivos

---

### `main.py` — Ponto de Entrada

Arquivo principal que inicializa a aplicação. Executa as seguintes etapas em sequência:

1. **Valida** as credenciais carregadas do `.env` via `Config.validate()`
2. **Instancia** o `JiraClient` com as credenciais
3. **Instancia** o `JiraMonitor` configurado para detectar cards com status `"Concluído"`
4. **Inicia** o loop infinito de monitoramento com `monitor.start_monitoring()`

---

### 📁 `config/`

#### `config.py` — Classe `Config`

Centraliza **todas** as configurações da aplicação lidas do arquivo `.env`.

| Atributo | Variável de Ambiente | Descrição |
|---|---|---|
| `JIRA_URL` | `JIRA_URL` | URL base da instância Jira |
| `JIRA_EMAIL` | `JIRA_EMAIL` | E-mail de autenticação |
| `JIRA_API_TOKEN` | `JIRA_API_TOKEN` | Token da API Atlassian |
| `JIRA_PROJECT_KEY` | `JIRA_PROJECT_KEY` | Chave do projeto a monitorar |
| `POLL_INTERVAL` | `POLL_INTERVAL` | Intervalo em segundos entre verificações |

**Método importante:**
- `validate()` — Verifica se as variáveis obrigatórias (`JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`) estão presentes. Lança `ValueError` se alguma estiver faltando.

---

### 📁 `jira/`

#### `jira_client.py` — Classe `JiraClient`

Responsável pela **comunicação direta com a API REST do Jira**. Utiliza autenticação via `HTTPBasicAuth` (e-mail + token).

| Método | Descrição |
|---|---|
| `search_issues(jql_query, max_results)` | Busca cards usando JQL (Jira Query Language) |
| `get_issue_details(issue_key)` | Busca o JSON completo de um card pelo seu ID e retorna um objeto `Issue` já parseado |

---

#### `monitor.py` — Classe `JiraMonitor`

Responsável por **orquestrar o monitoramento contínuo**. Mantém um `set` de IDs já processados para evitar reprocessar o mesmo card.

| Método | Descrição |
|---|---|
| `build_jql()` | Monta a query JQL com o status-alvo e a chave do projeto |
| `process_new_cards()` | Executa a busca e filtra apenas cards ainda não processados |
| `_handle_matched_issue(issue_key)` | Pega os detalhes completos do card e aciona o `save_bronze()` |
| `start_monitoring()` | Loop infinito: chama `process_new_cards()` e dorme por `POLL_INTERVAL` segundos |

---

### 📁 `models/`

#### `jira_models.py` — Classes `Issue` e `Subtask`

Define os **modelos de dados** usando **Pydantic**, garantindo tipagem e validação automática.

**`Subtask`**
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | `str` | ID interno da subtask no Jira |
| `key` | `str` | Chave legível (ex: `SCRUM-42`) |
| `descricao` | `str` | Título/sumário da subtask |

**`Issue`**
| Campo | Tipo | Descrição |
|---|---|---|
| `id` | `str` | ID interno do card no Jira |
| `descricao` | `str` (opcional) | Texto da descrição do card (convertido de ADF para texto puro) |
| `data_entrega` | `str` (opcional) | Data de entrega (`duedate`) |
| `subtasks` | `List[Subtask]` | Lista de subtasks vinculadas |

---

### 📁 `pipeline/`

#### `bronze.py` — Função `save_bronze(issue)`

Implementa a **camada Bronze** da pipeline de dados. Recebe um objeto `Issue` e persiste os dados brutos em arquivos CSV, sem nenhuma transformação.

- Salva os dados da história em `stories_bronze.csv`
- Salva as subtasks em `subtasks_bronze.csv`
- Se o arquivo já existir, **acrescenta** os dados (modo `append`); se não existir, **cria** o arquivo com cabeçalho

---

### 📁 `util/`

#### `jira_util.py` — Funções `parse_issue()` e `adf_to_text()`

Contém funções auxiliares de **transformação e parsing** dos dados retornados pela API.

| Função | Descrição |
|---|---|
| `parse_issue(data)` | Recebe o JSON bruto da API do Jira e converte para um objeto `Issue` tipado |
| `adf_to_text(adf)` | Converte o formato de descrição do Jira (**Atlassian Document Format**) em texto puro, percorrendo recursivamente os nós do documento |

---

#### `log.py` — Classe `Log`

Sistema de **logging centralizado** para a aplicação, usando o módulo `logging` do Python. Exibe data/hora, nível do log, arquivo e número da linha.

| Método estático | Nível | Uso |
|---|---|---|
| `Log.info(msg)` | INFO | Mensagens de progresso normal |
| `Log.warning(msg)` | WARNING | Avisos não críticos |
| `Log.error(msg)` | ERROR | Erros recuperáveis |
| `Log.debug(msg)` | DEBUG | Informações detalhadas para desenvolvimento |
| `Log.critical(msg)` | CRITICAL | Erros fatais |

---

## 🔄 Fluxo de Execução

```
main.py
  │
  ├─ Config.validate()           → Valida credenciais do .env
  │
  ├─ JiraClient(url, email, token)
  │
  └─ JiraMonitor.start_monitoring()
       │
       └─ [Loop a cada POLL_INTERVAL segundos]
            │
            ├─ build_jql()         → Monta a query JQL
            ├─ search_issues()     → Chama a API do Jira
            │
            └─ [Para cada card novo encontrado]
                 │
                 ├─ get_issue_details()  → Busca JSON completo do card
                 ├─ parse_issue()        → Converte JSON → objeto Issue (Pydantic)
                 └─ save_bronze()        → Salva em stories_bronze.csv e subtasks_bronze.csv
```
