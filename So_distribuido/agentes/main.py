# -*- coding: utf-8 -*-
from fastapi import FastAPI
from pydantic import BaseModel
import os, time, threading, numpy as np, httpx
from typing import Dict, Any
from Libs.descubrimiento import Descubridor
from Libs.metricas import Metricas

PUERTO = int(os.getenv("PUERTO", "8101"))
GRUPO = os.getenv("DESCUBRIMIENTO_GRUPO", "239.10.10.10")
PGRUPO = int(os.getenv("DESCUBRIMIENTO_PUERTO", "50000"))
NOMBRE = os.getenv("NOMBRE", "agente")
COORD = os.getenv("COORDINADOR", "http://localhost:8000")

app = FastAPI(title=f"Agente {NOMBRE} (ES)")
metricas = Metricas()
desc = Descubridor(GRUPO, PGRUPO, NOMBRE, f"http://localhost:{PUERTO}", intervalo=1.5)
_carga = 0
_lock = threading.Lock()

class Tarea(BaseModel):
    id: str
    tipo: str
    payload: Dict[str, Any]

@app.on_event("startup")
def inicio():
    desc.iniciar()

@app.get("/metrics")
def metrics():
    return metricas.exportar_texto()

@app.get("/estado")
def estado():
    with _lock:
        carga = _carga
    return {"nombre": NOMBRE, "carga": carga}

def _ejecutar_regresion(payload:Dict[str, Any]):
    # Entrena regresión lineal y predice sobre X_test (todo en numpy)
    X = np.array(payload["X"], dtype=float)
    y = np.array(payload["y"], dtype=float)
    X_test = np.array(payload.get("X_test", X[:2]), dtype=float)
    # Añadir columna de 1s para el sesgo
    Xb = np.c_[np.ones((X.shape[0], 1)), X]
    # w = (X^T X)^(-1) X^T y
    w = np.linalg.pinv(Xb.T @ Xb) @ Xb.T @ y
    Xb_test = np.c_[np.ones((X_test.shape[0],1)), X_test]
    y_pred = Xb_test @ w
    return {"coeficientes": w.tolist(), "predicciones": y_pred.tolist()}

@app.post("/tareas/ejecutar")
def ejecutar(t:Tarea):
    global _carga
    t0 = time.time()
    with _lock:
        _carga += 1
    try:
        if t.tipo == "regresion_lineal":
            res = _ejecutar_regresion(t.payload)
        else:
            res = {"mensaje": f"Tipo de tarea no reconocido: {t.tipo}"}
        # enviar resultado al coordinador
        httpx.post(COORD + "/resultados", json={
            "tarea_id": t.id, "estado": "COMPLETADA", "detalle": res
        }, timeout=10.0)
        return {"ok": True, "resultado": res}
    finally:
        dur = (time.time()-t0)*1000.0
        metricas.observe("duracion_ms", dur)
        with _lock:
            _carga -= 1
