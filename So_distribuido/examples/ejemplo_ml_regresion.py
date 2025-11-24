# -*- coding: utf-8 -*-
"""
Ejemplo de envío de una tarea de regresión lineal al coordinador.
"""
import argparse, requests, uuid, numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coordinador", default="http://localhost:8000")
    args = ap.parse_args()

    # Generar dataset simple
    rng = np.random.default_rng(0)
    X = rng.normal(size=(200, 3))
    w = np.array([1.5, -2.0, 0.7])
    y = 2.0 + X @ w + rng.normal(scale=0.1, size=200)
    X_test = [[0.1, 0.2, 0.3],[1.0, -1.0, 0.5]]

    tarea = {
        "id": str(uuid.uuid4()),
        "tipo": "regresion_lineal",
        "payload": {"X": X.tolist(), "y": y.tolist(), "X_test": X_test}
    }
    r = requests.post(args.coordinador + "/tareas", json=tarea, timeout=10)
    r.raise_for_status()
    print("Tarea enviada:", r.json())

if __name__ == "__main__":
    main()
