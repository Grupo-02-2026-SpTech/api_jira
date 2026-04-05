from service.jira_client import JiraClient
from config.config import Config
from util.log import Log
from pipeline.bronze import save_bronze

class JiraMonitor:
    """
    Classe responsável por orquestrar a lógica de monitoramento contínuo.
    """
    def __init__(self, client: JiraClient, status_target: str):
        self.client = client
        self.status_target = status_target
        self.processed_issues = set() # Armazena chaves de cards já printados para não floodar o terminal

    def build_jql(self) -> str:
        """Constrói a query do Jira (JQL) filtrando cards concluídos hoje."""
        jql = f'status = "{self.status_target}" AND statusCategoryChangedDate >= startOfDay()'
        if Config.JIRA_PROJECT_KEY:
            jql = f'project = "{Config.JIRA_PROJECT_KEY}" AND ' + jql
        return jql

    def process_new_cards(self):
        """Verifica se existem cards com o status alvo e não processados."""
        jql = self.build_jql()
        try:
            
            data = self.client.search_issues(jql_query=jql)
            issues = data.get('issues', [])
            
            for issue in issues:
                issue_key = issue['id']
                
                # Só processa se o card ainda não foi printado
                if issue_key not in self.processed_issues:
                    self._handle_matched_issue(issue_key)
                    self.processed_issues.add(issue_key)
                    
        except Exception as e:
            Log.error(f"Falha ao buscar cards: {e}")

    def _handle_matched_issue(self, issue_key: str):
        """Pega o JSON completo do card e printa na tela."""
        Log.info(f"\n{'='*50}")
        Log.info(f"NOVO CARD NO STATUS '{self.status_target.upper()}': {issue_key}")
        Log.info(f"{'='*50}")
        try:
            full_json = self.client.get_issue_details(issue_key)
            save_bronze(full_json)
           
           
        except Exception as e:
            Log.error(f"Não foi possível pegar detalhes do card {issue_key}: {e}")

    def start_monitoring(self):
        """
        Inicia o loop infinito ("100% do tempo").
        """
        Log.info(f"[*] Iniciando monitoramento do Jira...")
        Log.info(f"[*] Status alvo: '{self.status_target}'")
        Log.info(f"[*] Intervalo: {Config.POLL_INTERVAL} segundos")
        Log.info("[*] Pressione CTRL+C para parar.\n")
        
        while True:
            self.process_new_cards()
            # Descansa o terminal até o próximo ciclo
            time.sleep(Config.POLL_INTERVAL)
