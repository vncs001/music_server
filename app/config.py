"""Configurações do servidor, lidas das variáveis de ambiente (arquivo .env)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    # Senha que o app manda em todo pedido (Authorization: Bearer <token>)
    api_token: str
    # Pasta onde os MP3 ficam até o celular buscar
    download_dir: Path
    # Arquivos mais velhos que isso são apagados (o celular já guardou a cópia dele)
    max_file_age_hours: float
    # Quantos downloads ao mesmo tempo
    max_parallel_downloads: int
    # Opcional: chave da YouTube Data API. Vazio = busca pelo próprio yt-dlp (sem chave)
    youtube_api_key: str
    # Opcional: cookies.txt de uma conta do YouTube (ajuda quando a VPS é bloqueada)
    cookies_file: Path | None

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        token = os.getenv("API_TOKEN", "").strip()
        if not token:
            raise RuntimeError("Defina API_TOKEN no .env (veja .env.example)")

        cookies = os.getenv("COOKIES_FILE", "").strip()
        return cls(
            api_token=token,
            download_dir=Path(os.getenv("DOWNLOAD_DIR", "downloads")),
            max_file_age_hours=float(os.getenv("MAX_FILE_AGE_HOURS", "24")),
            max_parallel_downloads=int(os.getenv("MAX_PARALLEL_DOWNLOADS", "2")),
            youtube_api_key=os.getenv("YOUTUBE_API_KEY", "").strip(),
            cookies_file=Path(cookies) if cookies else None,
        )
