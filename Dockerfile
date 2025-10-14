# Usa la misma versión de Python que en local
FROM python:3.12-slim

WORKDIR /app

# Copia e instala dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de tu app
COPY . .

# Expone el puerto (por defecto Flask usa el 5000)
EXPOSE 5000

# Evita buffering en los logs
ENV PYTHONUNBUFFERED=1

# Arranca con Gunicorn en modo producción: 
# "app" es el módulo y "app" la instancia de Flask dentro de él.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]