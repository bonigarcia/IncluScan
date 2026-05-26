from pathlib import Path

from incluscan.scraper import crawl_site, extract_html_document, extract_pdf_document


def test_extract_html_document_returns_title_and_visible_text():
    html = Path("tests/fixtures/html/uc3m-sample.html").read_text(encoding="utf-8")
    doc = extract_html_document(html, "https://www.uc3m.es/")

    assert doc.title == "UC3M Sample"
    assert "Language without bias" in doc.text
    assert "var x = 1" not in doc.text


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

    snapshot, pages = crawl_site("https://www.uc3m.es/", page_cap=1, fetch=fake_get)

    assert snapshot.base_url == "https://www.uc3m.es/"
    assert len(pages) == 1
    assert pages[0].url == "https://www.uc3m.es/page-2"
