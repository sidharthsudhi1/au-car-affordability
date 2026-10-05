"""Redbook new-car detail scraper (Selenium for navigation, BeautifulSoup for parsing).

Opens the Redbook results page, clicks into each listing's detail page, and extracts
specification tiles plus the "Price When New" valuation. Redbook now sits behind a bot
challenge, so this runs only where automated access is permitted; it never tries to
bypass the challenge.

    python scraping/redbook_scraper.py --pages 2 --per-page 10 --out redbook_sample.csv
"""

import argparse
import random
import re
import time
from pathlib import Path
from urllib import robotparser
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE = "https://www.redbook.com.au"
RESULTS_URL = (
    f"{BASE}/cars/results/?q=(And.Service.redbook._.RecordType.car._.CountryCode.AU."
    "_.YearRange.range(2014..2024).)&sort=Price"
)
CARD_CSS = "div.listing-item.card.slimline, article"
DETAIL_CSS = ".key-details-wrapper, .vehicle-details, .specs, .rb-vehicle"
WAIT = 12
PAUSE = (1.5, 3.0)
YEAR_RE = re.compile(r"\b(20(?:1[4-9]|2[0-4]))\b")


def pause():
    time.sleep(random.uniform(*PAUSE))


def allowed(url: str) -> bool:
    rp = robotparser.RobotFileParser(f"{BASE}/robots.txt")
    rp.read()
    return rp.can_fetch("*", url)


def build_driver(headless: bool) -> webdriver.Chrome:
    opts = ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,1000")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(40)
    return driver


def accept_cookies(driver) -> None:
    for by, sel in [
        (By.CSS_SELECTOR, "button[aria-label*='accept' i]"),
        (By.XPATH, "//button[contains(.,'Accept') or contains(.,'I agree') or contains(.,'Agree')]"),
    ]:
        try:
            WebDriverWait(driver, 3).until(EC.element_to_be_clickable((by, sel))).click()
            pause()
            return
        except TimeoutException:
            continue


def cards(driver):
    return driver.find_elements(By.CSS_SELECTOR, "div.listing-item.card.slimline") or driver.find_elements(
        By.CSS_SELECTOR, "article, li.listing-item"
    )


def open_detail(driver, card) -> bool:
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
    pause()
    try:
        btn = card.find_element(By.XPATH, ".//a[contains(., 'View details') or contains(., 'View Details')]")
    except NoSuchElementException:
        btn = next((b for css in ("a.btn.btn-primary", "a.js-encode-search")
                    for b in card.find_elements(By.CSS_SELECTOR, css)), None)
    if btn is None:
        return False
    try:
        driver.execute_script("arguments[0].click();", btn)
    except (ElementClickInterceptedException, StaleElementReferenceException):
        return False
    return True


def text(node) -> str | None:
    return (node.get_text(" ", strip=True) or None) if node else None


def tile(soup: BeautifulSoup, *labels: str) -> str | None:
    wanted = {label.lower() for label in labels}
    for item in soup.select(".key-details-item"):
        caption = text(item.select_one(".key-details-item-caption, .key-details-item-caption-ancap"))
        if caption and caption.lower() in wanted:
            return text(item.select_one(".key-details-item-title"))
    return None


def price_when_new(soup: BeautifulSoup) -> str | None:
    for block in soup.select(".grid-item, .valuation, .price-block, .rb-valuation"):
        body = block.get_text(" ", strip=True)
        if re.search(r"price\s*when\s*new", body, re.I):
            val = block.select_one(".valuation-price")
            if val:
                return text(val)
            m = re.search(r"\$\s?[\d,]+", body)
            if m:
                return m.group(0)
    m = re.search(r"Price\s*When\s*New\s*[:\-]?\s*(\$\s?[\d,]+)", soup.get_text(" ", strip=True), re.I)
    return m.group(1) if m else None


def parse_detail(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    year = YEAR_RE.search(soup.get_text(" ", strip=True))
    return {
        "title": text(soup.select_one("h1, .vehicle-title, .rb-vehicle-title")),
        "year": int(year.group(1)) if year else None,
        "body_type": tile(soup, "Body Type"),
        "engine": tile(soup, "Engine", "Engine Type"),
        "transmission": tile(soup, "Transmission"),
        "fuel_consumption": tile(soup, "Fuel Combined", "Fuel Consumption"),
        "drive_type": tile(soup, "Drive Type", "Drivetrain"),
        "ancap": tile(soup, "ANCAP Rating", "ANCAP Safety Rating"),
        "price_when_new": price_when_new(soup),
        "url": url,
    }


def goto_page(driver, page: int) -> None:
    parts = list(urlsplit(RESULTS_URL))
    q = parse_qs(parts[3], keep_blank_values=True)
    q["page"] = [str(page)]
    parts[3] = urlencode(q, doseq=True)
    driver.get(urlunsplit(parts))
    accept_cookies(driver)
    WebDriverWait(driver, WAIT).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, CARD_CSS)))


def scrape(pages: int, per_page: int, headless: bool) -> pd.DataFrame:
    if not allowed(RESULTS_URL):
        raise SystemExit("robots.txt disallows the results page; not scraping")
    driver = build_driver(headless)
    rows = []
    try:
        for page in range(1, pages + 1):
            goto_page(driver, page)
            for i in range(min(per_page, len(cards(driver)))):
                try:
                    if not open_detail(driver, cards(driver)[i]):
                        continue
                    WebDriverWait(driver, WAIT).until(EC.presence_of_element_located((By.CSS_SELECTOR, DETAIL_CSS)))
                    rows.append(parse_detail(driver.page_source, driver.current_url))
                    print(f"page {page} card {i + 1}: {rows[-1]['title']}")
                    driver.back()
                    WebDriverWait(driver, WAIT).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, CARD_CSS)))
                    pause()
                except (TimeoutException, StaleElementReferenceException):
                    goto_page(driver, page)
    finally:
        driver.quit()
    df = pd.DataFrame(rows)
    if not df.empty:
        df["price_when_new_aud"] = pd.to_numeric(df["price_when_new"].str.replace(r"[^\d]", "", regex=True))
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--per-page", type=int, default=10)
    ap.add_argument("--out", type=Path, default=Path("redbook_sample.csv"))
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()
    df = scrape(args.pages, args.per_page, args.headless)
    df.to_csv(args.out, index=False)
    print(f"saved {len(df)} rows to {args.out}")


if __name__ == "__main__":
    main()
