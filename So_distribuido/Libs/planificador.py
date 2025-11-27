# -*- coding: utf-8 -*-
"""
Planificador local para nodo en sistema operativo descentralizado.
Toma decisiones autónomas sobre ejecución o reenvío de tareas.
"""

from typing import List, Dict, Any

class PlanificadorLocal:
    def __init__(self, mi_nombre: str, mi_url: str, metricas, obtener_carga_fn):
        self.mi_nombre = mi_nombre
        self.mi_url = mi_url
        self.metricas = metricas
        self.obtener_carga_fn = obtener_carga_fn

    def _puntuar_nodo(self, nodo: Dict[str, Any]) -> float:
        """Calcula puntuación inversamente proporcional a la carga."""
        carga = nodo.get("carga", 0.0)
        return 1.0 / (1.0 + carga)

    def elegir_ejecutor(self, vecinos: List[Dict[str, Any]], tarea=None) -> str:
        """
        Decide quién debe ejecutar la tarea.
        Retorna:
          - "YO" si este nodo debe ejecutarla.
          - URL de un vecino si debe reenviarse.
          - None si no hay nodos disponibles.
        """
        # Construir candidato propio
        carga_propia = self.obtener_carga_fn()
        candidato_propio = {
            "nombre": self.mi_nombre,
            "url": self.mi_url,
            "carga": carga_propia
        }

        # Filtrar vecinos: excluir al nodo local si aparece (evitar duplicados)
        vecinos_filtrados = [
            v for v in vecinos
            if v.get("nombre") != self.mi_nombre
        ]

        # Lista completa de candidatos: yo + vecinos válidos
        candidatos = [candidato_propio] + vecinos_filtrados

        if not candidatos:
            return None

        # Calcular puntuaciones
        puntuados = []
        for c in candidatos:
            score = self._puntuar_nodo(c)
            puntuados.append((score, c))

        # Ordenar de mejor a peor
        puntuados.sort(key=lambda x: x[0], reverse=True)

        # El mejor candidato es el primero
        mejor_score, mejor_nodo = puntuados[0]

        # Si el mejor es este nodo, devolver "YO"
        if mejor_nodo["url"] == self.mi_url:
            return "YO"

        # De lo contrario, devolver la URL del mejor vecino
        return mejor_nodo["url"]