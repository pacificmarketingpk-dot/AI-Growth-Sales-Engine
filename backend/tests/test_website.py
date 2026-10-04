import pytest

from app.services.website import extract_page, fetch_homepage

HTML = """<html><head><title>Acme - Ship faster</title><meta name="description" content="Dev tools">
<meta name="viewport" content="width=device-width"></head><body><h1>Ship faster</h1>
<a href="/demo">Book a demo</a><form><input type="email"></form><img src="a.png"><script>x()</script></body></html>"""


def test_extract_page():
    d = extract_page(HTML, "https://acme.io")
    assert d["title"] == "Acme - Ship faster" and d["h1"] == ["Ship faster"]
    assert "Book a demo" in d["cta_candidates"] and d["form_count"] == 1 and d["email_inputs"] == 1
    assert d["has_viewport_meta"] and d["images_missing_alt"] == 1 and "x()" not in d["text_excerpt"]


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["http://127.0.0.1", "http://localhost:8000", "http://10.0.0.5", "ftp://x.com", ""])
async def test_ssrf_blocked(url):
    assert await fetch_homepage(url) is None
