from pydantic import BaseModel
from typing import List, Optional


class Issue(BaseModel):
    id: str
    descricao: str | None = None
    data_entrega: str | None = None
    assignee: str | None = None