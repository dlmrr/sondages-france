import time
import logging
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
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
    """Create a Selenium Chrome driver using webdriver-manager."""
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(f"user-agent={HEADERS['User-Agent']}")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


def save_polls(polls, institut, filename=None):
    """Save a list of (date, subject, link) tuples to CSV."""
    if not polls:
        logging.warning(f"No polls to save for {institut}")
        return None
    df = pd.DataFrame(polls, columns=["date", "subject", "link"])
    df["institut"] = institut
    fname = filename or f"{institut.lower().replace(' ', '_')}_polls.csv"
    path = DATA_DIR / fname
    df.to_csv(path, index=False, encoding="utf-8")
    logging.info(f"Saved {len(df)} polls to {path}")
    return df
