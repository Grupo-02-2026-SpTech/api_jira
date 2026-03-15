from pydantic import BaseModel
from typing import List, Optional


class Subtask(BaseModel):
    id: str
    key: str
    descricao: str


class Issue(BaseModel):
    id: str
    descricao: Optional[str] = None
    data_entrega: Optional[str] = None
    subtasks: List[Subtask] = []
