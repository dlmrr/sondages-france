"""
IFOP scraper (Ifop Opinion only) — Selenium version.
URL: https://www.ifop.com/page/{N}/?s&search_marques[0]=ifop-opinion&search_formats[0]=post&is_ajax=1
~534 pages, 12 items per page, ~6398 results.
Uses Selenium to bypass reCAPTCHA. Supports resume from checkpoint.
"""
import json
import logging
import random
import sys
import time

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base import make_driver, save_polls, load_existing_links, append_polls, DATA_DIR

log = logging.getLogger("ifop")

BASE_URL = "https://www.ifop.com/page/{page}/?s&search_marques%5B0%5D=ifop-opinion&search_formats%5B0%5D=post&is_ajax=1"
COLUMNS = ["date", "subject", "brand", "sector", "link"]
CHECKPOINT_FILE = DATA_DIR / "ifop_checkpoint.json"


def _save_checkpoint(page, polls):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump({"page": page, "polls": polls}, f, ensure_ascii=False)


def _load_checkpoint():
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["page"], [tuple(p) for p in data["polls"]]
    return 1, []


def scrape(max_pages=110, resume=True, headless=False):
    start_page = 1
    polls = []

    if resume:
        start_page, polls = _load_checkpoint()
        if start_page > 1:
            print(f"  [IFOP] Resuming from page {start_page} with {len(polls)} polls already collected")
            sys.stdout.flush()

    driver = make_driver(headless=headless)
    page = start_page
    consecutive_failures = 0

    try:
        # Warm up: visit main page to get cookies/session
        driver.get("https://www.ifop.com/")
        time.sleep(2)

        while page <= max_pages:
            url = BASE_URL.format(page=page)

            # Random delay to look human — generous to avoid captcha
            delay = random.uniform(3, 7)
            if page > start_page and (page - start_page) % 20 == 0:
                pause = random.uniform(15, 30)
                print(f"  [IFOP] Taking a {pause:.0f}s break...")
                sys.stdout.flush()
                time.sleep(pause)
            time.sleep(delay)

            try:
                driver.get(url)
                # Wait for cards to appear
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".card__search"))
                    )
                except Exception:
                    pass

                soup = BeautifulSoup(driver.page_source, "lxml")
                cards = [a for a in soup.find_all("a", href=True) if a.find("div", class_="card__search")]

                if not cards:
                    # Check if captcha page
                    if "captcha" in driver.page_source.lower() and len(driver.page_source) < 3000:
                        print(f"  [IFOP] Captcha at page {page}. Waiting 60s...")
                        sys.stdout.flush()
                        _save_checkpoint(page, polls)
                        save_polls(polls, "IFOP", columns=COLUMNS)
                        time.sleep(60)
                        # Refresh and retry
                        driver.get(url)
                        time.sleep(5)
                        soup = BeautifulSoup(driver.page_source, "lxml")
                        cards = [a for a in soup.find_all("a", href=True) if a.find("div", class_="card__search")]

                    if not cards:
                        consecutive_failures += 1
                        if consecutive_failures >= 3:
                            print(f"  [IFOP] {consecutive_failures} consecutive empty pages at page {page}. Stopping.")
                            print(f"  [IFOP] Run again to resume from page {page}.")
                            _save_checkpoint(page, polls)
                            break
                        page += 1
                        continue

                consecutive_failures = 0

                for card in cards:
                    try:
                        link = card["href"]
                        h3 = card.find("h3")
                        subject = h3.get_text(strip=True) if h3 else ""

                        date_div = card.find("div", class_="card__search-day")
                        date = date_div.get_text(strip=True) if date_div else ""

                        tag_lists = card.find_all("ul", class_="card__search-tags")
                        brand = ""
                        sector = ""
                        if len(tag_lists) >= 1:
                            items = tag_lists[0].find_all("li")
                            if items:
                                brand = items[0].get_text(strip=True)
                        if len(tag_lists) >= 2:
                            items = tag_lists[1].find_all("li")
                            if items:
                                sector = items[0].get_text(strip=True)

                        if subject:
                            polls.append((date, subject, brand, sector, link))
                    except Exception as e:
                        log.debug(f"Error parsing card on page {page}: {e}")

                print(f"  [IFOP] Page {page}/{max_pages}: {len(cards)} items | {len(polls)} total")
                sys.stdout.flush()

                if page % 10 == 0:
                    _save_checkpoint(page + 1, polls)
                    save_polls(polls, "IFOP", columns=COLUMNS)

            except Exception as e:
                log.warning(f"Error on page {page}: {e}")
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    _save_checkpoint(page, polls)
                    break
                time.sleep(5)
                continue

            page += 1

    finally:
        driver.quit()

    # Clean up checkpoint on full completion
    if page > max_pages:
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()

    return save_polls(polls, "IFOP", columns=COLUMNS)


def update(max_pages=10, headless=True):
    """Incremental update. Use headless=False locally to avoid captcha."""
    known_links = load_existing_links("IFOP")
    if not known_links:
        print("  [IFOP] No existing data — skipping (full scrape needed)")
        return 0

    mode = "headless" if headless else "non-headless"
    print(f"  [IFOP] Starting incremental update ({mode})...")
    sys.stdout.flush()

    try:
        driver = make_driver(headless=headless)
    except Exception as e:
        print(f"  [IFOP] Could not start browser: {e}")
        return 0

    new_polls = []
    page = 1
    known_streak = 0

    try:
        driver.get("https://www.ifop.com/")
        time.sleep(2)

        while page <= max_pages:
            url = BASE_URL.format(page=page)
            delay = random.uniform(3, 7)
            time.sleep(delay)

            try:
                driver.get(url)
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".card__search"))
                    )
                except Exception:
                    pass

                soup = BeautifulSoup(driver.page_source, "lxml")
                cards = [a for a in soup.find_all("a", href=True) if a.find("div", class_="card__search")]

                if not cards:
                    if "captcha" in driver.page_source.lower() and len(driver.page_source) < 3000:
                        print(f"  [IFOP] Captcha detected at page {page}, stopping")
                        break
                    break

                page_new = 0
                for card in cards:
                    try:
                        link = card["href"]
                        if link in known_links:
                            known_streak += 1
                            if known_streak >= 3:
                                print(f"  [IFOP] Found 3 known polls in a row, stopping")
                                added = append_polls(new_polls, "IFOP", columns=COLUMNS)
                                print(f"  [IFOP] Added {added} new polls")
                                return added
                            continue

                        known_streak = 0
                        h3 = card.find("h3")
                        subject = h3.get_text(strip=True) if h3 else ""
                        date_div = card.find("div", class_="card__search-day")
                        date = date_div.get_text(strip=True) if date_div else ""
                        tag_lists = card.find_all("ul", class_="card__search-tags")
                        brand = ""
                        sector = ""
                        if len(tag_lists) >= 1:
                            items = tag_lists[0].find_all("li")
                            if items:
                                brand = items[0].get_text(strip=True)
                        if len(tag_lists) >= 2:
                            items = tag_lists[1].find_all("li")
                            if items:
                                sector = items[0].get_text(strip=True)
                        if subject:
                            new_polls.append((date, subject, brand, sector, link))
                            page_new += 1
                    except Exception as e:
                        log.debug(f"Error parsing card: {e}")

                print(f"  [IFOP] Page {page}: {page_new} new | {len(new_polls)} total new")
                sys.stdout.flush()

            except Exception as e:
                print(f"  [IFOP] Error on page {page}: {e}")
                break

            page += 1

    finally:
        driver.quit()

    added = append_polls(new_polls, "IFOP", columns=COLUMNS)
    print(f"  [IFOP] Added {added} new polls")
    return added


if __name__ == "__main__":
    scrape()
