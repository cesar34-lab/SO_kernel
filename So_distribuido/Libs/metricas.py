# -*- coding: utf-8 -*-
"""
Métricas simples en memoria, estilo Prometheus (texto).
"""
import threading, time
from typing import Dict

class Metricas:
    def __init__(self):
        self._lock = threading.Lock()
        self.contadores: Dict[str, float] = {}
        self.observaciones: Dict[str, list] = {}

    def inc(self, nombre:str, valor:float=1.0):
        with self._lock:
            self.contadores[nombre] = self.contadores.get(nombre, 0.0) + valor

    def observe(self, nombre:str, valor:float):
        with self._lock:
            self.observaciones.setdefault(nombre, []).append(valor)

    def exportar_texto(self)->str:
        with self._lock:
            lineas = []
            for k,v in self.contadores.items():
                lineas.append(f"# TYPE {k} counter")
                lineas.append(f"{k} {v}")
            for k,vals in self.observaciones.items():
                if vals:
                    avg = sum(vals)/len(vals)
                    lineas.append(f"# TYPE {k}_avg gauge")
                    lineas.append(f"{k}_avg {avg}")
            return "\n".join(lineas)
