FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Las dependencias se copian antes que el código fuente para aprovechar la
# caché de capas de Docker: los paquetes sólo se reinstalan cuando cambian
# los archivos de requisitos, no en cada cambio de código.
COPY requirements/base.txt requirements/base.txt
COPY requirements/dev.txt requirements/dev.txt
RUN pip install --no-cache-dir -r requirements/dev.txt

# El entrypoint se instala antes del código para que la capa también se
# cachée independientemente de cambios en el código de la aplicación.
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY . .

ENTRYPOINT ["/entrypoint.sh"]
