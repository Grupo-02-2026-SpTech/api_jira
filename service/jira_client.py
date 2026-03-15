import requests
from requests.auth import HTTPBasicAuth
from util.jira_util import parse_issue
from util.log import Log

class JiraClient:
    """
    Classe responsável pela comunicação direta com a API do Jira.
    """
    def __init__(self, url: str, email: str, token: str):
        self.url = url.rstrip("/")
        self.auth = HTTPBasicAuth(email, token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def search_issues(self, jql_query: str, max_results: int = 50) -> dict:
        """
        Busca cards no Jira usando JQL (Jira Query Language).
        """
        Log.info("Iniciaindo pesquisa de cards já concluidos")
        search_endpoint = f"{self.url}/rest/api/3/search/jql"
        params = {
            "jql": jql_query,
            "maxResults": max_results
        }
        
        Log.info("URL de request montada: " + search_endpoint)
        response = requests.get(
            search_endpoint,
            headers=self.headers,
            params=params,
            auth=self.auth
        )
        print(response.json())
        response.raise_for_status()
        return response.json()

    def get_issue_details(self, issue_key: str):

        issue_endpoint = f"{self.url}/rest/api/3/issue/{issue_key}"

        response = requests.get(
            issue_endpoint,
            headers=self.headers,
            auth=self.auth
        )

        response.raise_for_status()
        data = response.json()

        issue = parse_issue(data)

        return issue


