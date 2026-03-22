import os
import re
import pandas as pd
from util.log import Log

# ── Caminhos ───────────────────────────────────────────────────────────────────

BRONZE_STORIES_PATH = "stories_bronze.csv"
SILVER_STORIES_PATH = "stories_silver.csv"

# ── Normalização de Datas e Texto ──────────────────────────────────────────────

def _parse_date(value) -> str | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    try:
        parsed = pd.to_datetime(value, format="%Y-%m-%d", errors="coerce")
        if pd.isna(parsed):
            parsed = pd.to_datetime(value, dayfirst=True, errors="coerce")
        return parsed.strftime("%d/%m/%Y") if not pd.isna(parsed) else None
    except Exception:
        return None


def _clean_text(value) -> str | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    return str(value).strip()


# ── Reformatação da Descrição ──────────────────────────────────────────────────

def _reformatar_descricao(texto: str) -> str:
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


def _processar_descricao(value) -> str | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    texto = str(value).strip()
    return _reformatar_descricao(texto) if texto else None


# ── Processamento ──────────────────────────────────────────────────────────────

def _process_stories(df: pd.DataFrame) -> pd.DataFrame:
    Log.info("[Silver] Aplicando transformações nas stories...")

    expected = {
        "card_id": None,
        "descricao": None,
        "data_entrega": None,
        "assignee": None,
        "data_processamento": None,
    }
    for col, default in expected.items():
        if col not in df.columns:
            Log.warning(f"[Silver] Coluna '{col}' não encontrada na Bronze — preenchendo com None.")
            df[col] = default

    df["card_id"]            = df["card_id"].apply(_clean_text)
    df["descricao"]          = df["descricao"].apply(_processar_descricao)
    df["data_entrega"]       = df["data_entrega"].apply(_parse_date)
    df["assignee"]           = df["assignee"].apply(lambda v: _clean_text(v) or "Não atribuído")
    df["data_processamento"] = df["data_processamento"].apply(_parse_date)

    df = df.sort_values("data_processamento", ascending=False, na_position="last")
    df = df.drop_duplicates(subset=["card_id"], keep="first")
    df = df.sort_values("card_id").reset_index(drop=True)

    Log.info(f"[Silver] {len(df)} stories únicas após deduplicação.")
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