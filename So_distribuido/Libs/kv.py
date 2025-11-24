# -*- coding: utf-8 -*-
"""
Almacén clave-valor replicado simple con versión y *gossip* opcional (pull).
Para el MVP: se replica vía llamadas HTTP al coordinador, que propaga a agentes.
"""
import threading
from typing import Dict, Any, Optional

class Registro:
    def __init__(self, valor: Any, version:int):
        self.valor = valor
        self.version = version

class KVLocal:
    def __init__(self):
        self._lock = threading.Lock()
        self._data: Dict[str, Registro] = {}

    def get(self, clave:str) -> Optional[Any]:
        with self._lock:
            reg = self._data.get(clave)
            return None if reg is None else reg.valor

    def put(self, clave:str, valor:Any, version:int=None) -> int:
        with self._lock:
            if clave not in self._data:
                ver = 1 if version is None else version
                self._data[clave] = Registro(valor, ver)
                return ver
            else:
                reg = self._data[clave]
                nueva_ver = (reg.version + 1) if version is None else max(reg.version+1, version)
                self._data[clave] = Registro(valor, nueva_ver)
                return nueva_ver

    def estado(self):
        with self._lock:
            return {k: {"version": v.version, "valor": v.valor} for k,v in self._data.items()}
