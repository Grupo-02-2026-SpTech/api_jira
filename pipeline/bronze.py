import pandas as pd
import os
from datetime import datetime
from util.log import Log


def get_bronze_filename() -> str:
    """Retorna o nome do arquivo bronze com a data de hoje."""
    hoje = datetime.now().strftime("%Y-%m-%d")
    return f"stories_bronze_{hoje}.csv"


def save_bronze(issue):
    """Salva os dados do card no CSV da camada Bronze (com data no nome)."""

    Log.info("Iniciando processo de save_bronze")

    agora = datetime.now()

    # =========================
    # HISTÓRIA
    # =========================
    story = {
        "card_id": issue.id,
        "descricao": issue.descricao,
        "data_entrega": issue.data_entrega,
        "assignee": issue.assignee,
        "data_processamento": agora
    }

    df_story = pd.DataFrame([story])

    story_file = get_bronze_filename()

    if not os.path.exists(story_file):
        Log.info(f"Criando arquivo '{story_file}'...")
        df_story.to_csv(story_file, index=False)
        Log.info(f"Arquivo '{story_file}' criado com sucesso.")
    else:
        Log.info(f"Adicionando card ao arquivo '{story_file}'...")
        df_story.to_csv(story_file, mode="a", header=False, index=False)
        Log.info(f"Card adicionado ao '{story_file}' com sucesso.")