"""
(C) Copyright 2026 Boni Garcia (https://bonigarcia.github.io/)
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
 http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from pathlib import Path

import requests

from incluscan.scraper import crawl_site, extract_html_document, extract_pdf_document


def test_extract_html_document_returns_title_and_visible_text():
    html = Path("tests/fixtures/html/uc3m-sample.html").read_text(encoding="utf-8")
    doc = extract_html_document(html, "https://www.uc3m.es/")

    assert doc.title == "UC3M Sample"
    assert "Language without bias" in doc.text
    assert "var x = 1" not in doc.text


def test_extract_html_document_includes_meta_description_when_body_is_sparse():
    html = """
    <html>
      <head>
        <title>UC3M</title>
        <meta name="description" content="University text in the homepage">
      </head>
      <body></body>
    </html>
    """

    doc = extract_html_document(html, "https://www.uc3m.es/")

    assert doc.title == "UC3M"
    assert "University text in the homepage" in doc.text


def test_extract_pdf_document_uses_embedded_text(monkeypatch, tmp_path: Path):
    class FakePage:
        def extract_text(self):
            return "Texto del PDF"

    class FakeReader:
        pages = [FakePage()]

    monkeypatch.setattr("incluscan.scraper.PdfReader", lambda *_args, **_kwargs: FakeReader())

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%fake")

    doc = extract_pdf_document(pdf_path, "https://www.uc3m.es/sample.pdf")

    assert doc.content_type == "application/pdf"
    assert "Texto del PDF" in doc.text


def test_crawl_site_prefers_sitemap_urls():
    class FakeResponse:
        def __init__(self, url: str):
            self.status_code = 200
            self.headers = {"content-type": "text/html; charset=utf-8"}
            self.url = url
            if url.endswith("sitemap.xml"):
                self.text = "<urlset><url><loc>https://www.uc3m.es/page-2</loc></url></urlset>"
                self.content = self.text.encode("utf-8")
            elif url.endswith("page-2"):
                self.text = '<html><head><title>From sitemap</title></head><body><p>Second</p></body></html>'
                self.content = self.text.encode("utf-8")
            elif url.endswith("robots.txt"):
                self.text = "User-agent: *\nAllow: /"
                self.content = self.text.encode("utf-8")
            else:
                self.text = '<html><head><title>UC3M Sample</title></head><body><p>First</p></body></html>'
                self.content = self.text.encode("utf-8")

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=10, headers=None):
        return FakeResponse(url)

    snapshot, pages = crawl_site("https://www.uc3m.es/", page_cap=2, fetch=fake_get)

    assert snapshot.base_url == "https://www.uc3m.es/"
    assert len(pages) == 2
    assert pages[0].url == "https://www.uc3m.es/"
    assert pages[1].url == "https://www.uc3m.es/page-2"


def test_crawl_site_keeps_seed_url_even_when_sitemap_exists():
    class FakeResponse:
        def __init__(self, url: str):
            self.status_code = 200
            self.headers = {"content-type": "text/html; charset=utf-8"}
            self.url = url
            if url.endswith("sitemap.xml"):
                self.text = "<urlset><url><loc>https://www.uc3m.es/page-2</loc></url></urlset>"
                self.content = self.text.encode("utf-8")
            elif url.endswith("page-2"):
                self.text = '<html><head><title>From sitemap</title></head><body><p>Second</p></body></html>'
                self.content = self.text.encode("utf-8")
            elif url.endswith("robots.txt"):
                self.text = "User-agent: *\nAllow: /"
                self.content = self.text.encode("utf-8")
            else:
                self.text = '<html><head><title>Seed page</title></head><body><p>Seed</p></body></html>'
                self.content = self.text.encode("utf-8")

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=10, headers=None):
        return FakeResponse(url)

    snapshot, pages = crawl_site("https://www.uc3m.es/grado/admision/solicitud/estudiantes-internacionales/estudiantes-europeos", page_cap=2, fetch=fake_get)

    assert snapshot.base_url == "https://www.uc3m.es/grado/admision/solicitud/estudiantes-internacionales/estudiantes-europeos"
    assert any(page.url.endswith("estudiantes-europeos") for page in pages)
    assert any(page.url == "https://www.uc3m.es/page-2" for page in pages)


def test_crawl_site_deduplicates_equivalent_root_urls():
    class FakeResponse:
        def __init__(self, url: str):
            self.status_code = 200
            self.headers = {"content-type": "text/html; charset=utf-8"}
            self.url = url
            if url.endswith("sitemap.xml"):
                self.text = "<urlset><url><loc>http://www.uc3m.es</loc></url><url><loc>http://www.uc3m.es/</loc></url><url><loc>https://www.uc3m.es/page-2</loc></url></urlset>"
                self.content = self.text.encode("utf-8")
            elif url.endswith("page-2"):
                self.text = '<html><head><title>From sitemap</title></head><body><p>Second</p></body></html>'
                self.content = self.text.encode("utf-8")
            elif url.endswith("robots.txt"):
                self.text = "User-agent: *\nAllow: /"
                self.content = self.text.encode("utf-8")
            else:
                self.text = '<html><head><title>Seed page</title></head><body><p>Seed</p></body></html>'
                self.content = self.text.encode("utf-8")

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=10, headers=None):
        return FakeResponse(url)

    snapshot, pages = crawl_site("https://www.uc3m.es/", page_cap=4, fetch=fake_get)

    assert snapshot.base_url == "https://www.uc3m.es/"
    assert len(pages) == 2
    assert pages[0].url == "https://www.uc3m.es/"
    assert pages[1].url == "https://www.uc3m.es/page-2"


def test_crawl_site_skips_timed_out_seed_page_and_continues():
    class FakeResponse:
        def __init__(self, url: str):
            self.status_code = 200
            self.headers = {"content-type": "text/html; charset=utf-8"}
            self.url = url
            if url.endswith("sitemap.xml"):
                self.text = "<urlset><url><loc>https://www.uc3m.es/page-2</loc></url></urlset>"
                self.content = self.text.encode("utf-8")
            elif url.endswith("page-2"):
                self.text = '<html><head><title>From sitemap</title></head><body><p>Second</p></body></html>'
                self.content = self.text.encode("utf-8")
            elif url.endswith("robots.txt"):
                self.text = "User-agent: *\nAllow: /"
                self.content = self.text.encode("utf-8")
            else:
                self.text = '<html><head><title>Seed page</title></head><body><p>Seed</p></body></html>'
                self.content = self.text.encode("utf-8")

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=10, headers=None):
        if url == "https://www.uc3m.es/":
            raise requests.ReadTimeout("timed out")
        return FakeResponse(url)

    snapshot, pages = crawl_site("https://www.uc3m.es/", page_cap=2, fetch=fake_get)

    assert snapshot.base_url == "https://www.uc3m.es/"
    assert len(pages) == 1
    assert pages[0].url == "https://www.uc3m.es/page-2"


def test_crawl_site_deduplicates_case_variant_same_page():
    class FakeResponse:
        def __init__(self, url: str):
            self.status_code = 200
            self.headers = {"content-type": "text/html; charset=utf-8"}
            self.url = url
            if url.endswith("sitemap.xml"):
                self.text = "<urlset><url><loc>http://www.uc3m.es/Inicio</loc></url><url><loc>http://www.uc3m.es/inicio</loc></url><url><loc>https://www.uc3m.es/page-2</loc></url></urlset>"
                self.content = self.text.encode("utf-8")
            elif url.endswith("page-2"):
                self.text = '<html><head><title>From sitemap</title></head><body><p>Second</p></body></html>'
                self.content = self.text.encode("utf-8")
            elif url.endswith("robots.txt"):
                self.text = "User-agent: *\nAllow: /"
                self.content = self.text.encode("utf-8")
            elif url == "https://www.uc3m.es/":
                self.text = '<html><head><title>Home</title></head><body><p>Seed</p></body></html>'
                self.content = self.text.encode("utf-8")
            else:
                self.text = '<html><head><title>Inicio</title></head><body><p>Campus</p></body></html>'
                self.content = self.text.encode("utf-8")

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=10, headers=None):
        return FakeResponse(url)

    snapshot, pages = crawl_site("https://www.uc3m.es/", page_cap=4, fetch=fake_get)

    assert snapshot.base_url == "https://www.uc3m.es/"
    assert len(pages) == 3
    assert pages[0].url == "https://www.uc3m.es/"
    assert sum(page.url.lower().endswith("/inicio") for page in pages) == 1
    assert any(page.url == "https://www.uc3m.es/page-2" for page in pages)


def test_crawl_site_uses_final_redirected_url():
    class FakeResponse:
        def __init__(self, url: str):
            self.status_code = 200
            self.headers = {"content-type": "text/html; charset=utf-8"}
            if url == "http://www.uc3m.es/Vida_Universitaria":
                self.url = "https://www.uc3m.es/vida-universitaria"
                self.text = '<html><head><title>Vida universitaria</title></head><body><p>Campus life</p></body></html>'
            elif url == "https://www.uc3m.es/vida-universitaria":
                self.url = "https://www.uc3m.es/vida-universitaria"
                self.text = '<html><head><title>Vida universitaria</title></head><body><p>Campus life</p></body></html>'
            elif url.endswith("sitemap.xml"):
                self.url = url
                self.text = "<urlset><url><loc>http://www.uc3m.es/Vida_Universitaria</loc></url><url><loc>https://www.uc3m.es/vida-universitaria</loc></url></urlset>"
            elif url.endswith("robots.txt"):
                self.url = url
                self.text = "User-agent: *\nAllow: /"
            else:
                self.url = url
                self.text = '<html><head><title>Seed</title></head><body><p>Seed</p></body></html>'
            self.content = self.text.encode("utf-8")

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=10, headers=None):
        return FakeResponse(url)

    snapshot, pages = crawl_site("https://www.uc3m.es/", page_cap=2, fetch=fake_get)

    assert snapshot.base_url == "https://www.uc3m.es/"
    assert len(pages) == 2
    assert sum(page.url.endswith("vida-universitaria") for page in pages) == 1
    assert any(page.url == "https://www.uc3m.es/vida-universitaria" for page in pages)


def test_crawl_site_ignores_desktop_query_variant():
    class FakeResponse:
        def __init__(self, url: str):
            self.status_code = 200
            self.headers = {"content-type": "text/html; charset=utf-8"}
            self.url = url
            if url.endswith("sitemap.xml"):
                self.text = "<urlset><url><loc>https://www.uc3m.es/vida-universitaria?d=Desktop</loc></url><url><loc>https://www.uc3m.es/vida-universitaria</loc></url></urlset>"
            elif url.endswith("robots.txt"):
                self.text = "User-agent: *\nAllow: /"
            elif url == "https://www.uc3m.es/":
                self.text = '<html><head><title>Home</title></head><body><p>Seed</p></body></html>'
            else:
                self.text = '<html><head><title>Vida universitaria</title></head><body><p>Campus life</p></body></html>'
            self.content = self.text.encode("utf-8")

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=10, headers=None):
        return FakeResponse(url)

    snapshot, pages = crawl_site("https://www.uc3m.es/", page_cap=2, fetch=fake_get)

    assert snapshot.base_url == "https://www.uc3m.es/"
    assert len(pages) == 2
    assert any(page.url == "https://www.uc3m.es/vida-universitaria" for page in pages)
    assert sum(page.url == "https://www.uc3m.es/vida-universitaria" for page in pages) == 1


def test_crawl_site_skips_soft_404_error_pages():
    class FakeResponse:
        def __init__(self, url: str):
            self.status_code = 200
            self.headers = {"content-type": "text/html; charset=utf-8"}
            self.url = url
            if url.endswith("sitemap.xml"):
                self.text = "<urlset><url><loc>https://www.uc3m.es/ss/Satellite/UC3MInstitucional/es/PortadaMiniSiteB/1371206944418/Becas_Alumni</loc></url><url><loc>https://www.uc3m.es/page-2</loc></url></urlset>"
            elif url.endswith("Becas_Alumni"):
                self.text = "<html><head><title>Parece que no existe en la web una página con esta dirección.</title></head><body><p>Parece que no existe en la web una página con esta dirección.</p><p>Pruebe a buscar en nuestro sitio web o a navegar por las principales secciones.</p></body></html>"
            elif url.endswith("page-2"):
                self.text = '<html><head><title>From sitemap</title></head><body><p>Second</p></body></html>'
            elif url.endswith("robots.txt"):
                self.text = "User-agent: *\nAllow: /"
            else:
                self.text = '<html><head><title>Seed</title></head><body><p>Seed</p></body></html>'
            self.content = self.text.encode("utf-8")

        def raise_for_status(self):
            return None

    def fake_get(url, timeout=10, headers=None):
        return FakeResponse(url)

    snapshot, pages = crawl_site("https://www.uc3m.es/", page_cap=3, fetch=fake_get)

    assert snapshot.base_url == "https://www.uc3m.es/"
    assert all("Becas_Alumni" not in page.url for page in pages)
    assert any(page.url == "https://www.uc3m.es/page-2" for page in pages)
