"""Testes sem internet: busca e download são falsos (não chamam o YouTube)."""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import JobStatus, SearchResult
from app.services.downloader import Downloader
from app.services.jobs import JobManager

TOKEN = "segredo"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


class FakeSearch:
    def search(self, query: str, limit: int) -> list[SearchResult]:
        return [SearchResult(video_id=f"v{i}", title=f"{query} {i}", channel="Canal") for i in range(limit)]


class FakeDownloader:
    def __init__(self, folder: Path, fail: bool = False):
        self.folder = folder
        self.fail = fail

    def download(self, job_id, video_id, on_progress):
        on_progress(JobStatus.DOWNLOADING, 0.5)
        if self.fail:
            raise RuntimeError("Video unavailable")
        path = self.folder / f"{job_id}.mp3"
        path.write_bytes(b"ID3fake")
        return path, "Banda - Musica.mp3"


def make_client(tmp_path: Path, fail: bool = False) -> TestClient:
    settings = Settings(TOKEN, tmp_path, 24, 1, "", None)
    jobs = JobManager(FakeDownloader(tmp_path, fail), max_parallel=1, max_age_hours=24)
    return TestClient(create_app(settings, search_engine=FakeSearch(), jobs=jobs))


def wait_job(client: TestClient, job_id: str) -> dict:
    for _ in range(50):
        job = client.get(f"/downloads/{job_id}", headers=AUTH).json()
        if job["status"] in ("done", "error"):
            return job
        time.sleep(0.02)
    raise AssertionError("job não terminou")


def test_health_sem_token(tmp_path):
    assert make_client(tmp_path).get("/health").json() == {"ok": True}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer errado"}])
def test_rotas_exigem_token(tmp_path, headers):
    assert make_client(tmp_path).get("/search?q=x", headers=headers).status_code == 401


def test_check_valida_token(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/check", headers=AUTH).json() == {"ok": True}
    assert client.get("/check").status_code == 401


def test_busca(tmp_path):
    results = make_client(tmp_path).get("/search?q=rock&limit=3", headers=AUTH).json()
    assert [r["video_id"] for r in results] == ["v0", "v1", "v2"]


def test_download_completo(tmp_path):
    client = make_client(tmp_path)
    job = client.post("/downloads", json={"video_id": "abc"}, headers=AUTH).json()
    job = wait_job(client, job["id"])
    assert job["status"] == "done" and job["progress"] == 1.0
    assert job["file_name"] == "Banda - Musica.mp3"

    file = client.get(f"/downloads/{job['id']}/file", headers=AUTH)
    assert file.status_code == 200 and file.content == b"ID3fake"
    assert file.headers["content-type"] == "audio/mpeg"


def test_download_com_erro(tmp_path):
    client = make_client(tmp_path, fail=True)
    job = client.post("/downloads", json={"video_id": "abc"}, headers=AUTH).json()
    job = wait_job(client, job["id"])
    assert job["status"] == "error" and "unavailable" in job["error"]
    assert client.get(f"/downloads/{job['id']}/file", headers=AUTH).status_code == 409


def test_job_inexistente(tmp_path):
    assert make_client(tmp_path).get("/downloads/nada", headers=AUTH).status_code == 404


def test_limpeza_apaga_arquivos_antigos(tmp_path):
    jobs = JobManager(FakeDownloader(tmp_path), max_parallel=1, max_age_hours=24)
    job = jobs.create("abc")
    jobs.pool.shutdown(wait=True)
    assert job.file_path.exists()
    job.created_at -= 25 * 3600
    jobs.cleanup()
    assert not job.file_path.exists() and jobs.get(job.id) is None


@pytest.mark.parametrize(
    "info, expected",
    [
        ({"title": "Queen - Bohemian Rhapsody", "channel": "Queen Official"}, "Queen - Bohemian Rhapsody.mp3"),
        ({"title": "Bohemian Rhapsody", "channel": "Queen - Topic"}, "Queen - Bohemian Rhapsody.mp3"),
        ({"track": "Song", "artist": "Band", "title": "x"}, "Band - Song.mp3"),
        ({"title": 'A/B: "C"?', "channel": ""}, "AB C.mp3"),
        ({"title": "Queen – Bohemian Rhapsody", "channel": "Queen Official"}, "Queen - Bohemian Rhapsody.mp3"),
    ],
)
def test_nome_do_arquivo(info, expected):
    assert Downloader.nice_file_name(info) == expected
