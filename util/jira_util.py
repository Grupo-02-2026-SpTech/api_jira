from models.jira_models import Issue


def parse_issue(data: dict) -> Issue:
    descricao_texto, bold_texts = adf_to_text(data["fields"].get("description"))

    # O assignee pode ser None se o card não tiver responsável atribuído
    assignee_raw = data["fields"].get("assignee")
    assignee = assignee_raw["displayName"] if assignee_raw else None

    issue = Issue(
        id=data["id"],
        descricao=descricao_texto,
        data_entrega=data["fields"].get("duedate"),
        assignee=assignee,
        # Se quiser usar depois com IA, já pode adicionar isso no model:
        # destaques=bold_texts
    )

    return issue


def adf_to_text(adf):
    """
    Converte descrição do Jira (ADF) em texto puro
    e marca trechos em negrito.
    """

    if not adf:
        return "", []

    result = []
    bold_texts = []

    def walk(node):
        node_type = node.get("type")

        if node_type == "text":
            text = node.get("text", "")

            marks = node.get("marks", [])
            is_bold = any(mark.get("type") == "strong" for mark in marks)

            if is_bold:
                result.append(f"[FUNCIONALIDADE]{text}[/FUNCIONALIDADE]")
                bold_texts.append(text)
            else:
                result.append(text)

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

    # Trata corretamente o root do ADF (geralmente "doc")
    if isinstance(adf, dict):
        walk(adf)
    else:
        for node in adf:
            walk(node)

    return "".join(result).strip(), bold_texts