# Arquitectura (MVP en Español)

- **Descubrimiento (UDP Multicast)**: cada proceso anuncia `{"nombre","url","ts"}` y mantiene una tabla de vecinos con expiración por `timeout`.
- **Coordinador**: registra agentes descubiertos, estima latencia por `/estado`, y planifica tareas con un **scheduler básico**.
- **Agentes**: ejecutan tareas (p.ej. `regresion_lineal`) y reportan resultados al coordinador en `/resultados`.
- **KV**: almacenamiento local por proceso con versión; el coordinador actúa como fuente de verdad para la lista de tareas del MVP.
- **Métricas**: expuestas en `/metrics` en texto.
- **Seguridad (MVP)**: sin autenticación; agregar token compartido en siguientes versiones.

## Estados de tarea
`SUBMITIDO -> EN_EJECUCION -> COMPLETADA/FAILED`

## Mensajes principales
- `POST /tareas` (cliente->coordinador)
- `POST /tareas/ejecutar` (coordinador->agente)
- `POST /resultados` (agente->coordinador)
- `GET /agentes`, `GET /tareas`, `GET /metrics`, `GET /estado`
