# So_distribuido/nodo/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias primero (mejora caché en builds)
COPY ../requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código fuente
COPY .. /app

# Ejecutar el nodo unificado
CMD ["python", "-m", "uvicorn", "nodo.main:app", "--host", "0.0.0.0", "--port", "8100"], "-b"]