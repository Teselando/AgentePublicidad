"""Hallazgos públicos: una invitación es un candidato, nunca acceso confirmado."""

from __future__ import annotations

from dataclasses import dataclass
import html
import ipaddress
import os
import re
from urllib.parse import urlparse

INVITE = re.compile(r"https?://chat\.whatsapp\.com/([A-Za-z0-9]{20,32})", re.IGNORECASE)
QUERIES = [
    'site:edu.es "chat.whatsapp.com" "ingeniería" estudiantes',
    'site:es "chat.whatsapp.com" "informática" universidad',
    'site:es "chat.whatsapp.com" "ADE" estudiantes',
    'site:es "chat.whatsapp.com" "matemáticas" universidad',
    'site:es "chat.whatsapp.com" "arquitectura" alumnos',
    'site:es "chat.whatsapp.com" (DAM OR DAW OR ASIR) estudiantes',
    'site:es "chat.whatsapp.com" (bachillerato OR PAU OR "4 ESO") alumnos',
]


@dataclass(frozen=True)
class Finding:
    reference: str
    invitation: str
    source: str


def canonical_invite(text: str) -> list[str]:
    text = html.unescape(text).replace("\\/", "/")
    return list(dict.fromkeys(f"https://chat.whatsapp.com/{code}" for code in INVITE.findall(text)))


def public_page(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname
    if parsed.scheme != "https" or not host or host == "localhost" or host.endswith(".local"):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return True


def search(*, limit: int = 30) -> list[Finding]:
    import requests

    key = os.environ["BRAVE_API_KEY"]
    result: list[Finding] = []
    seen: set[str] = set()
    session = requests.Session()
    session.headers.update({"User-Agent": "AgenteMariii/0.1 (+public-group-research)"})
    for query in QUERIES:
        response = session.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": key},
            params={"q": query, "count": 20, "country": "ES", "search_lang": "es"}, timeout=20,
        )
        response.raise_for_status()
        for hit in response.json().get("web", {}).get("results", []):
            source = hit.get("url", "")
            if not public_page(source):
                continue
            text = source + " " + hit.get("description", "")
            if urlparse(source).hostname != "chat.whatsapp.com":
                try:
                    page = session.get(source, timeout=10, allow_redirects=False)
                    if page.ok and "text/html" in page.headers.get("Content-Type", "") and len(page.content) < 2_000_000:
                        text += " " + page.text
                except requests.RequestException:
                    pass
            for invitation in canonical_invite(text):
                if invitation not in seen:
                    seen.add(invitation)
                    result.append(Finding(hit.get("title", "Referencia sin nombre")[:200], invitation, source))
                    if len(result) >= limit:
                        return result
    return result
