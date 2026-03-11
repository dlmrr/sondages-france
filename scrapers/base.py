import time
import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)


def get_soup(url, retries=3, delay=1.5):
    """Fetch a URL with retries and return a BeautifulSoup object."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return BeautifulSoup(r.content, "lxml")
        except requests.RequestException as e:
            logging.warning(f"Attempt {attempt+1}/{retries} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
    logging.error(f"All {retries} attempts failed for {url}")
    return None


def make_driver(headless=True):
    """Create a Selenium Chrome driver with stealth options."""
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--lang=fr-FR")
    opts.add_argument(f"user-agent={HEADERS['User-Agent']}")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    # Remove webdriver flag from navigator
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver


def _csv_path(institut, filename=None):
    """Get the CSV path for an institute."""
    fname = filename or f"{institut.lower().replace(' ', '_')}_polls.csv"
    return DATA_DIR / fname


def load_existing_links(institut, filename=None):
    """Load the set of known links for an institute."""
    path = _csv_path(institut, filename)
    if not path.exists():
        return set()
    df = pd.read_csv(path)
    return set(df["link"].dropna().tolist())


def append_polls(new_polls, institut, columns=None, filename=None):
    """Append new polls to existing CSV, deduplicating by link."""
    columns = columns or ["date", "subject", "link"]
    if not new_polls:
        logging.info(f"No new polls for {institut}")
        return 0
    new_df = pd.DataFrame(new_polls, columns=columns)
    new_df["institut"] = institut
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _csv_path(institut, filename)

    if path.exists():
        existing = pd.read_csv(path)
        before = len(existing)
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["link"], keep="last")
        added = len(combined) - before
    else:
        combined = new_df
        added = len(new_df)

    combined.to_csv(path, index=False, encoding="utf-8")
    logging.info(f"Added {added} new polls for {institut} (total: {len(combined)})")
    return added


def save_polls(polls, institut, columns=None, filename=None):
    """Save a list of poll tuples to CSV.

    Default columns: date, subject, link.
    Pass custom columns list if scraper captures more fields.
    """
    if not polls:
        logging.warning(f"No polls to save for {institut}")
        return None
    columns = columns or ["date", "subject", "link"]
    df = pd.DataFrame(polls, columns=columns)
    df["institut"] = institut
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fname = filename or f"{institut.lower().replace(' ', '_')}_polls.csv"
    path = DATA_DIR / fname
    df.to_csv(path, index=False, encoding="utf-8")
    logging.info(f"Saved {len(df)} polls to {path}")
    return df
