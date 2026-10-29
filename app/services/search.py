"""Busca de músicas no YouTube.

Duas implementações com o mesmo método `search()`:
  - YtDlpSearch:   sem chave, usa o próprio yt-dlp (padrão)
  - YouTubeApiSearch: usa a YouTube Data API v3 (precisa de YOUTUBE_API_KEY, ~100 buscas/dia grátis)
"""

import json
import urllib.parse
import urllib.request
from typing import Protocol

from yt_dlp import YoutubeDL

from app.models import SearchResult


class SearchEngine(Protocol):
    def search(self, query: str, limit: int) -> list[SearchResult]: ...


class YtDlpSearch:
    def search(self, query: str, limit: int) -> list[SearchResult]:
        options = {
            "quiet": True,
            "no_warnings": True,
            # só a lista de resultados, sem abrir cada vídeo (bem mais rápido)
            "extract_flat": "in_playlist",
        }
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)

        return [self._to_result(entry) for entry in info.get("entries") or [] if entry]

    @staticmethod
    def _to_result(entry: dict) -> SearchResult:
        thumbnails = entry.get("thumbnails") or []
        duration = entry.get("duration")
        return SearchResult(
            video_id=entry["id"],
            title=entry.get("title") or "?",
            channel=entry.get("channel") or entry.get("uploader") or "",
            duration_sec=int(duration) if duration else None,
            thumbnail=thumbnails[-1]["url"] if thumbnails else None,
        )


class YouTubeApiSearch:
    """Igual ao protótipo Music-01/index.js, agora no servidor (a chave não vai para o celular)."""

    URL = "https://www.googleapis.com/youtube/v3/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, limit: int) -> list[SearchResult]:
        params = urllib.parse.urlencode(
            {
                "part": "snippet",
                "type": "video",
                "maxResults": limit,
                "q": query,
                "key": self.api_key,
            }
        )
        with urllib.request.urlopen(f"{self.URL}?{params}", timeout=15) as response:
            data = json.load(response)

        return [
            SearchResult(
                video_id=item["id"]["videoId"],
                title=item["snippet"]["title"],
                channel=item["snippet"]["channelTitle"],
                thumbnail=item["snippet"]["thumbnails"]["default"]["url"],
            )
            for item in data.get("items", [])
        ]


def make_search_engine(api_key: str) -> SearchEngine:
    """Com chave usa a API oficial; sem chave usa o yt-dlp."""
    return YouTubeApiSearch(api_key) if api_key else YtDlpSearch()
