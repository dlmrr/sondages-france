"""
Harris Interactive scraper.
URL: https://harris-interactive.fr/catalogue/
Category filtering, no visible dates on cards. May need Selenium.
"""
import logging
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base import get_soup, make_driver, save_polls

log = logging.getLogger("harris")

CATALOGUE_URL = "https://harris-interactive.fr/catalogue/"
# Old paginated URL (may still work for archived polls)
LEGACY_URL = "https://harris-interactive.fr/actualite/sondages-publies/page/{page}/"


def scrape():
    polls = []

    # Try the new catalogue page with Selenium (JS-rendered)
    driver = make_driver(headless=True)
    try:
        driver.get(CATALOGUE_URL)
        time.sleep(3)

        # Scroll to load all items
        last_count = 0
        for attempt in range(50):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Try clicking load more / pagination
            try:
                load_more = driver.find_element(By.CSS_SELECTOR, ".load-more, .more, [data-page], .next")
                load_more.click()
                time.sleep(2)
            except Exception:
                pass

            soup = BeautifulSoup(driver.page_source, "lxml")
            items = soup.select("article, .catalogue-item, .study-item, .feed-container, .card")
            current_count = len(items)

            if current_count == last_count and attempt > 3:
                break
            last_count = current_count
            log.info(f"Scroll {attempt+1}: {current_count} items loaded")

        # Parse all loaded items
        soup = BeautifulSoup(driver.page_source, "lxml")

        # Try various selectors
        for selector in [
            "article",
            ".catalogue-item",
            ".study-item",
            "li.feed-container",
            ".card",
        ]:
            items = soup.select(selector)
            if items:
                log.info(f"Found {len(items)} items with selector '{selector}'")
                break

        for item in items:
            try:
                link_tag = item.find("a", href=True)
                if not link_tag:
                    continue
                link = link_tag["href"]
                if not link.startswith("http"):
                    link = "https://harris-interactive.fr" + link

                title_tag = item.find(["h2", "h3", "h4"])
                subject = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)

                date_tag = item.find("time") or item.find("span", class_="entry-date") or item.find("span", class_="date")
                date = date_tag.get_text(strip=True) if date_tag else ""

                if subject and len(subject) > 3:
                    polls.append((date, subject, link))
            except Exception as e:
                log.debug(f"Error parsing item: {e}")

    finally:
        driver.quit()

    # Also try legacy paginated URL
    log.info("Trying legacy paginated URL...")
    for page in range(1, 300):
        url = LEGACY_URL.format(page=page)
        soup = get_soup(url)
        if soup is None:
            break

        items = soup.select("li.feed-container, article")
        if not items:
            break

        for item in items:
            try:
                date_tag = item.find("span", class_="entry-date")
                date = date_tag.get_text(strip=True) if date_tag else ""
                link_tag = item.find("a", href=True)
                link = link_tag["href"] if link_tag else ""
                subject = link_tag.get_text(strip=True) if link_tag else ""
                if subject:
                    polls.append((date, subject, link))
            except Exception as e:
                log.debug(f"Error parsing legacy item: {e}")

        log.info(f"Legacy page {page}: {len(items)} items, {len(polls)} total")
        time.sleep(1)

    return save_polls(polls, "HARRIS INTERACTIVE")


if __name__ == "__main__":
    scrape()
