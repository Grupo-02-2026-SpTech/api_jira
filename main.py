import sys
import os
from datetime import datetime

from config.config import Config
from service.jira_client import JiraClient
from service.monitor import JiraMonitor
from service.s3_uploader import S3Uploader
from pipeline.bronze import get_bronze_filename
from util.log import Log

from dotenv import load_dotenv
load_dotenv()


def main():
    # 1. Valida se todas as credenciais foram carregadas corretamente
    try:
        Config.validate()
        Log.info("Credenciais validadas com sucesso!!")
    except ValueError as e:
        print(e)
        return

    # 2. Instancia o cliente do Jira
    if not Config.JIRA_URL or not Config.JIRA_EMAIL or not Config.JIRA_API_TOKEN:
        raise ValueError("Credenciais do Jira não configuradas")

    client = JiraClient(
        url=Config.JIRA_URL,
        email=Config.JIRA_EMAIL,
        token=Config.JIRA_API_TOKEN
    )

    # 3. Instancia o Monitor buscando cards "Concluído" apenas do dia de hoje
    monitor = JiraMonitor(
        client=client,
        status_target="Concluído"
    )

    # 4. Processa todos os cards concluídos hoje e salva no CSV Bronze
    hoje = datetime.now().strftime("%d/%m/%Y")
    Log.info(f"[Main] Buscando cards concluídos em {hoje}...")

    monitor.process_new_cards()

    # 5. Verifica se o arquivo Bronze foi gerado
    bronze_file = get_bronze_filename()

    if not os.path.exists(bronze_file):
        Log.info(f"[Main] Nenhum card concluído hoje ({hoje}). Nenhum arquivo gerado.")
        return

    # 6. Faz upload do arquivo Bronze para o S3 com a data no nome
    s3_key = f"bronze/{bronze_file}"
    Log.info(f"[Main] Iniciando upload de '{bronze_file}' → s3://{Config.AWS_S3_BUCKET}/{s3_key}")

    uploader = S3Uploader()
    sucesso = uploader.upload_file(local_path=bronze_file, s3_key=s3_key)

    if sucesso:
        Log.info("[Main] ✅ Pipeline concluída com sucesso!")
    else:
        Log.error("[Main] ❌ Falha no upload para o S3.")
        sys.exit(1)


if __name__ == "__main__":
    main()