# -*- coding: utf-8 -*-
"""
Planificador básico: selecciona agente por puntuación de carga y latencia estimada.
Mantiene colas y reintentos simples.
"""
import time, random
from typing import List, Dict, Any

class SchedulerBasico:
    def __init__(self, reintentos:int=2):
        self.reintentos = reintentos

    def puntuar(self, agentes:List[Dict[str, Any]]):
        # Espera que cada agente tenga: {nombre, url, carga, lat_ms, disponible}
        candidatos = []
        for a in agentes:
            if not a.get("disponible", True): 
                continue
            carga = a.get("carga", 0.0)
            lat = a.get("lat_ms", 10.0)
            score = 1.0/(1.0 + carga + lat/100.0)
            candidatos.append((score, a))
        candidatos.sort(key=lambda x: x[0], reverse=True)
        return [a for _,a in candidatos]

    def elegir(self, agentes:List[Dict[str, Any]]):
        orden = self.puntuar(agentes)
        if not orden:
            return None
        # Pequeña aleatoriedad para repartir
        top = orden[:max(1, min(3, len(orden)))]
        return random.choice(top)
