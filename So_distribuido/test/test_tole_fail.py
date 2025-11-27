# -*- coding: utf-8 -*-
import pytest
from unittest.mock import patch, MagicMock
import httpx
from nodo.main import ejecutar_tarea, _carga, Tarea
from fastapi import Request

# Mock global para evitar efectos secundarios reales
@pytest.fixture
def mock_httpx_post():
    with patch("nodo.main.httpx.post") as mock:
        yield mock

@pytest.fixture
def mock_planificador():
    with patch("nodo.main.planificador") as mock:
        yield mock

@pytest.fixture
def mock_desc():
    with patch("nodo.main.desc") as mock:
        mock.lista_vecinos_con_metricas.return_value = [
            {"nombre": "nodo1", "url": "http://nodo1:8101", "carga": 0.2},
            {"nombre": "nodo2", "url": "http://nodo2:8102", "carga": 0.9}
        ]
        yield mock

def create_mock_request(client_host="192.168.1.100", client_port=9000):
    mock_req = MagicMock(spec=Request)
    mock_req.client.host = client_host
    mock_req.client.port = client_port
    return mock_req

def test_tarea_se_reintenta_tras_fallo_local(mock_httpx_post, mock_planificador, mock_desc):
    """Prueba que una tarea que falla localmente se reenvía a otro nodo."""
    mock_planificador.elegir_ejecutor.return_value = "YO"

    tarea = Tarea(
        id="t1",
        tipo="regresion_lineal",
        payload={"X": [[1]], "y": [1]}
    )
    request = create_mock_request()

    # Simular fallo en ejecución local
    with patch("nodo.main._ejecutar_tarea_local", side_effect=Exception("Simulated crash")):
        response = ejecutar_tarea(tarea, request)

    # Debe intentar reenviar
    assert response["estado"] == "REENVIADO_POR_ERROR"
    assert "a" in response
    mock_httpx_post.assert_called()  # debe llamar a reenvío

def test_tarea_falla_tras_maximos_reintentos(mock_planificador, mock_desc):
    """Prueba que tras MAX_REINTENTOS, la tarea se marca como FALLIDA."""
    mock_planificador.elegir_ejecutor.return_value = "YO"

    tarea = Tarea(
        id="t2",
        tipo="regresion_lineal",
        payload={"X": [[1]], "y": [1], "_reintento": 3}  # > MAX_REINTENTOS=2
    )
    request = create_mock_request()

    with patch("nodo.main._ejecutar_tarea_local", side_effect=Exception("Crash")):
        with patch("nodo.main.httpx.post") as mock_post:
            response = ejecutar_tarea(tarea, request)

    assert response["estado"] == "FALLIDA"
    assert "Máximo de reintentos" in response["error"]
    # Debe intentar notificar al cliente
    mock_post.assert_called()

def test_reenvio_falla_y_se_reintenta_con_otro_nodo(mock_httpx_post, mock_planificador, mock_desc):
    """Si el reenvío falla, debe intentar con otro nodo."""
    mock_planificador.elegir_ejecutor.return_value = "http://nodo1:8101"
    # Asegurar que hay al menos 2 vecinos para que haya "otro nodo"
    mock_desc.lista_vecinos_con_metricas.return_value = [
        {"nombre": "nodo1", "url": "http://nodo1:8101", "carga": 0.2},
        {"nombre": "nodo2", "url": "http://nodo2:8102", "carga": 0.3}
    ]

    tarea = Tarea(
        id="t3",
        tipo="regresion_lineal",
        payload={"X": [[1]], "y": [1]}
    )
    request = create_mock_request()

    # Simular: primer reenvío falla, segundo tiene éxito
    respuesta_exitosa = MagicMock()
    respuesta_exitosa.status_code = 200
    respuesta_exitosa.json.return_value = {"estado": "REENVIADO", "a": "http://nodo2:8102"}

    mock_httpx_post.side_effect = [
        httpx.RequestError("Timeout"),  # Falla en nodo1
        respuesta_exitosa               # Éxito al reenviar a nodo2
    ]

    response = ejecutar_tarea(tarea, request)

    assert response["estado"] == "REENVIADO_POR_FALLO"
    assert response["a"] == "http://nodo2:8102"
    assert mock_httpx_post.call_count == 2

def test_no_hay_nodos_disponibles_para_reintento(mock_planificador):
    """Si no hay nodos alternativos, la tarea falla."""
    mock_planificador.elegir_ejecutor.return_value = "YO"

    tarea = Tarea(
        id="t4",
        tipo="regresion_lineal",
        payload={"X": [[1]], "y": [1]}
    )
    request = create_mock_request()

    # Simular que no hay vecinos (solo este nodo)
    with patch("nodo.main.desc.lista_vecinos_con_metricas", return_value=[]):
        with patch("nodo.main._ejecutar_tarea_local", side_effect=Exception("Crash")):
            response = ejecutar_tarea(tarea, request)

    assert response["estado"] == "FALLIDA"
    assert "No hay nodos alternativos" in response["error"]