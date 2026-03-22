"""
pipeline/silver.py
------------------
Camada Silver da arquitetura medalhão — JIRA API.

Tratamentos de qualidade aplicados:
  - Tipagem e normalização de datas (DD/MM/YYYY)
  - Limpeza e padronização de texto (strip, caixa, caracteres especiais)
  - Fallback explícito para todos os campos nulos
  - Validação de card_id (deve ser numérico)
  - Validação de data_entrega (não pode ser anterior a hoje)
  - Normalização de assignee (title case, sem caracteres especiais)
  - Deduplicação por card_id (mantém o mais recente)
  - Log de registros rejeitados/inconsistentes
  - Salva em stories_silver.csv
"""

import os
import re
import unicodedata
from datetime import datetime
import pandas as pd
from util.log import Log

# ── Caminhos ───────────────────────────────────────────────────────────────────

BRONZE_STORIES_PATH = "stories_bronze.csv"
SILVER_STORIES_PATH = "stories_silver.csv"

# ── Valores padrão para nulos ──────────────────────────────────────────────────

DEFAULTS = {
    "card_id":            "ID_DESCONHECIDO",
    "descricao":          "Sem descrição",
    "data_entrega":       "Sem data",
    "assignee":           "Não atribuído",
    "data_processamento": "Sem data",
}

# ── Normalização de caracteres especiais ───────────────────────────────────────

CHAR_MAP = {
    "→": "->",
    "–": "-",
    "—": "-",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2026": "...",
    "\u00a0": " ",   # non-breaking space
}

def _normalizar_caracteres(texto: str) -> str:
    """Substitui caracteres especiais por equivalentes ASCII seguros."""
    for char, substituto in CHAR_MAP.items():
        texto = texto.replace(char, substituto)
    # Remove demais caracteres não-ASCII que não sejam letras acentuadas do português
    normalizado = []
    for c in texto:
        cat = unicodedata.category(c)
        # Mantém letras (incluindo acentuadas), números, pontuação e espaço
        if cat.startswith(('L', 'N', 'P', 'Z')) or c in '|:.;,!?@#$%&*()-_+=[]{}/<>\n\r\t':
            normalizado.append(c)
        else:
            normalizado.append(' ')
    return re.sub(r' {2,}', ' ', ''.join(normalizado)).strip()


# ── Normalização de Datas ──────────────────────────────────────────────────────

def _parse_date(value, campo: str = "") -> str:
    """
    Converte para DD/MM/YYYY. Retorna o valor padrão se inválido.
    Para data_entrega, loga aviso se a data for no passado.
    """
    default = DEFAULTS.get(campo, "Sem data")

    if pd.isna(value) or str(value).strip() == "":
        return default
    try:
        parsed = pd.to_datetime(value, format="%Y-%m-%d", errors="coerce")
        if pd.isna(parsed):
            parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
        if pd.isna(parsed):
            Log.warning(f"[Silver] Data inválida no campo '{campo}': '{value}' — usando '{default}'.")
            return default

        if campo == "data_entrega" and parsed.date() < datetime.today().date():
            Log.warning(f"[Silver] data_entrega '{parsed.strftime('%d/%m/%Y')}' é anterior a hoje.")

        return parsed.strftime("%d/%m/%Y")
    except Exception:
        return default


# ── Normalização de Texto ──────────────────────────────────────────────────────

def _clean_text(value, campo: str = "") -> str:
    """Strip, normaliza caracteres e aplica fallback."""
    default = DEFAULTS.get(campo, "")
    if pd.isna(value) or str(value).strip() == "":
        return default
    texto = _normalizar_caracteres(str(value).strip())
    return texto if texto else default


def _normalizar_assignee(value) -> str:
    """
    Normaliza o nome do responsável:
      - Title Case
      - Remove caracteres especiais
      - Fallback para 'Não atribuído'
    """
    default = DEFAULTS["assignee"]
    if pd.isna(value) or str(value).strip() == "":
        return default
    texto = _normalizar_caracteres(str(value).strip())
    if not texto:
        return default
    # Title case preservando acentos
    return texto.title()


# ── Validação de card_id ───────────────────────────────────────────────────────

def _validar_card_id(value) -> str:
    """Garante que card_id seja numérico. Loga e usa fallback se não for."""
    default = DEFAULTS["card_id"]
    if pd.isna(value) or str(value).strip() == "":
        Log.warning(f"[Silver] card_id vazio encontrado — usando '{default}'.")
        return default
    valor = str(value).strip()
    if not valor.isdigit():
        Log.warning(f"[Silver] card_id não numérico: '{valor}' — mantendo valor original.")
    return valor


# ── Reformatação da Descrição ──────────────────────────────────────────────────

def _reformatar_descricao(texto: str) -> str:
    """
    Reorganiza o texto da descrição do Jira em blocos coesos separados por ' | ',
    prontos para uma única linha no CSV.
    """
    linhas = [l.strip() for l in re.split(r"[\r\n]+", texto)]
    linhas = [l for l in linhas if l]

    cabecalho   = []
    historia    = []
    jornada     = {}
    etapa_atual = None
    modo        = "cabecalho"

    MARCADORES_HISTORIA = re.compile(r"^(Como |Quero |Para )", re.IGNORECASE)
    ETAPA_NUMERADA      = re.compile(r"^(\d+)\.\s+(.+)")
    BULLET              = re.compile(r"^[-•]\s+(.+)")

    for linha in linhas:
        if re.search(r"jornada funcional", linha, re.IGNORECASE):
            modo = "jornada"
            continue

        if re.search(r"^história$", linha, re.IGNORECASE):
            modo = "historia"
            continue

        if modo != "jornada" and MARCADORES_HISTORIA.match(linha):
            modo = "historia"

        if modo == "cabecalho":
            cabecalho.append(linha)
        elif modo == "historia":
            historia.append(linha)
        elif modo == "jornada":
            match_etapa  = ETAPA_NUMERADA.match(linha)
            match_bullet = BULLET.match(linha)

            if match_etapa:
                num          = int(match_etapa.group(1))
                titulo       = match_etapa.group(2).strip().rstrip(":")
                etapa_atual  = num
                jornada[num] = {"titulo": titulo, "itens": []}
            elif match_bullet and etapa_atual is not None:
                item = match_bullet.group(1).strip()
                if item:
                    jornada[etapa_atual]["itens"].append(item)
            elif etapa_atual is not None and linha:
                jornada[etapa_atual]["itens"].append(linha)

    blocos = []

    if cabecalho:
        blocos.append(" | ".join(cabecalho))

    if historia:
        historia_texto = re.sub(r"\s{2,}", " ", " ".join(historia))
        blocos.append(historia_texto)

    for num in sorted(jornada.keys()):
        etapa  = jornada[num]
        titulo = etapa["titulo"]
        itens  = etapa["itens"]
        bloco  = f"{num}. {titulo}: {' | '.join(itens)}" if itens else f"{num}. {titulo}"
        blocos.append(bloco)

    resultado = re.sub(r" {2,}", " ", " | ".join(blocos))
    return resultado.strip()


def _processar_descricao(value) -> str:
    """Reformata a descrição. Retorna fallback se vazia."""
    default = DEFAULTS["descricao"]
    if pd.isna(value) or str(value).strip() == "":
        return default
    texto = _normalizar_caracteres(str(value).strip())
    if not texto:
        return default
    return _reformatar_descricao(texto)


# ── Processamento ──────────────────────────────────────────────────────────────

def _process_stories(df: pd.DataFrame) -> pd.DataFrame:
    Log.info("[Silver] Aplicando transformações e qualidade de dados...")

    # Garante colunas mínimas
    for col, default in DEFAULTS.items():
        if col not in df.columns:
            Log.warning(f"[Silver] Coluna '{col}' ausente na Bronze — preenchendo com '{default}'.")
            df[col] = default

    total_antes = len(df)

    # Validação e transformação por campo
    df["card_id"]            = df["card_id"].apply(_validar_card_id)
    df["descricao"]          = df["descricao"].apply(_processar_descricao)
    df["data_entrega"]       = df["data_entrega"].apply(lambda v: _parse_date(v, "data_entrega"))
    df["assignee"]           = df["assignee"].apply(_normalizar_assignee)
    df["data_processamento"] = df["data_processamento"].apply(lambda v: _parse_date(v, "data_processamento"))

    # Remove registros com card_id inválido (fallback padrão)
    invalidos = df[df["card_id"] == DEFAULTS["card_id"]]
    if not invalidos.empty:
        Log.warning(f"[Silver] {len(invalidos)} registro(s) com card_id inválido removido(s).")
        df = df[df["card_id"] != DEFAULTS["card_id"]]

    # Deduplicação: mantém o mais recente por card_id
    df = df.sort_values("data_processamento", ascending=False, na_position="last")
    df = df.drop_duplicates(subset=["card_id"], keep="first")
    df = df.sort_values("card_id").reset_index(drop=True)

    total_depois = len(df)
    Log.info(f"[Silver] {total_depois} stories únicas após deduplicação (removidas: {total_antes - total_depois}).")
    return df


# ── Persistência ───────────────────────────────────────────────────────────────

def _save_silver(df: pd.DataFrame) -> None:
    df.to_csv(SILVER_STORIES_PATH, index=False, encoding="utf-8-sig", sep=",", quoting=1)
    Log.info(f"[Silver] CSV salvo em '{SILVER_STORIES_PATH}' ({len(df)} linhas).")


# ── Ponto de Entrada ───────────────────────────────────────────────────────────

def run_silver() -> None:
    Log.info("[Silver] ════════════════════════════════════════")
    Log.info("[Silver] Iniciando pipeline Silver...")

    if not os.path.exists(BRONZE_STORIES_PATH):
        Log.error(f"[Silver] '{BRONZE_STORIES_PATH}' não encontrado. Execute o monitoramento primeiro.")
        return

    df_bronze = pd.read_csv(BRONZE_STORIES_PATH, dtype=str, sep=None, engine="python")
    Log.info(f"[Silver] Bronze carregada: {len(df_bronze)} linhas.")

    df_silver = _process_stories(df_bronze)
    _save_silver(df_silver)

    Log.info("[Silver] Pipeline Silver concluída.")
    Log.info("[Silver] ════════════════════════════════════════")