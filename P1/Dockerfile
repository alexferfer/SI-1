FROM python:3.12

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Abre los puertos de escucha del contenedor
EXPOSE 5050
EXPOSE 5051