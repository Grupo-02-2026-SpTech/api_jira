import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class Config:
    """
    Classe centralizada para gerenciar configurações e variáveis de ambiente.
    """
    JIRA_URL = os.getenv("JIRA_URL")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
    
    # Trocar por uma consulta a um banco de dados
    JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")
    
    # Intervalo de tempo do loop (em segundos)
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 30))

    # Configurações AWS S3
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")  # Obrigatório em contas AWS Academy
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")

    @classmethod
    def validate(cls):
        """Valida se as variáveis essenciais estão presentes."""
        missing = []
        if not cls.JIRA_URL: missing.append("JIRA_URL")
        if not cls.JIRA_EMAIL: missing.append("JIRA_EMAIL")
        if not cls.JIRA_API_TOKEN: missing.append("JIRA_API_TOKEN")
        if not cls.AWS_ACCESS_KEY_ID: missing.append("AWS_ACCESS_KEY_ID")
        if not cls.AWS_SECRET_ACCESS_KEY: missing.append("AWS_SECRET_ACCESS_KEY")
        if not cls.AWS_S3_BUCKET: missing.append("AWS_S3_BUCKET")

        if missing:
            raise ValueError(f"Faltam variáveis de ambiente obrigatórias: {', '.join(missing)}. Verifique o .env.")
