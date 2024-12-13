import os
import sys
import random
import warnings
from pathlib import Path
import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
from playwright.sync_api import sync_playwright

warnings.filterwarnings("ignore")

# Add current file directory to path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.bot import PersonalityBot
from bot.utilities import setup_logger
from bot.configs.style_config import StyleConfig  # Ensure this matches your file structure

def get_latest_article():
    feed_urls = [
        "https://www.coindesk.com/arc/outboundfeeds/rss/?",
        "https://cointelegraph.com/rss"
    ]
    
    latest_article = None
    latest_time = None

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

    title = latest_article.get('title', '')
    article_url = latest_article.get('link', '')
    parsed = urlparse(article_url)
    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

    return title, clean_url

def get_full_article_content(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page = context.new_page()
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            browser.close()
            return f"Could not retrieve the article content (Navigation Error: {e})."

        if not response or response.status != 200:
            browser.close()
            return f"Could not retrieve the article content (Status Code: {response.status if response else 'No Response'})."
        
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()

        soup = BeautifulSoup(html, 'html.parser')
        domain = urlparse(url).netloc.lower()
        content = extract_content(soup, domain)
        return content if content else "No full content found."

def extract_content(soup, domain):
    if "coindesk.com" in domain:
        article_body = soup.find("div", class_="article-pharagraphs") or soup.find("article")
        return extract_paragraphs(article_body)
    elif "cointelegraph.com" in domain:
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

    article_body = soup.find("article") or soup.find("main") or soup.find("body")
    return extract_paragraphs(article_body)

def extract_paragraphs(container):
    if not container:
        return None
    paragraphs = container.find_all("p")
    text = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
    return text.strip() if text.strip() else None

def generate_summary(title, excerpt, config):
    """
    Generate a summary based on the style configuration
    """
    min_len, max_len = config.get_length_constraints()
    personality = config.get_personality_prompt()
    hooks = config.get_appropriate_hooks()
    hook = random.choice(hooks) if hooks else ""
    
    # Combined prompt with clear instructions
    prompt = (
        f"System: You are summarizing a crypto news article. "
        f"Response must be {min_len}-{max_len} characters, "
        f"include at least one hashtag and emoji, and focus on the key points.\n\n"
        f"{personality}\n\n"
        f"Article to summarize:\n"
        f"Title: {title}\n\n"
        f"Content:\n{excerpt}\n\n"
        f"Create a single summary that:\n"
        f"1. Captures the key points\n"
        f"2. Uses appropriate market terms\n"
        f"3. Includes strategic emojis\n"
        f"4. Ends with a relevant hashtag"
    )
    
    return prompt
    
    return prompt

def simulate_bot_responses():
    print("\n" + "="*80)
    print("  CRYPTO NEWS HEADLINE SUMMARIZER")
    print("="*80 + "\n")

    model_path = "./mistral_qlora_finetuned"
    if not Path(model_path).exists():
        print("Model not found at the specified path.")
        return

    logger = setup_logger("article_sim")
    bot = PersonalityBot(model_path=model_path, logger=logger)

    print("Fetching the latest article...")
    title, url = get_latest_article()

    if title and url:
        print("\n----------------------------------------")
        print("       LATEST ARTICLE DETAILS")
        print("----------------------------------------\n")
        print(f"Title: {title}")
        print(f"Link:  {url}")

        print("\nExtracting article content, please wait...")
        full_content = get_full_article_content(url)

        # We'll just provide a brief excerpt to keep it focused
        excerpt = full_content[:800] if full_content and isinstance(full_content, str) else ""

        # Create a style config instance and enable summarization mode
        config = StyleConfig.default()
        config.is_summarizing = True

        # Generate the prompt using the style configuration
        prompt = generate_summary(title, excerpt, config)

        print("\n----------------------------------------")
        print("         GENERATING TWEET SUMMARY")
        print("----------------------------------------\n")

        tweet_summary = bot.generate_response(prompt)

        if tweet_summary:
            # Print just the summary and link, no extra labels
            print(tweet_summary.strip())
            print(f"\n{url}")
        else:
            print("No summary could be generated.")
    else:
        print("No article found at this time.")

    print("\n" + "="*80)

if __name__ == "__main__":
    simulate_bot_responses()