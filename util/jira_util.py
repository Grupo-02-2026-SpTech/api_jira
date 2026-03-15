from models.jira_models import Subtask, Issue

def parse_issue(data: dict) -> Issue:
    """
    Converte os dados em objetos JSON
    """
    subtasks = []

    for sub in data["fields"].get("subtasks", []):
        subtasks.append(
            Subtask(
                id=sub["id"],
                key=sub["key"],
                descricao=sub["fields"]["summary"]
            )
        )

    descricao_texto = adf_to_text(data["fields"].get("description"))

    issue = Issue(
        id=data["id"],
        descricao=descricao_texto,
        data_entrega=data["fields"].get("duedate"),
        subtasks=subtasks
    )

    return issue


def adf_to_text(adf):
    """
    Converte descrição do Jira (ADF) em texto puro.
    """

    if not adf:
        return ""

    result = []

    def walk(node):
        node_type = node.get("type")

        if node_type == "text":
            result.append(node.get("text", ""))

        elif node_type == "hardBreak":
            result.append("\n")

        elif node_type == "paragraph":
            for child in node.get("content", []):
                walk(child)
            result.append("\n\n")

        elif node_type == "heading":
            for child in node.get("content", []):
                walk(child)
            result.append("\n\n")

        elif node_type == "listItem":
            result.append("- ")
            for child in node.get("content", []):
                walk(child)
            result.append("\n")

        elif node_type in ["orderedList", "bulletList"]:
            for child in node.get("content", []):
                walk(child)
            result.append("\n")

        else:
            for child in node.get("content", []):
                walk(child)

    walk(adf)
    
    return "".join(result).strip()
