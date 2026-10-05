# redbook_click_scrape.py
import re, time, random
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import (
    TimeoutException, StaleElementReferenceException,
    ElementClickInterceptedException, NoSuchElementException
)

RESULTS_URL = "https://www.redbook.com.au/cars/results/?q=(And.Service.redbook._.RecordType.car._.CountryCode.AU._.YearRange.range(2014..2024).)&sort=Price"

MAX_PAGES = 1             # increase after testing
MAX_CARS_PER_PAGE = 10    # increase after testing
WAIT = 12
PAUSE = (1.0, 2.2)
OUT_CSV = Path("redbook_sample.csv")

def sleep():
    time.sleep(random.uniform(*PAUSE))

def build_driver(headless=False):
    opts = ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140 Safari/537.36")
    drv = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=opts)
    drv.set_page_load_timeout(40)
    return drv

def accept_cookies(driver):
    # Try common selectors; ignore failures
    candidates = [
        "button[aria-label*='accept' i]",
        "//button[contains(.,'Accept') or contains(.,'I agree') or contains(.,'Agree')]",
        ".accept, .consent"
    ]
    for sel in candidates:
        try:
            if sel.startswith("//"):
                el = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, sel)))
            else:
                el = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
            el.click()
            sleep()
            return
        except Exception:
            pass

def get_cards(driver):
    cards = driver.find_elements(By.CSS_SELECTOR, "div.listing-item.card.slimline")
    if not cards:
        cards = driver.find_elements(By.CSS_SELECTOR, "article, li.listing-item")
    return cards

def click_view_details(driver, card):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
    sleep()
    try:
        # Prefer visible text
        btn = card.find_element(By.XPATH, ".//a[contains(., 'View details') or contains(., 'View Details')]")
    except NoSuchElementException:
        # Fallback classes
        for css in ("a.btn.btn-primary", "a.js-encode-search"):
            try:
                btn = card.find_element(By.CSS_SELECTOR, css)
                break
            except NoSuchElementException:
                btn = None
        if not btn:
            return False

    try:
        driver.execute_script("arguments[0].click();", btn)
    except (ElementClickInterceptedException, StaleElementReferenceException):
        try:
            btn.click()
        except Exception:
            return False
    return True

def txt(el):
    if not el: return None
    t = el.get_text(" ", strip=True)
    return t if t else None

def find_tile_value(soup, labels):
    if isinstance(labels, str):
        labels = [labels]
    labels = [l.lower() for l in labels]
    for item in soup.select(".key-details-item"):
        cap = txt(item.select_one(".key-details-item-caption, .key-details-item-caption-ancap"))
        if not cap: continue
        if cap.strip().lower() in labels:
            return txt(item.select_one(".key-details-item-title"))
    return None

def extract_price_when_new(soup):
    # Search blocks that contain "Price When New"
    for block in soup.select(".grid-item, .valuation, .price-block, .rb-valuation"):
        text = block.get_text(" ", strip=True)
        if re.search(r"price\s*when\s*new", text, re.I):
            val = block.select_one(".valuation-price")
            if val: return txt(val)
            m = re.search(r"\$\s?[\d,]+", text)
            if m: return m.group(0)
    m = re.search(r"Price\s*When\s*New\s*[:\-]?\s*(\$\s?[\d,]+)", soup.get_text(" ", strip=True), re.I)
    return m.group(1) if m else None

def parse_detail(driver):
    soup = BeautifulSoup(driver.page_source, "lxml")
    title = txt(soup.select_one("h1, .vehicle-title, .rb-vehicle-title"))
    # year anywhere on page
    m = re.search(r"\b(2014|2015|2016|2017|2018|2019|2020|2021|2022|2023|2024)\b", soup.get_text(" ", strip=True))
    year = int(m.group(0)) if m else None
    return {
        "Title": title,
        "Year": year,
        "Body Type": find_tile_value(soup, "Body Type"),
        "Engine": find_tile_value(soup, ["Engine", "Engine Type"]),
        "Transmission": find_tile_value(soup, "Transmission"),
        "Fuel Consumption": find_tile_value(soup, ["Fuel Combined", "Fuel Consumption"]),
        "Drive Type": find_tile_value(soup, ["Drive Type", "Drivetrain"]),
        "ANCAP Rating": find_tile_value(soup, ["ANCAP Rating", "ANCAP Safety Rating"]),
        "Price When New": extract_price_when_new(soup),
        "URL": driver.current_url,
    }

def main():
    driver = build_driver(headless=False)  # set True after it works
    driver.get(RESULTS_URL)
    accept_cookies(driver)

    rows = []

    for page in range(1, MAX_PAGES + 1):
        if page > 1:
            # try numbered pagination first
            try:
                page_btn = driver.find_element(By.XPATH, f"//a[normalize-space()='{page}']")
                driver.execute_script("arguments[0].click();", page_btn)
                sleep()
                accept_cookies(driver)
            except Exception:
                from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode
                parts = list(urlsplit(driver.current_url))
                q = parse_qs(parts[3], keep_blank_values=True)
                q["page"] = [str(page)]
                parts[3] = urlencode(q, doseq=True)
                driver.get(urlunsplit(parts))
                sleep()
                accept_cookies(driver)

        WebDriverWait(driver, WAIT).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.listing-item.card.slimline, article"))
        )

        cards = get_cards(driver)
        print(f"[page {page}] cards: {len(cards)}")

        for idx, card in enumerate(cards[:MAX_CARS_PER_PAGE], start=1):
            try:
                if not click_view_details(driver, card):
                    print(f"  [{idx}] could not click View details")
                    continue

                WebDriverWait(driver, WAIT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".key-details-wrapper, .vehicle-details, .specs, .rb-vehicle"))
                )
                sleep()

                data = parse_detail(driver)
                print(f"  [{idx}] ✓ {data.get('Title')}")
                rows.append(data)

                driver.back()
                WebDriverWait(driver, WAIT).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.listing-item.card.slimline, article"))
                )
                cards = get_cards(driver)  # refresh references
                sleep()
            except (TimeoutException, StaleElementReferenceException) as e:
                print(f"  [{idx}] timeout/stale, recovering: {e}")
                driver.get(RESULTS_URL)
                accept_cookies(driver)
                WebDriverWait(driver, WAIT).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.listing-item.card.slimline, article"))
                )
                cards = get_cards(driver)

    driver.quit()

    df = pd.DataFrame(rows)

    # optional: numeric price
    def to_num(s):
        if not s: return None
        s = re.sub(r"[^\d]", "", s)
        return float(s) if s else None

    if not df.empty:
        df["Price When New (num)"] = df["Price When New"].map(to_num)

    df.to_csv(OUT_CSV, index=False)
    print(f"\n✅ Saved {len(df)} rows → {OUT_CSV.resolve()}")

if __name__ == "__main__":
    main()
