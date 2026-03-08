"""
ODOXA scraper.
URL: https://www.odoxa.fr/les-sondages/
Uses AJAX/infinite scroll — needs Selenium to load all content.
Cards with date, category, title, link.
"""
import logging
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base import make_driver, save_polls

log = logging.getLogger("odoxa")

URL = "https://www.odoxa.fr/les-sondages/"


def scrape():
    driver = make_driver(headless=True)
    polls = []

    try:
        driver.get(URL)
        time.sleep(3)

        # Scroll down repeatedly to trigger infinite scroll / load more
        last_count = 0
        max_scroll_attempts = 100
        for attempt in range(max_scroll_attempts):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Also try clicking "load more" button if it exists
            try:
                load_more = driver.find_element(By.CSS_SELECTOR, ".load-more, .more-posts, button[data-action='load-more']")
                load_more.click()
                time.sleep(2)
            except Exception:
                pass

            soup = BeautifulSoup(driver.page_source, "lxml")
            sondages = soup.find_all("a", class_="sondage")
            if not sondages:
                sondages = soup.select("article, .sondage-item, .post-item")

            current_count = len(sondages)
            log.info(f"Scroll {attempt+1}: {current_count} items loaded")

            if current_count == last_count:
                # No new content loaded, try a few more times then stop
                if attempt > 5:
                    break
            last_count = current_count

        # Parse all loaded items
        soup = BeautifulSoup(driver.page_source, "lxml")

        # Try the old selector first
        sondages = soup.find_all("a", class_="sondage")
        if sondages:
            for item in sondages:
                try:
                    link = item.get("href", "")
                    date_span = item.find("span", class_="date")
                    date = date_span.get_text(strip=True) if date_span else ""
                    title_div = item.find("div")
                    subject = title_div.get_text(strip=True) if title_div else ""
                    if subject:
                        polls.append((date, subject, link))
                except Exception as e:
                    log.debug(f"Error parsing sondage: {e}")
        else:
            # Fallback: parse articles
            articles = soup.find_all("article")
            for article in articles:
                try:
                    link_tag = article.find("a", href=True)
                    link = link_tag["href"] if link_tag else ""
                    title_tag = article.find(["h2", "h3"])
                    subject = title_tag.get_text(strip=True) if title_tag else ""
                    time_tag = article.find("time")
                    date = time_tag.get_text(strip=True) if time_tag else ""
                    if subject:
                        polls.append((date, subject, link))
                except Exception as e:
                    log.debug(f"Error parsing article: {e}")

        log.info(f"Total items parsed: {len(polls)}")
    finally:
        driver.quit()

    return save_polls(polls, "ODOXA")


if __name__ == "__main__":
    scrape()
