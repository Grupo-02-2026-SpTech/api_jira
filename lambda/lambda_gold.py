"""
lambda/lambda_gold.py
----------------------
AWS Lambda — Camada Gold da arquitetura medalhão.

Trigger: S3 Event (PutObject) no bucket silver-gp02
  - Recebe o arquivo stories_silver_YYYY-MM-DD.csv
  - Aplica os mesmos tratamentos do pipeline/enrich_JIRA.py
  - Gera stories_gold_YYYY-MM-DD.csv
  - Faz upload para o bucket gold-gp02
"""

import io
import re
import os
import warnings
import boto3
import pandas as pd

warnings.filterwarnings("ignore")


# ── Clientes AWS ───────────────────────────────────────────────────────────────

s3 = boto3.client("s3")

GOLD_BUCKET = "gold-gp02"


# ── Complexidade Textual ───────────────────────────────────────────────────────

def classificar_complexidade(palavras):
    if palavras == 0:
        return "Vazio"
    elif palavras < 20:
        return "Baixa"
    elif palavras < 50:
        return "Média"
    else:
        return "Alta"


# ── Qualidade da Descrição ─────────────────────────────────────────────────────

def qualidade_descricao(row):
    if row["descricao_vazia"]:
        return "Crítica"
    elif row["descricao_curta"]:
        return "Ruim"
    elif row["complexidade_textual"] == "Média":
        return "Boa"
    elif row["complexidade_textual"] == "Alta":
        return "Ótima"
    return "Regular"


# ── Qualidade Geral ────────────────────────────────────────────────────────────

def qualidade_geral(row):
    if not row["data_valida"]:
        return "Crítica"
    if row["descricao_vazia"]:
        return "Ruim"
    if row["complexidade_textual"] == "Alta":
        return "Alta"
    return "Média"


# ── Enriquecimento Gold ────────────────────────────────────────────────────────

def enriquecer(df: pd.DataFrame) -> pd.DataFrame:
    print("[Gold] Iniciando enriquecimento...")

    # Remove colunas sem nome
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

    print("[Gold] Colunas detectadas:", df.columns.tolist())

    # Normaliza nomes das colunas
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # Validação de schema
    colunas_esperadas = ["card_id", "descricao", "data_entrega", "assignee", "data_processamento"]
    for col in colunas_esperadas:
        if col not in df.columns:
            raise ValueError(f"[Gold] Coluna obrigatória ausente: {col}")

    # Renomeia card_id → hu_id (padrão Gold)
    df = df.rename(columns={"card_id": "hu_id"})

    # Padronização de campos de texto
    df["hu_id"]    = df["hu_id"].astype("string").str.strip()
    df["descricao"] = df["descricao"].astype("string").str.strip().str.lower()
    df["assignee"]  = df["assignee"].astype("string").str.strip().str.title()

    # Substituição de valores inválidos
    df["descricao"]    = df["descricao"].replace(["sem descrição", "none", "null"], "")
    df["data_entrega"] = df["data_entrega"].replace(["Sem data", "none", "null"], None)

    # Conversão de datas
    df["data_entrega"]       = pd.to_datetime(df["data_entrega"],       errors="coerce", dayfirst=True)
    df["data_processamento"] = pd.to_datetime(df["data_processamento"], errors="coerce", dayfirst=True)

    # Validade de datas
    df["data_valida"] = df["data_entrega"].notna() & df["data_processamento"].notna()

    # Lead time
    df["lead_time_dias"] = (df["data_processamento"] - df["data_entrega"]).dt.days
    df.loc[~df["data_valida"], "lead_time_dias"] = None

    # Features de texto
    df["tamanho_descricao"] = df["descricao"].str.len()
    df["qtd_palavras"]      = df["descricao"].str.split().str.len().fillna(0)

    # Complexidade e flags
    df["complexidade_textual"] = df["qtd_palavras"].apply(classificar_complexidade)
    df["descricao_curta"]      = df["qtd_palavras"] < 15
    df["descricao_longa"]      = df["qtd_palavras"] > 60
    df["descricao_vazia"]      = df["qtd_palavras"] == 0

    # Scores de qualidade
    df["qualidade_descricao"] = df.apply(qualidade_descricao, axis=1)
    df["qualidade_dado"]      = df.apply(qualidade_geral, axis=1)

    df["score_qualidade"] = (
        df["data_valida"].astype(int) * 0.4 +
        (~df["descricao_vazia"]).astype(int) * 0.3 +
        (df["qtd_palavras"] > 20).astype(int) * 0.3
    )

    df["confiabilidade"] = (
        df["data_valida"].astype(int) +
        (~df["descricao_vazia"]).astype(int)
    ) / 2

    # Deduplicação por hu_id (mantém o mais recente)
    df = df.sort_values("data_processamento", ascending=False)
    df = df.drop_duplicates(subset=["hu_id"], keep="first")

    # Organização das colunas
    colunas_ordenadas = [
        "hu_id",
        "assignee",
        "data_entrega",
        "data_processamento",
        "data_valida",
        "lead_time_dias",
        "descricao",
        "qtd_palavras",
        "tamanho_descricao",
        "complexidade_textual",
        "qualidade_descricao",
        "qualidade_dado",
        "score_qualidade",
        "confiabilidade",
        "descricao_curta",
        "descricao_longa",
        "descricao_vazia",
    ]

    df = df[[col for col in colunas_ordenadas if col in df.columns]]

    print(f"[Gold] Enriquecimento concluído. Total de registros: {len(df)}")
    return df


# ── Handler do Lambda ──────────────────────────────────────────────────────────

def lambda_handler(event, context):
    """
    Disparado por um evento S3 PutObject no bucket silver-gp02.
    Espera receber um arquivo no padrão: silver/stories_silver_YYYY-MM-DD.csv
    """

    # 1. Extrai bucket e chave do evento S3
    record     = event["Records"][0]
    src_bucket = record["s3"]["bucket"]["name"]
    src_key    = record["s3"]["object"]["key"]  # ex: silver/stories_silver_2026-04-05.csv

    print(f"[Lambda] Arquivo recebido: s3://{src_bucket}/{src_key}")

    # 2. Valida se o arquivo segue o padrão esperado
    filename = os.path.basename(src_key)  # stories_silver_2026-04-05.csv

    match = re.match(r"stories_silver_(\d{4}-\d{2}-\d{2})\.csv$", filename)
    if not match:
        print(f"[Lambda] Arquivo '{filename}' não segue o padrão esperado. Ignorando.")
        return {"statusCode": 200, "body": "Arquivo ignorado."}

    data_str = match.group(1)  # ex: 2026-04-05

    # 3. Baixa o CSV Silver direto do S3 para memória
    print(f"[Lambda] Baixando '{src_key}' do bucket '{src_bucket}'...")
    response = s3.get_object(Bucket=src_bucket, Key=src_key)
    conteudo = response["Body"].read().decode("utf-8")

    # Tenta separador ; primeiro, depois ,
    df = pd.read_csv(io.StringIO(conteudo), sep=";", dtype=str)
    if len(df.columns) == 1:
        df = pd.read_csv(io.StringIO(conteudo), sep=",", quotechar='"', dtype=str)

    print(f"[Lambda] Silver carregada: {len(df)} linhas.")

    # 4. Aplica enriquecimento Gold
    df_gold = enriquecer(df)

    # 5. Serializa para CSV em memória (separador ; igual ao enrich_JIRA.py original)
    buffer = io.StringIO()
    df_gold.to_csv(buffer, sep=";", index=False, encoding="utf-8-sig")
    csv_bytes = buffer.getvalue().encode("utf-8-sig")

    # 6. Define o nome do arquivo Gold com a mesma data do Silver
    gold_filename = f"stories_gold_{data_str}.csv"
    gold_key      = f"gold/{gold_filename}"

    # 7. Faz upload para o bucket gold-gp02
    print(f"[Lambda] Enviando '{gold_filename}' para s3://{GOLD_BUCKET}/{gold_key}...")
    s3.put_object(
        Bucket=GOLD_BUCKET,
        Key=gold_key,
        Body=csv_bytes,
        ContentType="text/csv"
    )

    print(f"[Lambda] ✅ Pipeline Gold concluída! → s3://{GOLD_BUCKET}/{gold_key}")

    return {
        "statusCode": 200,
        "body": f"Gold gerada com sucesso: {gold_key}"
    }
