# -*- coding: utf-8 -*-
"""
Almacén clave-valor replicado con consistencia eventual (gossip ligero).
Cada nodo mantiene su propio estado y lo sincroniza con vecinos.
"""
import threading
import time
import httpx
from typing import Dict, Any, Optional, List

class Registro:
    def __init__(self, valor: Any, version: int):
        self.valor = valor
        self.version = version

    def __repr__(self):
        return f"Registro(v={self.version}, val={self.valor})"

class KVReplicado:
    def __init__(self, mi_url: str):
        self.mi_url = mi_url
        self._lock = threading.Lock()
        self._data: Dict[str, Registro] = {}

    def get(self, clave: str) -> Optional[Any]:
        with self._lock:
            reg = self._data.get(clave)
            return reg.valor if reg else None

    def put(self, clave: str, valor: Any, version: Optional[int] = None) -> int:
        with self._lock:
            if clave not in self._data:
                nueva_ver = version if version is not None else 1
                self._data[clave] = Registro(valor, nueva_ver)
            else:
                reg = self._data[clave]
                if version is None:
                    nueva_ver = reg.version + 1
                else:
                    nueva_ver = max(reg.version + 1, version)
                self._data[clave] = Registro(valor, nueva_ver)
            ver_final = self._data[clave].version

        # Propagar asíncronamente a vecinos (modo fire-and-forget)
        # Se debe llamar desde fuera en un hilo o tarea async
        return ver_final

    def estado_completo(self) -> Dict[str, Dict[str, Any]]:
        """Devuelve {clave: {"valor": ..., "version": ...}} para replicación."""
        with self._lock:
            return {
                k: {"valor": v.valor, "version": v.version}
                for k, v in self._data.items()
            }

    def fusionar_desde_vecino(self, estado_remoto: Dict[str, Dict[str, Any]]):
        """Fusiona estado remoto: solo sobrescribe si versión es mayor."""
        with self._lock:
            for clave, datos in estado_remoto.items():
                ver_remota = datos["version"]
                val_remoto = datos["valor"]
                if clave not in self._data or self._data[clave].version < ver_remota:
                    self._data[clave] = Registro(val_remoto, ver_remota)

    def replicar_a_vecino(self, vecino_url: str):
        """Envía estado completo a un vecino (gossip push)."""
        try:
            estado = self.estado_completo()
            httpx.post(
                f"{vecino_url}/kv/sync",
                json=estado,
                timeout=2.0
            )
        except Exception:
            # Silencioso: tolerancia a fallos
            pass

    def replicar_a_vecinos(self, vecinos: List[Dict[str, str]]):
        """Replica estado a todos los vecinos válidos (en hilos separados)."""
        from threading import Thread
        urls = [v["url"] for v in vecinos if v.get("url") and v["url"] != self.mi_url]
        for url in urls:
            Thread(target=self.replicar_a_vecino, args=(url,), daemon=True).start()