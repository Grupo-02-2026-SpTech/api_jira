from pydantic import BaseModel
from typing import List, Optional


class Issue(BaseModel):
    id: str
    descricao: Optional[str] = None
    data_entrega: Optional[str] = None
