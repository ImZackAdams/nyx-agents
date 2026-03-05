from __future__ import annotations

import logging
from bs4 import BeautifulSoup
from typing import Optional, Protocol
from functools import wraps
from playwright.sync_api import sync_playwright


def handle_errors(func):
    """Decorator for consistent error handling"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            if hasattr(self, "logger") and self.logger:
                self.logger.error(f"Error in {func.__name__}: {e}")
            return None
    return wrapper


class ContentExtractor(Protocol):
    def extract(self, soup: BeautifulSoup) -> Optional[str]:
        ...


class BaseExtractor:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def extract(self, soup: BeautifulSoup) -> Optional[str]:
        article_body = soup.find("article") or soup.find("main") or soup.find("body")
        if not article_body:
            return None
        self._clean_unwanted_elements(article_body)
        return self._extract_paragraphs(article_body)

    @staticmethod
    def _extract_paragraphs(container) -> Optional[str]:
        if not container:
            return None
        paragraphs = container.find_all("p")
        text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        return text.strip() if text.strip() else None

    def _clean_unwanted_elements(self, article_body):
        unwanted_selectors = [
            "script", "style", "nav", "header", "footer",
            ".ad", ".advertisement", ".social-share",
            ".related-articles", ".newsletter-signup",
        ]
        for selector in unwanted_selectors:
            for element in article_body.select(selector):
                element.decompose()


class ContentExtractionService:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.extractor = BaseExtractor(logger=self.logger)

    def get_article_content(self, url: str, logger=None) -> Optional[str]:
        logger = logger or self.logger

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                viewport={"width": 1920, "height": 1080},
            )

            context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
                """
            )

            page = context.new_page()
            page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
            })

            try:
                logger.debug(f"Fetching content from: {url}")
                response = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                if not response or response.status != 200:
                    logger.error(f"Failed to fetch {url}: Status {response.status if response else 'No Response'}")
                    return None

                try:
                    page.wait_for_selector("article, main, body", timeout=5000)
                except Exception as e:
                    logger.warning(f"Timeout waiting for content selector, proceeding anyway: {e}")

                try:
                    page.wait_for_timeout(2000)
                except Exception as e:
                    logger.warning(f"Additional wait interrupted: {e}")

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                text = self.extractor.extract(soup)
                if not text:
                    logger.warning(f"No content extracted for {url}")
                return text

            except Exception as e:
                logger.error(f"Error extracting content from {url}: {e}")
                return None
            finally:
                browser.close()
