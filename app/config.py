"""Configurações do servidor, lidas das variáveis de ambiente (arquivo .env)."""

import base64
import os
import tempfile
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
            raise RuntimeError("API_TOKEN não chegou ao servidor: defina a variável no painel ou no .env (veja .env.example)")

        return cls(
            api_token=token,
            download_dir=Path(os.getenv("DOWNLOAD_DIR", "downloads")),
            max_file_age_hours=float(os.getenv("MAX_FILE_AGE_HOURS", "24")),
            max_parallel_downloads=int(os.getenv("MAX_PARALLEL_DOWNLOADS", "2")),
            youtube_api_key=os.getenv("YOUTUBE_API_KEY", "").strip(),
            cookies_file=cls._cookies_file(),
        )

    @staticmethod
    def _cookies_file() -> Path | None:
        """
        Cookies do YouTube (evitam o bloqueio "Sign in to confirm you're not a bot").
        Duas formas:
          - YOUTUBE_COOKIES_B64: conteúdo do cookies.txt em base64 (para painéis que só têm variáveis)
          - COOKIES_FILE: caminho de um cookies.txt montado no contêiner
        """
        encoded = os.getenv("YOUTUBE_COOKIES_B64", "").strip()
        if encoded:
            # o yt-dlp reescreve o arquivo ao renovar os cookies: precisa ser uma pasta gravável
            path = Path(tempfile.gettempdir()) / "youtube_cookies.txt"
            path.write_bytes(base64.b64decode(encoded))
            return path

        cookies = os.getenv("COOKIES_FILE", "").strip()
        return Path(cookies) if cookies else None
