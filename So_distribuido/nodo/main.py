# -*- coding: utf-8 -*-
"""
Nodo unificado para sistema operativo descentralizado.
Cada nodo puede recibir, planificar y ejecutar tareas sin depender de un coordinador central.
"""

import os, time, threading, numpy as np, httpx
import random
import uuid
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from Libs.descubrimiento import Descubridor
from Libs.mensajeria import Mensaje
from Libs.metricas import Metricas
from Libs.planificador import PlanificadorLocal
from Libs.kv import KVReplicado

# --- Configuración desde variables de entorno ---
PUERTO = int(os.getenv("PUERTO", "8100"))
GRUPO = os.getenv("DESCUBRIMIENTO_GRUPO", "239.10.10.10")
PGRUPO = int(os.getenv("DESCUBRIMIENTO_PUERTO", "50000"))
NOMBRE = os.getenv("NOMBRE", "nodo")

def get_mi_url():
    return f"http://{NOMBRE}:{PUERTO}"

# --- Instancias globales ---
app = FastAPI(title=f"Nodo {NOMBRE} - SO Descentralizado")
metricas = Metricas()
_carga = 0
_lock = threading.Lock()

def obtener_metricas_locales():
    with _lock:
        carga_actual = _carga
    return {"carga": carga_actual}

kv = KVReplicado(get_mi_url())
planificador = PlanificadorLocal(
    mi_nombre=NOMBRE,
    mi_url=get_mi_url(),
    metricas=metricas,
    obtener_carga_fn=lambda: _carga
)
desc = Descubridor(
    grupo=GRUPO,
    puerto=PGRUPO,
    nombre=NOMBRE,
    servicio_url=get_mi_url(),
    obtener_metricas_fn=obtener_metricas_locales,
    intervalo=1.5
)
def enviar_mensaje(destino_url: str, tipo: str, payload: Dict[str, Any], msg_id: str = None):
    """Envía un mensaje a otro nodo de forma asíncrona."""
    if msg_id is None:
        msg_id = str(uuid.uuid4())
    mensaje = Mensaje(
        id=msg_id,
        tipo=tipo,
        origen=get_mi_url(),
        destino=destino_url.split("/")[-1].split(":")[0],  # extraer nombre del host
        payload=payload
    )
    try:
        httpx.post(f"{destino_url}/mensajes", json=mensaje.dict(), timeout=2.0)
    except Exception as e:
        metricas.inc("mensajes_fallidos")
        # Opcional: guardar en cola para reenvío

# --- Sondeo activo de vecinos (tolerancia a fallos) ---
def monitorear_vecinos():
    while True:
        vecinos = desc.lista_vecinos_con_metricas()
        for v in vecinos:
            if v["url"] == get_mi_url():
                continue
            try:
                r = httpx.get(f"{v['url']}/estado", timeout=1.0)
                if r.status_code != 200:
                    pass  # opcional: lista negra
            except Exception:
                pass  # nodo no responde → se ignorará en planificación
        time.sleep(2.0)

# --- Modelos Pydantic ---
class Tarea(BaseModel):
    id: str
    tipo: str
    payload: Dict[str, Any]

class Resultado(BaseModel):
    tarea_id: str
    estado: str
    detalle: Dict[str, Any] = {}

def calcular_gradiente(modelo, datos):
    # Simulación: devuelve un vector de ceros del mismo tamaño que el modelo
    import numpy as np
    return np.zeros_like(modelo).tolist()
def _ejecutar_federado(payload: Dict[str, Any]):
    # 1. Entrenar localmente
    gradiente = calcular_gradiente(payload["modelo"], payload["datos"])

    # 2. Enviar gradiente a un nodo coordinador (o a todos)
    vecinos = desc.lista_vecinos_con_metricas()
    for v in vecinos:
        if "coordinador" in v["nombre"]:  # convención
            enviar_mensaje(v["url"], "gradiente", {"grad": gradiente})

    return {"estado": "gradiente_enviado"}
# --- Ejecución local de tareas ---
def _ejecutar_regresion(payload: Dict[str, Any]):
    X = np.array(payload["X"], dtype=float)
    y = np.array(payload["y"], dtype=float)
    X_test = np.array(payload.get("X_test", X[:2]), dtype=float)
    Xb = np.c_[np.ones((X.shape[0], 1)), X]
    w = np.linalg.pinv(Xb.T @ Xb) @ Xb.T @ y
    Xb_test = np.c_[np.ones((X_test.shape[0], 1)), X_test]
    y_pred = Xb_test @ w
    return {"coeficientes": w.tolist(), "predicciones": y_pred.tolist()}

def _ejecutar_tarea_local(t: Tarea):
    global _carga
    t0 = time.time()
    with _lock:
        _carga += 1
    try:
        if t.tipo == "regresion_lineal":
            res = _ejecutar_regresion(t.payload)
        else:
            res = {"mensaje": f"Tipo de tarea no reconocido: {t.tipo}"}
        return {"ok": True, "resultado": res}
    finally:
        dur = (time.time() - t0) * 1000.0
        metricas.observe("duracion_ms", dur)
        with _lock:
            _carga -= 1

# --- Constantes ---
MAX_REINTENTOS = 2

# --- Endpoints ---
@app.on_event("startup")
def inicio():
    desc.iniciar()
    threading.Thread(target=monitorear_vecinos, daemon=True).start()

@app.get("/metrics")
def metrics():
    return metricas.exportar_texto()

@app.get("/estado")
def estado():
    with _lock:
        carga = _carga
    return {
        "nombre": NOMBRE,
        "url": get_mi_url(),
        "carga": carga,
    }

@app.post("/kv/sync")
async def sync_kv(estado_remoto: Dict[str, Dict[str, Any]]):
    kv.fusionar_desde_vecino(estado_remoto)
    return {"ok": True}

@app.get("/kv/estado_completo")
async def get_kv_estado():
    return kv.estado_completo()

@app.post("/tareas")
async def submit_tarea(t: Tarea):
    metricas.inc("tareas_recibidas")
    t_dict = {"id": t.id, "tipo": t.tipo, "payload": t.payload, "estado": "SUBMITIDO"}
    lista = kv.get("tareas") or []
    lista.append(t_dict)
    version = kv.put("tareas", lista)
    kv.replicar_a_vecinos(desc.lista_vecinos_con_metricas())
    return {"ok": True, "version": version}

@app.post("/tareas/ejecutar")
def ejecutar_tarea(t: Tarea, request: Request):
    reintento = t.payload.get("_reintento", 0)
    origen = t.payload.get("origen") or f"http://{request.client.host}:{request.client.port}"

    if reintento > MAX_REINTENTOS:
        if origen != get_mi_url():
            try:
                httpx.post(f"{origen}/resultados", json={
                    "tarea_id": t.id,
                    "estado": "FALLIDA",
                    "detalle": {"error": "Máximo de reintentos alcanzado"}
                }, timeout=2.0)
            except:
                pass
        return {"estado": "FALLIDA", "error": "Máximo de reintentos"}

    vecinos = desc.lista_vecinos_con_metricas()
    decision = planificador.elegir_ejecutor(vecinos, t)

    if decision == "YO":
        try:
            resultado = _ejecutar_tarea_local(t)
            if origen != get_mi_url():
                httpx.post(f"{origen}/resultados", json={
                    "tarea_id": t.id,
                    "estado": "COMPLETADA",
                    "detalle": resultado["resultado"]
                }, timeout=2.0)
            return {"estado": "COMPLETADA", "resultado": resultado["resultado"]}
        except Exception as e:
            metricas.inc("tareas_fallidas")
            t.payload["_reintento"] = reintento + 1
            otros_vecinos = [v for v in vecinos if v["url"] != get_mi_url()]
            if otros_vecinos:
                fallback = random.choice(otros_vecinos)["url"]
                httpx.post(f"{fallback}/tareas/ejecutar", json=t.dict(), timeout=2.0)
                return {"estado": "REENVIADO_POR_ERROR", "a": fallback}
            else:
                return {"estado": "FALLIDA", "error": "No hay nodos alternativos"}


    elif decision and decision.startswith("http"):

        try:

            r = httpx.post(f"{decision}/tareas/ejecutar", json=t.dict(), timeout=10.0)

            if r.status_code == 200:

                return r.json()

            else:

                raise Exception("Nodo destino rechazó la tarea")

        except Exception:

            t.payload["_reintento"] = reintento + 1

            otros = [v for v in vecinos if v["url"] != decision]

            if otros:

                nuevo = random.choice(otros)["url"]

                try:

                    httpx.post(f"{nuevo}/tareas/ejecutar", json=t.dict(), timeout=2.0)

                    return {"estado": "REENVIADO_POR_FALLO", "a": nuevo}

                except Exception:

                    # Si el reintento también falla, notificar fracaso

                    if origen != get_mi_url():

                        try:

                            httpx.post(f"{origen}/resultados", json={

                                "tarea_id": t.id,

                                "estado": "FALLIDA",

                                "detalle": {"error": "Todos los nodos fallaron"}

                            }, timeout=2.0)

                        except:

                            pass

                    return {"estado": "FALLIDA", "error": "Reintento también falló"}

            else:

                return {"estado": "FALLIDA", "error": "No hay nodos disponibles"}
@app.post("/mensajes")
async def recibir_mensaje(m: Mensaje):
    if m.destino != NOMBRE:
        return {"ok": False, "razon": "destino incorrecto"}
    if m.tipo == "ping":
        return {"ok": True, "respuesta": "pong"}
    elif m.tipo == "gradiente":
        kv.put(f"gradiente_{m.id}", m.payload)
        return {"ok": True}  # ← debe devolver {"ok": True}
    else:
        return {"ok": False, "razon": "tipo no soportado"}

@app.post("/resultados")
async def recibir_resultado(res: Resultado):
    metricas.inc("resultados_recibidos")
    print(f"[{NOMBRE}] Resultado recibido para tarea {res.tarea_id}: {res.estado}")
    return {"ok": True}