"""Fila de downloads: cada pedido vira um "job" que roda em segundo plano.

O celular pede o download, recebe o id do job e fica perguntando o status
até ficar "done"; aí busca o arquivo. Os jobs ficam só na memória:
se o servidor reiniciar, os downloads em andamento são perdidos (é só pedir de novo).
"""

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from app.models import JobInfo, JobStatus
from app.services.downloader import Downloader

log = logging.getLogger("uvicorn.error")


@dataclass
class DownloadJob:
    video_id: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    file_path: Path | None = None
    file_name: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)

    def to_info(self) -> JobInfo:
        return JobInfo(
            id=self.id,
            video_id=self.video_id,
            status=self.status,
            progress=round(self.progress, 3),
            file_name=self.file_name,
            error=self.error,
        )


class JobManager:
    def __init__(self, downloader: Downloader, max_parallel: int, max_age_hours: float):
        self.downloader = downloader
        self.max_age_seconds = max_age_hours * 3600
        self.jobs: dict[str, DownloadJob] = {}
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=max_parallel)

    def create(self, video_id: str) -> DownloadJob:
        self.cleanup()
        job = DownloadJob(video_id=video_id)
        with self.lock:
            self.jobs[job.id] = job
        self.pool.submit(self._run, job)
        return job

    def get(self, job_id: str) -> DownloadJob | None:
        with self.lock:
            return self.jobs.get(job_id)

    def cleanup(self) -> None:
        """Esquece jobs antigos e apaga seus arquivos (economiza disco da VPS)."""
        limit = time.time() - self.max_age_seconds
        with self.lock:
            old = [job for job in self.jobs.values() if job.created_at < limit]
            for job in old:
                del self.jobs[job.id]
        for job in old:
            if job.file_path:
                job.file_path.unlink(missing_ok=True)

    def _run(self, job: DownloadJob) -> None:
        def on_progress(status: JobStatus, progress: float) -> None:
            job.status = status
            job.progress = progress

        try:
            job.file_path, job.file_name = self.downloader.download(job.id, job.video_id, on_progress)
            job.progress = 1.0
            job.status = JobStatus.DONE
        except Exception as error:  # qualquer falha do yt-dlp vira mensagem para o app
            # aparece no log do contêiner (docker logs), com o motivo completo
            log.error("download %s (video %s) falhou: %s", job.id, job.video_id, error)
            job.error = self._readable(str(error))
            job.status = JobStatus.ERROR

    @staticmethod
    def _readable(message: str) -> str:
        """
        "ERROR: [youtube] abc123: Sign in to confirm..." -> "Sign in to confirm..."
        Tira o prefixo técnico para o motivo caber na tela do celular.
        """
        message = message.removeprefix("ERROR: ")
        if message.startswith("[") and ": " in message:
            message = message.split(": ", 1)[1]
        return message[:300]
