"""Baixa o áudio de um vídeo e converte para MP3 (yt-dlp + ffmpeg)."""

import re
from pathlib import Path
from typing import Callable

from yt_dlp import YoutubeDL

from app.models import JobStatus

# Recebe (status, progresso de 0.0 a 1.0)
ProgressCallback = Callable[[JobStatus, float], None]


class Downloader:
    def __init__(self, download_dir: Path, cookies_file: Path | None = None):
        self.download_dir = download_dir
        self.cookies_file = cookies_file
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def download(self, job_id: str, video_id: str, on_progress: ProgressCallback) -> tuple[Path, str]:
        """Baixa e devolve (caminho do MP3 no servidor, nome bonito do arquivo)."""

        def progress_hook(data: dict) -> None:
            if data["status"] == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                done = data.get("downloaded_bytes", 0)
                # o download vai até 90%; os últimos 10% são a conversão
                on_progress(JobStatus.DOWNLOADING, 0.9 * done / total if total else 0.0)
            elif data["status"] == "finished":
                on_progress(JobStatus.CONVERTING, 0.9)

        options = {
            "format": "bestaudio/best",
            "outtmpl": str(self.download_dir / f"{job_id}.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "progress_hooks": [progress_hook],
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
                {"key": "FFmpegMetadata"},
            ],
        }
        if self.cookies_file:
            options["cookiefile"] = str(self.cookies_file)

        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)

        return self.download_dir / f"{job_id}.mp3", self.nice_file_name(info)

    @staticmethod
    def nice_file_name(info: dict) -> str:
        """
        Gera "Artista - Titulo.mp3", o formato que o app usa para mostrar artista e título.
        Muitos vídeos já se chamam "Artista - Música"; nesse caso o título é usado como está.
        """
        title = info.get("track") or info.get("title") or info.get("id") or "musica"
        title = re.sub(r"\s[–—]\s", " - ", title)  # "Queen – Song" (travessão) -> "Queen - Song"
        artist = info.get("artist") or info.get("channel") or info.get("uploader") or ""
        artist = artist.removesuffix(" - Topic")  # canais automáticos do YouTube Music

        name = title if " - " in title or not artist else f"{artist} - {title}"
        # tira caracteres que não podem ir em nome de arquivo
        name = re.sub(r'[\\/:*?"<>|]+', "", name).strip() or "musica"
        return f"{name[:120]}.mp3"
