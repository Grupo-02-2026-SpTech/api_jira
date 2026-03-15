from config.config import Config
from service.jira_client import JiraClient
from service.monitor import JiraMonitor
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


    # 3. Instancia o Monitor e define que procurará pelo status "xre"
    monitor = JiraMonitor(
        client=client,
        status_target="Concluído"
    )

    # 4. Trava a thread executando o monitoramento sem parar (Loop Infinito)
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        Log.error("\n\nMonitoramento interrompido pelo usuário (CTRL+C). Encerrando a aplicação.")
    except Exception as e:
        Log.error(f"\n[ERRO CRÍTICO] A aplicação parou inesperadamente: {e}")

if __name__ == "__main__":
    main()
