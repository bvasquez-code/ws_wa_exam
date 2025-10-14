# Usa la misma versión de Python que en local
FROM python:3.12-slim

WORKDIR /app

# Copia e instala dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tu app
COPY . .

# Railway te da un puerto en $PORT
EXPOSE 5000
ENV PYTHONUNBUFFERED=1

# WSGI target "app:app" = archivo app.py (o package app/__init__.py) exponiendo una variable Flask llamada "app"
# Usa $PORT si existe; si no, 5000
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-5000} app:app"]