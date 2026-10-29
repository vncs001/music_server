"""Formatos de dados que entram e saem da API (viram JSON automaticamente)."""

from enum import Enum

from pydantic import BaseModel


class SearchResult(BaseModel):
    video_id: str
    title: str
    channel: str
    duration_sec: int | None = None
    thumbnail: str | None = None


class DownloadRequest(BaseModel):
    video_id: str


class JobStatus(str, Enum):
    QUEUED = "queued"  # na fila, esperando vaga
    DOWNLOADING = "downloading"  # baixando do YouTube
    CONVERTING = "converting"  # ffmpeg convertendo para MP3
    DONE = "done"  # pronto para o celular buscar
    ERROR = "error"


class JobInfo(BaseModel):
    id: str
    video_id: str
    status: JobStatus
    # de 0.0 a 1.0
    progress: float
    # nome do arquivo no formato "Artista - Titulo.mp3" (o app lê artista/título daqui)
    file_name: str | None = None
    error: str | None = None
