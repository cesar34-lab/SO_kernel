# -*- coding: utf-8 -*-
import pytest
from Libs.kv import KVReplicado

def test_put_y_get_locales():
    """Verifica que put y get funcionen localmente."""
    kv = KVReplicado("http://nodo:8100")
    version = kv.put("clave1", "valor1")
    assert version == 1
    assert kv.get("clave1") == "valor1"
    assert kv.get("clave_inexistente") is None


def test_versiones_monotonicas():
    """Las versiones deben incrementarse correctamente."""
    kv = KVReplicado("http://nodo:8100")
    v1 = kv.put("x", 10)
    v2 = kv.put("x", 20)
    assert v1 == 1
    assert v2 == 2
    assert kv.get("x") == 20


def test_version_explícita_en_put():
    """Si se proporciona una versión, se respeta (si es mayor)."""
    kv = KVReplicado("http://nodo:8100")
    kv.put("y", 100)  # v=1
    v = kv.put("y", 200, version=5)  # fuerza v=5
    assert v == 5
    assert kv.get("y") == 200

    # Versión menor debe ser ignorada
    v2 = kv.put("y", 300, version=3)  # 3 < 5 → se usa 6
    assert v2 == 6
    assert kv.get("y") == 300


def test_estado_completo_serializable():
    """El estado devuelto debe ser JSON-serializable con valor y versión."""
    kv = KVReplicado("http://nodo:8100")
    kv.put("a", [1, 2, 3])
    kv.put("b", {"clave": "valor"})

    estado = kv.estado_completo()
    assert isinstance(estado, dict)
    assert estado["a"]["valor"] == [1, 2, 3]
    assert estado["a"]["version"] == 1
    assert estado["b"]["valor"] == {"clave": "valor"}
    assert estado["b"]["version"] == 1


def test_fusionar_desde_vecino():
    """Debe actualizar solo si la versión remota es mayor."""
    kv = KVReplicado("http://nodo:8100")
    kv.put("dato", "local_v1")  # versión 1

    # Vecino tiene versión más alta
    estado_remoto = {
        "dato": {"valor": "remoto_v3", "version": 3},
        "nuevo_dato": {"valor": "desde_vecino", "version": 1}
    }
    kv.fusionar_desde_vecino(estado_remoto)

    assert kv.get("dato") == "remoto_v3"
    assert kv.get("nuevo_dato") == "desde_vecino"

    # Vecino tiene versión más baja → no debe sobrescribir
    estado_remoto_bajo = {
        "dato": {"valor": "remoto_v2", "version": 2}  # ya estamos en v3
    }
    kv.fusionar_desde_vecino(estado_remoto_bajo)
    assert kv.get("dato") == "remoto_v3"  # se mantiene la v3


def test_fusionar_ignora_versiones_menores():
    """Confirma que no se retrocede en versiones."""
    kv = KVReplicado("http://nodo:8100")
    kv.put("z", "v5", version=5)

    estado_viejo = {"z": {"valor": "v2", "version": 2}}
    kv.fusionar_desde_vecino(estado_viejo)

    assert kv.get("z") == "v5"
    # Versión sigue siendo 5
    estado = kv.estado_completo()
    assert estado["z"]["version"] == 5