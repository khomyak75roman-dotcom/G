"""SearxNG metasearch adapter (searxng/searxng).

Optional and keyless: set ``SEARXNG_URL`` to your own instance (e.g.
http://localhost:8080) and opt in with ``--sources searxng``. No network call
is made during discovery. Results carry their own licence metadata when the
instance provides it; unknown licences are marked as such for review.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .base import Candidate, SearchFilters, stable_url_id


class SearxngSource:
    name = "searxng"
    display_name = "SearxNG metasearch"
    provider = "searxng"
    priority = 25
    supports = {"video": True, "image": True}
    install_instructions = (
        "Run a SearxNG instance (docker compose or self-hosted) with the JSON "
        "API enabled, then set SEARXNG_URL=http://localhost:8080 in .env."
    )

    def is_available(self) -> bool:
        return bool(os.environ.get("SEARXNG_URL", "").strip())

    def _endpoint(self) -> str:
        return os.environ.get("SEARXNG_URL", "").strip().rstrip("/") + "/search"

    def search(self, query: str, filters: SearchFilters) -> list[Candidate]:
        import requests

        category = "videos" if filters.kind == "video" else "images" if filters.kind == "image" else "general"
        response = requests.get(
            self._endpoint(),
            params={
                "q": query,
                "format": "json",
                "categories": category,
                "language": "all",
            },
            headers={"Accept": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json() or {}
        results = payload.get("results") or []
        candidates: list[Candidate] = []
        for result in results:
            page_url = str(result.get("url") or "")
            direct_url = str(result.get("img_src") or page_url)
            if not direct_url:
                continue
            license_label = str(result.get("license") or "unknown")
            candidates.append(Candidate(
                source=self.name,
                source_id=stable_url_id(direct_url),
                source_url=page_url or direct_url,
                download_url=direct_url,
                kind="video" if filters.kind == "video" else "image",
                creator=str(result.get("author") or result.get("publisher") or ""),
                license=license_label,
                source_tags=str(result.get("title") or result.get("content") or "")[:500],
                thumbnail_url=str(result.get("thumbnail") or ""),
                extra={
                    "engine": result.get("engine", ""),
                    "license_unknown": license_label == "unknown",
                },
            ))
        return candidates

    def download(self, candidate: Candidate, out_path: Path) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if candidate.kind == "video" and candidate.source_url:
            from generator.downloads import download_url

            result = download_url(candidate.source_url, out_path.parent)
            if result.get("path"):
                source = Path(result["path"])
                if source.resolve() != out_path.resolve():
                    source.replace(out_path)
                return out_path
        import requests

        response = requests.get(candidate.download_url, stream=True, timeout=60)
        response.raise_for_status()
        with out_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    handle.write(chunk)
        return out_path
