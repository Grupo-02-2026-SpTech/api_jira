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

    # =========================
    # SUBTASKS
    # =========================
    linhas_subtasks = []

    for sub in issue.subtasks:
        linhas_subtasks.append({
            "card_id": issue.id,
            "subtask_id": sub.id,
            "subtask_key": sub.key,
            "subtask_descricao": sub.descricao,
            "data_processamento": agora
        })

    if linhas_subtasks:
        df_sub = pd.DataFrame(linhas_subtasks)

        subtask_file = "subtasks_bronze.csv"

        if not os.path.exists(subtask_file):
            Log.info("Iniciando processo de criacao do subtask.csv")
            df_sub.to_csv(subtask_file, index=False)
            Log.info("Processo de criação do subtask.csv CONCLUIDO")
        else:
            Log.info("Iniciando processo de append do subtask.csv")
            df_sub.to_csv(subtask_file, mode="a", header=False, index=False)
            Log.info("Processo de append do subtask.csv CONCLUIDO")