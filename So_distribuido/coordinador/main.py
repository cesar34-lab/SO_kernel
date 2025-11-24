# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, time, httpx, threading
from typing import List, Dict, Any
from Libs.descubrimiento import Descubridor
from Libs.kv import KVLocal
from Libs.scheduler import SchedulerBasico
from Libs.metricas import Metricas

PUERTO = int(os.getenv("PUERTO", "8000"))
GRUPO = os.getenv("DESCUBRIMIENTO_GRUPO", "239.10.10.10")
PGRUPO = int(os.getenv("DESCUBRIMIENTO_PUERTO", "50000"))
NOMBRE = os.getenv("NOMBRE", "coordinador")

app = FastAPI(title="Coordinador SO Distribuido (ES)")
kv = KVLocal()
metricas = Metricas()
agentes: Dict[str, Dict[str, Any]] = {}
scheduler = SchedulerBasico()

class Tarea(BaseModel):
    id: str
    tipo: str
    payload: Dict[str, Any]

class Resultado(BaseModel):
    tarea_id: str
    estado: str
    detalle: Dict[str, Any] = {}

desc = Descubridor(GRUPO, PGRUPO, NOMBRE, f"http://localhost:{PUERTO}", intervalo=1.5)

def latidos():
    while True:
        # medir latencia simple por /estado
        eliminar = []
        for nombre, a in list(agentes.items()):
            try:
                t0 = time.time()
                r = httpx.get(a["url"] + "/estado", timeout=1.0)
                a["disponible"] = r.status_code == 200
                a["lat_ms"] = (time.time()-t0)*1000.0
                a["carga"] = r.json().get("carga", 0.0)
            except Exception:
                a["disponible"] = False
                a["lat_ms"] = 9999
                eliminar.append(nombre)
        for n in eliminar:
            agentes.pop(n, None)
        time.sleep(2.0)

@app.on_event("startup")
def inicio():
    desc.iniciar()
    # hilo para traer vecinos como agentes
    def sync_vecinos():
        while True:
            for v in desc.lista_vecinos():
                if v["nombre"].startswith("agente"):
                    agentes[v["nombre"]] = {"nombre": v["nombre"], "url": v["url"], "disponible": True, "carga": 0.0, "lat_ms": 10.0}
            time.sleep(2.0)
    threading.Thread(target=sync_vecinos, daemon=True).start()
    threading.Thread(target=latidos, daemon=True).start()

@app.get("/metrics")
def metrics():
    return metricas.exportar_texto()

@app.get("/agentes")
def listar_agentes():
    return list(agentes.values())

@app.get("/tareas")
def listar_tareas():
    # MVP: kv["tareas"] = lista
    return kv.get("tareas") or []

@app.post("/tareas")
def submit_tarea(t:Tarea):
    metricas.inc("tareas_recibidas")
    lista = kv.get("tareas") or []
    lista.append({"id": t.id, "tipo": t.tipo, "payload": t.payload, "estado":"SUBMITIDO"})
    kv.put("tareas", lista)
    # elegir agente
    agente = scheduler.elegir(list(agentes.values()))
    if not agente:
        raise HTTPException(503, "No hay agentes disponibles")
    # delegar
    try:
        r = httpx.post(agente["url"] + "/tareas/ejecutar", json=t.dict(), timeout=10.0)
        if r.status_code != 200:
            raise HTTPException(500, f"Agente falló: {r.text}")
        # marcar en progreso
        lista[-1]["estado"] = "EN_EJECUCION"
        kv.put("tareas", lista)
        metricas.inc("tareas_enviadas")
        return {"asignado_a": agente["nombre"], "respuesta_agente": r.json()}
    except Exception as e:
        raise HTTPException(500, f"Error al delegar: {e}")

@app.post("/resultados")
def recibir_resultado(res:Resultado):
    metricas.inc("resultados_recibidos")
    lista = kv.get("tareas") or []
    for it in lista:
        if it["id"] == res.tarea_id:
            it["estado"] = res.estado
            it["resultado"] = res.detalle
    kv.put("tareas", lista)
    return {"ok": True}

@app.get("/estado")
def estado():
    return {
        "nombre": NOMBRE,
        "carga": len(kv.get("tareas") or []),
        "vecinos": len(desc.lista_vecinos())
    }
