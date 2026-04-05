"""
pipeline/enrich_jira.py
-----------------------
Camada de enriquecimento silver da arquitetura medalhão — JIRA API.

Função:
    Recebe a Silver tratada (stories_silver.csv) e gera features analíticas
    sobre qualidade, tempo e texto, produzindo stories_JIRA_Final.csv
    pronto para ser cruzado com as bases de PF na camada Gold.

Features geradas:
    - Renomeação de card_id → hu_id (padrão da Gold)
    - Conversão e validação de datas
    - lead_time_dias: dias entre entrega e processamento
    - Métricas de texto: qtd_palavras, tamanho_descricao, complexidade_textual
    - Flags de descrição: descricao_curta, descricao_longa, descricao_vazia
    - score_qualidade: score numérico 0–1 (data + presença + tamanho)
    - confiabilidade: score 0–1 (data válida + descrição presente)
    - qualidade_descricao: classificação textual por complexidade
    - qualidade_dado: classificação geral por data e complexidade
    - Deduplicação por hu_id (mantém o mais recente)

Saída:
    output/enriched/stories_JIRA_Final.csv
"""

import pandas as pd
import os
import warnings
warnings.filterwarnings("ignore")

# =========================
# PATHS
# =========================

input_path = "stories_silver.csv"
output_path = "stories_JIRA_Final.csv"

# =========================
# COMPLEXIDADE
# =========================
def classificar_complexidade(palavras):
    if palavras == 0:
        return "Vazio"
    elif palavras < 20:
        return "Baixa"
    elif palavras < 50:
        return "Média"
    else:
        return "Alta"


# =========================
# QUALIDADE DESCRIÇÃO
# =========================
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


# =========================
# QUALIDADE GERAL
# =========================
def qualidade_geral(row):
    if not row["data_valida"]:
        return "Crítica"
    if row["descricao_vazia"]:
        return "Ruim"
    if row["complexidade_textual"] == "Alta":
        return "Alta"
    return "Média"


# =========================
# PONTO DE ENTRADA
# =========================
def run_enrich_jira():

    try:
        df = pd.read_csv(input_path, sep=";")
        if len(df.columns) == 1:
            raise Exception("Separador incorreto")
    except:
        df = pd.read_csv(input_path, sep=",", quotechar='"')

    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

    print("Colunas detectadas:", df.columns.tolist())

    # =========================
    # NORMALIZAR COLUNAS
    # =========================
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # =========================
    # VALIDAÇÃO DE SCHEMA
    # =========================
    colunas_esperadas = ["card_id", "descricao", "data_entrega", "assignee", "data_processamento"]

    for col in colunas_esperadas:
        if col not in df.columns:
            raise ValueError(f"Coluna obrigatória ausente: {col}")

    # =========================
    # PADRONIZAÇÃO
    # =========================
    df = df.rename(columns={"card_id": "hu_id"})

    df["hu_id"] = df["hu_id"].astype("string").str.strip()
    df["descricao"] = df["descricao"].astype("string").str.strip().str.lower()
    df["assignee"] = df["assignee"].astype("string").str.strip().str.title()

    # Tratamento de valores ruins
    df["descricao"] = df["descricao"].replace(["sem descrição", "none", "null"], "")
    df["data_entrega"] = df["data_entrega"].replace(["Sem data", "none", "null"], None)

    # =========================
    # DATAS
    # =========================
    df["data_entrega"] = pd.to_datetime(df["data_entrega"], errors="coerce", dayfirst=True)
    df["data_processamento"] = pd.to_datetime(df["data_processamento"], errors="coerce", dayfirst=True)

    # =========================
    # QUALIDADE DE DATA
    # =========================
    df["data_valida"] = (
        df["data_entrega"].notna() &
        df["data_processamento"].notna()
    )

    # =========================
    # FEATURES DE TEMPO
    # =========================
    df["lead_time_dias"] = (
        df["data_processamento"] - df["data_entrega"]
    ).dt.days

    df.loc[~df["data_valida"], "lead_time_dias"] = None

    # =========================
    # FEATURES DE TEXTO
    # =========================
    df["tamanho_descricao"] = df["descricao"].str.len()
    df["qtd_palavras"] = df["descricao"].str.split().str.len().fillna(0)

    # =========================
    # COMPLEXIDADE + FLAGS
    # =========================
    df["complexidade_textual"] = df["qtd_palavras"].apply(classificar_complexidade)
    df["descricao_curta"] = df["qtd_palavras"] < 15
    df["descricao_longa"] = df["qtd_palavras"] > 60
    df["descricao_vazia"] = df["qtd_palavras"] == 0

    # =========================
    # QUALIDADE
    # =========================
    df["qualidade_descricao"] = df.apply(qualidade_descricao, axis=1)
    df["qualidade_dado"] = df.apply(qualidade_geral, axis=1)

    # =========================
    # SCORE NUMÉRICO
    # =========================
    df["score_qualidade"] = (
        df["data_valida"].astype(int) * 0.4 +
        (~df["descricao_vazia"]).astype(int) * 0.3 +
        (df["qtd_palavras"] > 20).astype(int) * 0.3
    )

    # =========================
    # CONFIABILIDADE (0 a 1)
    # =========================
    df["confiabilidade"] = (
        df["data_valida"].astype(int) +
        (~df["descricao_vazia"]).astype(int)
    ) / 2

    # =========================
    # DEDUPLICAÇÃO
    # =========================
    df = df.sort_values("data_processamento", ascending=False)
    df = df.drop_duplicates(subset=["hu_id"], keep="first")

    # =========================
    # ORGANIZAÇÃO FINAL
    # =========================
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
        "descricao_vazia"
    ]

    df = df[[col for col in colunas_ordenadas if col in df.columns]]

    # =========================
    # SALVAR
    # =========================
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    df.to_csv(output_path, sep=";", index=False, encoding="utf-8-sig")

    print("Base JIRA enriquecida com sucesso!")
    print(f"Total de registros finais: {len(df)}")
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    run_enrich_jira()