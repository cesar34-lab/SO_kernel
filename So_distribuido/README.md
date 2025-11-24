# Sistema Operativo Distribuido (MVP) — Español

Este repositorio contiene un **MVP ejecutable** (en Docker) para un sistema estilo *runtime* distribuido
con **descubrimiento de nodos**, **agentes de ejecución**, **planificador (coordinador)**,
**almacenamiento clave-valor replicado simple**, **métricas** y **un ejemplo ML** usando Numpy.
Todo el **código y comentarios están en español**.

## Componentes
- **coordinador/**: servicio FastAPI que actúa como planificador y orquestador de tareas.
- **agentes/**: servicio FastAPI por nodo que ejecuta tareas.
- **Libs/**: librerías compartidas (descubrimiento, kv, scheduler, métricas).
- **tools/**: utilidades y *bootstrap* local.
- **examples/**: ejemplo de regresión lineal distribuida.
- **docs/**: arquitectura y protocolos.
- **test/**: pruebas unitarias y de integración.
- **.github/workflows/**: CI con pytest y linters.

## Ejecución rápida (Docker Compose)
```bash
docker compose up --build
# Coordinador en http://localhost:8000
# Agentes en http://localhost:8101 y http://localhost:8102
```

## Flujo de ejemplo
1. Levanta el clúster con `docker compose up`.
2. Envía un **job de ejemplo**:
```bash
python examples/ejemplo_ml_regresion.py --coordinador http://localhost:8000
```
3. Revisa métricas en cada servicio (`/metrics`) y el estado en `/agentes` y `/tareas` del coordinador.

## Árbol
```
coordinador/
agentes/
Libs/
tools/
examples/
docs/
test/
.github/workflows/
docker-compose.yml
requirements.txt
```

## Licencia
MIT
