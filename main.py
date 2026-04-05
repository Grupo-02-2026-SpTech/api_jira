from config.config import Config
from service.jira_client import JiraClient
from service.monitor import JiraMonitor
from pipeline.silver import run_silver
from pipeline.enrich_JIRA import run_enrich_jira
from util.log import Log

import os
import time
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

    # 3. Instancia o Monitor e define que procurará pelo status "Concluído"
    monitor = JiraMonitor(
        client=client,
        status_target="Concluído"
    )

    # 4. Loop de monitoramento com pipeline Bronze → Silver → Enriched após cada ciclo
    Log.info("[Main] Iniciando monitoramento com arquitetura Bronze → Silver → Enriched")

    while True:
        try:
            # ── Bronze: coleta novos cards do Jira ───────────────────────────
            monitor.process_new_cards()

            # ── Silver: só roda se o bronze existir ──────────────────────────
            # Quando não há cards novos, o bronze não é gerado e o Silver
            # não deve ser chamado — evita quebrar o loop desnecessariamente
            if not os.path.exists("stories_bronze.csv"):
                Log.info("[Main] Nenhum card novo encontrado. Aguardando próximo ciclo...")
            else:
                # ── Silver: limpeza, normalização e deduplicação ─────────────
                run_silver()

                # ── Enriched: só roda se o silver existir ────────────────────
                # Garante que o Silver gerou o arquivo antes de enriquecer
                if not os.path.exists("stories_silver.csv"):
                    Log.info("[Main] Silver não gerou arquivo. Pulando Enriched.")
                else:
                    # ── Enriched: features analíticas e qualidade de texto ───
                    run_enrich_jira()

        except KeyboardInterrupt:
            Log.error("\n\nMonitoramento interrompido pelo usuário (CTRL+C). Encerrando a aplicação.")
            break
        except Exception as e:
            Log.error(f"\n[ERRO CRÍTICO] A aplicação parou inesperadamente: {e}")
            break

        time.sleep(Config.POLL_INTERVAL)


if __name__ == "__main__":
    main()