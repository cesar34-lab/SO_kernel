import time
from typing import Dict, Any

from pydantic import BaseModel


class Mensaje(BaseModel):
    id: str
    tipo: str  # ej: "gradiente", "resultado_parcial", "ping"
    origen: str
    destino: str
    payload: Dict[str, Any]
    ts: float = time.time()