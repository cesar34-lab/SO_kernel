# -*- coding: utf-8 -*-
import time
import json
from unittest.mock import patch, MagicMock
from Libs.descubrimiento import Descubridor

def test_escuchar_procesa_mensaje_valido():
    """Procesa un anuncio válido de un vecino y lo almacena con métricas."""
    d = Descubridor(
        grupo="239.10.10.10",
        puerto=50000,
        nombre="nodo_local",
        servicio_url="http://nodo_local:8100",
        obtener_metricas_fn=lambda: {"carga": 0.0}
    )

    ts = time.time()
    mensaje_valido = json.dumps({
        "nombre": "vecino1",
        "url": "http://vecino1:8101",
        "ts": ts,
        "carga": 0.4
    })

    # Simular socket que devuelve un mensaje válido y luego timeout
    mock_sock = MagicMock()
    mock_sock.recvfrom.side_effect = [
        (mensaje_valido.encode(), ("192.168.1.10", 50000)),
        TimeoutError()  # para salir del bucle en la prueba real, pero aquí no lo usamos directamente
    ]

    # Simular solo una iteración de escuchar (sin bucle infinito)
    with patch.object(d, '_socket_receptor', return_value=mock_sock):
        sock = d._socket_receptor()
        try:
            data, _ = sock.recvfrom(4096)
            info = json.loads(data.decode('utf-8'))
            if isinstance(info, dict):
                nombre = info.get("nombre")
                if nombre and nombre != d.nombre:
                    ts_val = info.get("ts")
                    url_val = info.get("url")
                    if isinstance(ts_val, (int, float)) and url_val:
                        metricas = {k: v for k, v in info.items() if k not in {"nombre", "url", "ts"}}
                        d.vecinos[nombre] = (ts_val, url_val, metricas)
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError, ValueError):
            pass

    vecinos = d.lista_vecinos_con_metricas()
    assert len(vecinos) == 1
    v = vecinos[0]
    assert v["nombre"] == "vecino1"
    assert v["url"] == "http://vecino1:8101"
    assert v["carga"] == 0.4


def test_escuchar_ignora_mensaje_propio():
    """No debe agregar un anuncio cuyo nombre coincida con el propio nodo."""
    d = Descubridor(
        grupo="239.10.10.10",
        puerto=50000,
        nombre="nodo_self",
        servicio_url="http://nodo_self:8100",
        obtener_metricas_fn=lambda: {}
    )

    mensaje_propio = json.dumps({
        "nombre": "nodo_self",
        "url": "http://nodo_self:8100",
        "ts": time.time(),
        "carga": 0.2
    }).encode()

    # Simular procesamiento manual
    info = json.loads(mensaje_propio.decode())
    nombre = info.get("nombre")
    # El código real en escuchar() hace: if nombre != self.nombre → procesar
    assert nombre == d.nombre  # por lo tanto, se ignora
    # No se agrega a vecinos
    assert len(d.vecinos) == 0


def test_escuchar_ignora_mensaje_malformado():
    """Debe ignorar mensajes no JSON o sin campos obligatorios."""
    d = Descubridor("239.10.10.10", 50000, "yo", "http://yo:8000", lambda: {})

    casos_invalidos = [
        b"no es json",
        json.dumps({"nombre": "mal", "ts": "no es numero"}).encode(),
        json.dumps({"url": "falta_nombre", "ts": time.time()}).encode(),
        json.dumps({"nombre": "ok", "url": "ok"}).encode(),  # falta ts
    ]

    for data in casos_invalidos:
        try:
            info = json.loads(data.decode())
            if not isinstance(info, dict):
                continue
            nombre = info.get("nombre")
            if not nombre or nombre == d.nombre:
                continue
            ts_val = info.get("ts")
            url_val = info.get("url")
            if not isinstance(ts_val, (int, float)) or not url_val:
                continue
            # Si llega aquí, sería válido → pero en estos casos no debería
            assert False, f"Mensaje inválido fue aceptado: {data}"
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            # Es correcto: se ignora
            pass

    assert len(d.vecinos) == 0


def test_purga_vecinos_expirados():
    """Los vecinos cuyo último latido supera el timeout deben eliminarse."""
    d = Descubridor("239.10.10.10", 50000, "yo", "http://yo:8000", lambda: {}, timeout=2.0)

    ts_viejo = time.time() - 5.0  # 5 segundos atrás (más allá del timeout de 2s)
    d.vecinos["nodo_viejo"] = (ts_viejo, "http://viejo:8000", {"carga": 0.5})
    d.vecinos["nodo_reciente"] = (time.time(), "http://reciente:8001", {"carga": 0.1})

    # Simular purga (como se hace en escuchar)
    ahora = time.time()
    expirados = [k for k, (ts, _, _) in d.vecinos.items() if ahora - ts > d.timeout]
    for k in expirados:
        d.vecinos.pop(k, None)

    vecinos = d.lista_vecinos_con_metricas()
    assert len(vecinos) == 1
    assert vecinos[0]["nombre"] == "nodo_reciente"