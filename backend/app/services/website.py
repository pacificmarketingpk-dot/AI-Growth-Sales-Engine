"""Optional website retrieval. Returns None unless the page was really fetched."""
import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

MAX_BYTES = 1_500_000


def _normalise(url: str) -> str | None:
    url = (url or "").strip()
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return None
    return url


async def _is_public(host: str) -> bool:
    """Block SSRF: refuse hosts resolving to private, loopback or link-local addresses."""
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


async def fetch_homepage(url: str) -> dict | None:
    url = _normalise(url)
    if not url or not await _is_public(urlparse(url).hostname):
        return None
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, max_redirects=3,
                                     headers={"User-Agent": "AIGrowthSalesEngine/1.0 (website review)"}) as c:
            r = await c.get(url)
        if r.status_code >= 400 or "html" not in r.headers.get("content-type", ""):
            return None
        if not await _is_public(urlparse(str(r.url)).hostname):
            return None
        return extract_page(r.text[:MAX_BYTES], str(r.url))
    except (httpx.HTTPError, ValueError):
        return None


def extract_page(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    meta = lambda name: (soup.find("meta", attrs={"name": name}) or {}).get("content", "")  # noqa: E731
    buttons = [b.get_text(" ", strip=True) for b in soup.find_all(["button", "a"]) if b.get_text(strip=True)]
    cta_words = ("demo", "contact", "start", "trial", "book", "get", "quote", "call", "sign up", "buy", "free")
    return {
        "url": url,
        "title": soup.title.get_text(strip=True) if soup.title else "",
        "meta_description": meta("description"),
        "has_viewport_meta": bool(soup.find("meta", attrs={"name": "viewport"})),
        "h1": [h.get_text(" ", strip=True) for h in soup.find_all("h1")][:5],
        "h2": [h.get_text(" ", strip=True) for h in soup.find_all("h2")][:12],
        "cta_candidates": [b for b in buttons if any(w in b.lower() for w in cta_words)][:15],
        "form_count": len(soup.find_all("form")),
        "email_inputs": len(soup.find_all("input", attrs={"type": "email"})),
        "image_count": len(soup.find_all("img")),
        "images_missing_alt": len([i for i in soup.find_all("img") if not i.get("alt")]),
        "text_excerpt": " ".join(soup.get_text(" ", strip=True).split())[:5000],
    }
