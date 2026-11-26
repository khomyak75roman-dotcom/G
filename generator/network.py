"""Opt-in network diagnostics for the keyless generator.

This module does not install or activate VPN clients, DPI bypasses, proxy
pools or traffic relays. It only reports the standard proxy environment that
``requests``/``yt-dlp``/``gallery-dl`` already honour, and checks that the
keyless stock sources are reachable through the caller's existing network.

Proxy values are redacted: credentials are never returned or printed.
"""
from __future__ import annotations

import os
import urllib.parse
from typing import Any

USER_AGENT = "OpenMontage/1.0 (network-check; keyless generator)"
SOURCE_ENDPOINTS = {
    "wikimedia": "https://commons.wikimedia.org/w/api.php?action=query&format=json&meta=siteinfo",
    "nasa": "https://images-api.nasa.gov/search?q=test&media_type=image&page_size=1",
    "archive_org": "https://archive.org/advancedsearch.php?q=test&rows=1&page=1&output=json",
}
PROXY_VARS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)


def _redact(value: str) -> str:
    """Return ``scheme://host:port`` without any user info or path."""
    try:
        parsed = urllib.parse.urlparse(value)
    except ValueError:
        return "<configured>"
    if parsed.scheme and parsed.hostname:
        port = f":{parsed.port}" if parsed.port else ""
        return f"{parsed.scheme}://{parsed.hostname}{port}"
    return "<configured>"


def proxy_report() -> dict[str, Any]:
    """Describe proxy configuration without exposing credentials."""
    configured: dict[str, str] = {}
    for name in PROXY_VARS:
        value = os.environ.get(name, "").strip()
        if value:
            configured[name] = "<all hosts>" if name.lower() == "no_proxy" else _redact(value)
    outbound = {k: v for k, v in configured.items() if not k.lower().endswith("no_proxy")}
    return {
        "proxy_env_configured": bool(outbound),
        "no_proxy_configured": bool(set(configured) - set(outbound)),
        "endpoints": configured,
        "note": (
            "Standard proxy environment is respected by requests, yt-dlp and gallery-dl. "
            "No VPN/DPI bypass or proxy-pool tooling is installed or activated."
        ),
    }


def check_sources(timeout: float = 8.0) -> dict[str, Any]:
    """Probe the default keyless sources via the caller's current network."""
    import requests

    results: dict[str, Any] = {}
    for name, url in SOURCE_ENDPOINTS.items():
        try:
            response = requests.get(
                url, timeout=timeout, stream=True,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
            results[name] = {"reachable": response.status_code < 400, "status": response.status_code}
            response.close()
        except Exception as exc:
            results[name] = {"reachable": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "sources": results,
        "reachable": [name for name, result in results.items() if result["reachable"]],
        "proxy": proxy_report(),
    }
