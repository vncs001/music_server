"""Servidor de downloads do 8bit player.

Rotas (todas, menos /health, exigem o header "Authorization: Bearer <API_TOKEN>"):
  GET  / ou /health                servidor vivo? (sem token)
  GET  /check                      token certo?
  GET  /search?q=nome&limit=5      busca músicas no YouTube
  POST /downloads {"video_id"}     começa a baixar, devolve o job
  GET  /downloads/{id}             status do job (progresso, erro, nome do arquivo)
  GET  /downloads/{id}/file        o MP3 pronto
"""

import secrets

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings
from app.models import DownloadRequest, JobInfo, JobStatus, SearchResult
from app.services.downloader import Downloader
from app.services.jobs import JobManager
from app.services.search import SearchEngine, make_search_engine


def create_app(
    settings: Settings,
    search_engine: SearchEngine | None = None,
    jobs: JobManager | None = None,
) -> FastAPI:
    """Monta o servidor. Os testes passam search_engine/jobs falsos."""
    search_engine = search_engine or make_search_engine(settings.youtube_api_key)
    jobs = jobs or JobManager(
        Downloader(settings.download_dir, settings.cookies_file),
        max_parallel=settings.max_parallel_downloads,
        max_age_hours=settings.max_file_age_hours,
    )

    app = FastAPI(title="8bit player - servidor de downloads")
    bearer = HTTPBearer(auto_error=False)

    def check_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
        sent = credentials.credentials if credentials else ""
        # compare_digest evita descobrir o token medindo o tempo de resposta
        if not secrets.compare_digest(sent, settings.api_token):
            raise HTTPException(status_code=401, detail="token inválido")

    def find_job(job_id: str):
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="download não encontrado (expirou?)")
        return job

    @app.get("/")
    @app.get("/health")
    def health() -> dict:
        """Sem token: o painel da VPS usa para saber se o servidor subiu."""
        return {"ok": True}

    @app.get("/check", dependencies=[Depends(check_token)])
    def check() -> dict:
        """O app chama no botão TESTAR: endereço certo + token certo."""
        return {"ok": True}

    @app.get("/search", dependencies=[Depends(check_token)])
    def search(q: str = Query(min_length=1, max_length=200), limit: int = Query(5, ge=1, le=15)) -> list[SearchResult]:
        try:
            return search_engine.search(q, limit)
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"falha na busca: {error}") from error

    @app.post("/downloads", dependencies=[Depends(check_token)])
    def start_download(request: DownloadRequest) -> JobInfo:
        return jobs.create(request.video_id).to_info()

    @app.get("/downloads/{job_id}", dependencies=[Depends(check_token)])
    def job_status(job_id: str) -> JobInfo:
        return find_job(job_id).to_info()

    @app.get("/downloads/{job_id}/file", dependencies=[Depends(check_token)])
    def job_file(job_id: str) -> FileResponse:
        job = find_job(job_id)
        if job.status != JobStatus.DONE or not job.file_path or not job.file_path.exists():
            raise HTTPException(status_code=409, detail="arquivo ainda não está pronto")
        return FileResponse(job.file_path, media_type="audio/mpeg", filename=job.file_name)

    return app


def create_app_from_env() -> FastAPI:
    """Usado pelo uvicorn: uvicorn app.main:create_app_from_env --factory"""
    return create_app(Settings.from_env())
