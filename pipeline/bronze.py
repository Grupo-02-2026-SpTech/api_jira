import pandas as pd
import os
from datetime import datetime
from util.log import Log 

def save_bronze(issue):

    Log.info("Iniciando processo de save_bronze")

    agora = datetime.now()

    # =========================
    # HISTÓRIA
    # =========================
    story = {
        "card_id": issue.id,
        "descricao": issue.descricao,
        "data_entrega": issue.data_entrega,
        "data_processamento": agora
    }

    df_story = pd.DataFrame([story])

    story_file = "stories_bronze.csv"

    if not os.path.exists(story_file):
        Log.info("Iniciando processo de criacao do stories.csv")
        df_story.to_csv(story_file, index=False)
        Log.info("Processo de criação do stories.csv CONCLUIDO")
    else:
        Log.info("Iniciando processo de append do stories.csv")
        df_story.to_csv(story_file, mode="a", header=False, index=False)
        Log.info("Processo de append do stories.csv CONCLUIDO")
