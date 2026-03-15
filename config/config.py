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

    @classmethod
    def validate(cls):
        """Valida se as variáveis essenciais estão presentes."""
        missing = []
        if not cls.JIRA_URL: missing.append("JIRA_URL")
        if not cls.JIRA_EMAIL: missing.append("JIRA_EMAIL")
        if not cls.JIRA_API_TOKEN: missing.append("JIRA_API_TOKEN")

        if missing:
            raise ValueError(f"Faltam variáveis de ambiente obrigatórias: {', '.join(missing)}. Verifique o .env.")
