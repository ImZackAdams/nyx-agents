import feedparser
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse

def get_latest_article():
    feed_urls = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/?",
        "https://cointelegraph.com/rss"
    ]
    
    latest_article = None
    latest_time = None
    
    # Find the most recent article
    for url in feed_urls:
        feed = feedparser.parse(url)
        if not feed.entries:
            continue
            
        for entry in feed.entries:
            pub_time = entry.get('published_parsed') or entry.get('updated_parsed')
            if pub_time and (latest_time is None or pub_time > latest_time):
                latest_time = pub_time
                latest_article = entry

    if not latest_article:
        return None, None

    # Get article details
    title = latest_article.get('title', '')
    url = latest_article.get('link', '')

    # Remove query parameters to potentially avoid suspicion
    parsed = urlparse(url)
    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

    return title, clean_url

def get_full_article_content(url):
    """
    Use Playwright to emulate a real browser, navigate to the page, and extract the content.
    This approach often bypasses basic 403 responses from sites that don't like bots.
    """
    with sync_playwright() as p:
        # Launch a headless browser (you can set headless=False to see the browser window)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/114.0.5735.110 Safari/537.36"
            )
        )

        page = context.new_page()

        # Try to navigate to the article URL
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            browser.close()
            return f"Could not retrieve the article content (Navigation Error: {e})."

        if not response or response.status != 200:
            browser.close()
            return f"Could not retrieve the article content (Status Code: {response.status if response else 'No Response'})."
        
        # Wait for a potential main content element - adjust selectors/time as needed
        # This might help ensure that the dynamic content is loaded
        page.wait_for_timeout(3000)  # Wait 3 seconds, sometimes needed for ads and paywalls

        # Get the rendered HTML
        html = page.content()
        browser.close()

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        domain = urlparse(url).netloc.lower()
        content = extract_content(soup, domain)
        return content if content else "No full content found."

def extract_content(soup, domain):
    """
    Extract article content using domain-specific heuristics.
    """
    if "coindesk.com" in domain:
        # CoinDesk specific
        article_body = soup.find("div", class_="article-pharagraphs")
        if not article_body:
            article_body = soup.find("article")
        return extract_paragraphs(article_body)
    elif "cointelegraph.com" in domain:
        # Cointelegraph selectors
        possible_selectors = [
            "div.post-content", 
            "div.post-content__text",
            "div.article__body",
            "div.post-page__article-content"
        ]
        for selector in possible_selectors:
            article_body = soup.select_one(selector)
            if article_body:
                text = extract_paragraphs(article_body)
                if text:
                    return text

        article_body = soup.find("article") or soup.find("main") or soup.find("body")
        return extract_paragraphs(article_body)

    # Fallback
    article_body = soup.find("article") or soup.find("main") or soup.find("body")
    return extract_paragraphs(article_body)

def extract_paragraphs(container):
    """
    Extract text from paragraph tags.
    """
    if not container:
        return None
    paragraphs = container.find_all("p")
    text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
    return text.strip() if text.strip() else None

if __name__ == "__main__":
    title, url = get_latest_article()
    if title and url:
        print(f"Latest Article:\n{title}")
        print(f"\nURL: {url}")
        content = get_full_article_content(url)
        print(f"\nContent:\n{content}")
    else:
        print("No article found")
