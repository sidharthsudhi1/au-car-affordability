import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("bs4")
pytest.importorskip("selenium")

SCRAPER = Path(__file__).parents[1] / "scraping" / "redbook_scraper.py"
spec = importlib.util.spec_from_file_location("redbook_scraper", SCRAPER)
scraper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scraper)

DETAIL = """
<html><body>
<h1>2021 Toyota Corolla Ascent Sport Auto</h1>
<div class="key-details-item"><span class="key-details-item-caption">Body Type</span>
  <span class="key-details-item-title">Hatchback</span></div>
<div class="key-details-item"><span class="key-details-item-caption">Transmission</span>
  <span class="key-details-item-title">Constantly Variable Transmission</span></div>
<div class="key-details-item"><span class="key-details-item-caption-ancap">ANCAP Rating</span>
  <span class="key-details-item-title">5 stars</span></div>
<div class="valuation"><span>Price When New</span><span class="valuation-price">$26,395</span></div>
</body></html>
"""


def test_parse_detail_extracts_tiles_and_price():
    row = scraper.parse_detail(DETAIL, "https://example/detail")
    assert row["title"] == "2021 Toyota Corolla Ascent Sport Auto"
    assert row["year"] == 2021
    assert row["body_type"] == "Hatchback"
    assert row["ancap"] == "5 stars"
    assert row["price_when_new"] == "$26,395"
    assert row["engine"] is None


def test_price_when_new_falls_back_to_page_text():
    soup = scraper.BeautifulSoup("<p>Price When New: $41,990 drive away</p>", "lxml")
    assert scraper.price_when_new(soup) == "$41,990"
