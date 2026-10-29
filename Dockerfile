FROM python:3.12-slim

# ffmpeg converte o áudio para MP3
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# roda sem ser root
RUN useradd --create-home music && mkdir -p /data/downloads && chown music /data/downloads
USER music

ENV DOWNLOAD_DIR=/data/downloads
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app_from_env", "--factory", "--host", "0.0.0.0", "--port", "8000"]
