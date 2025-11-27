# -*- coding: utf-8 -*-
import pytest
from unittest.mock import patch
from nodo.main import app, kv, NOMBRE
from Libs.mensajeria import Mensaje  # ✅ Importa desde Libs
from fastapi.testclient import TestClient

client = TestClient(app)

def test_mensaje_para_otro_nodo_es_ignorado():
    """Un mensaje dirigido a otro nodo debe ser rechazado."""
    mensaje = Mensaje(
        id="msg1",
        tipo="gradiente",
        origen="http://nodo1:8101",
        destino="otro_nodo",  # no es este nodo
        payload={"grad": [0.1, -0.2]}
    )
    response = client.post("/mensajes", json=mensaje.dict())
    assert response.status_code == 200
    assert response.json() == {"ok": False, "razon": "destino incorrecto"}

def test_mensaje_ping_devuelve_pong():
    """El tipo 'ping' debe devolver 'pong'."""
    mensaje = Mensaje(
        id="ping1",
        tipo="ping",
        origen="http://cliente:9000",
        destino=NOMBRE,
        payload={}
    )
    response = client.post("/mensajes", json=mensaje.dict())
    assert response.status_code == 200
    assert response.json() == {"ok": True, "respuesta": "pong"}

def test_mensaje_gradiente_se_almacena_en_kv():
    print("NOMBRE del nodo:", NOMBRE)
    mensaje = Mensaje(
        id="grad1",
        tipo="gradiente",
        origen="http://nodo1:8101",
        destino=NOMBRE,
        payload={"grad": [0.1, 0.2, -0.15]}
    )

    # Limpiar estado previo EN LA MISMA INSTANCIA QUE USA LA APP
    kv._data.clear()

    response = client.post("/mensajes", json=mensaje.dict())
    assert response.status_code == 200
    assert response.json()["ok"] is True

    # Verificar que se guardó en KV
    clave = f"gradiente_{mensaje.id}"
    valor = kv.get(clave)
    assert valor == mensaje.payload

    # Limpiar estado previo del KV para la prueba
    with patch.object(kv, '_data', {}):
        response = client.post("/mensajes", json=mensaje.dict())
        assert response.status_code == 200
        assert response.json()["ok"] is True

        # Verificar que se guardó en KV
        clave = f"gradiente_{mensaje.id}"
        valor = kv.get(clave)
        assert valor == mensaje.payload

def test_tipo_no_soportado_devuelve_error():
    """Mensajes con tipo desconocido deben fallar amablemente."""
    mensaje = Mensaje(
        id="x1",
        tipo="tipo_inventado",
        origen="http://nodoX:8100",
        destino=NOMBRE,
        payload={"dato": 42}
    )
    response = client.post("/mensajes", json=mensaje.dict())
    assert response.status_code == 200
    assert response.json() == {"ok": False, "razon": "tipo no soportado"}