import os
import sys
import gc
import logging
from pathlib import Path
import warnings
import feedparser
import requests
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore")

# Add current file directory to path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.bot import PersonalityBot
from bot.utilities import setup_logger
from bot.configs.posting_config import MAX_TWEET_LENGTH, MIN_TWEET_LENGTH

# Define new constants for articles, allowing even more room for detail
ARTICLE_MAX_TWEET_LENGTH = 400  
ARTICLE_MIN_TWEET_LENGTH = 50  

def fetch_latest_article(feed_url="https://www.coindesk.com/arc/outboundfeeds/rss/?"):
    feed = feedparser.parse(feed_url)
    if feed.entries:
        return feed.entries[0]
    return None

def get_full_article_text(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return f"Failed to retrieve article: {str(e)}"

    soup = BeautifulSoup(response.text, 'html.parser')

    # Remove non-content elements
    for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
        element.decompose()

    content_selectors = [
        ('article', None),
        ('main', None),
        ('div', 'article-content'),
        ('div', 'post-content'),
        ('div', 'entry-content'),
        ('div', 'content-body'),
    ]

    for tag, class_name in content_selectors:
        container = soup.find(tag, class_=class_name) if class_name else soup.find(tag)
        if container:
            text_blocks = []
            for p in container.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = p.get_text(strip=True)
                if text and len(text) > 10:
                    text_blocks.append(text)
            if text_blocks:
                return "\n\n".join(text_blocks)

    return "Could not find main content."

def simulate_bot_responses():
    print("\n" + "="*80)
    print("      CRYPTO NEWS HEADLINE SUMMARIZER")
    print("="*80 + "\n")

    model_path = "./mistral_qlora_finetuned"
    if not Path(model_path).exists():
        print("Sorry, the model could not be found at the specified path.")
        return

    logger = setup_logger("article_sim")

    try:
        bot = PersonalityBot(model_path=model_path, logger=logger)

        print("Fetching the latest article from CoinDesk...")
        latest_article = fetch_latest_article()

        if latest_article:
            title = latest_article.get("title", "No title provided")
            link = latest_article.get("link", "No link provided")

            print("\n----------------------------------------")
            print("          LATEST ARTICLE DETAILS")
            print("----------------------------------------\n")
            print(f"Title: {title}")
            print(f"Link:  {link}")

            print("\nExtracting article content. Please wait...")
            full_content = get_full_article_text(link)

            current_max_tweet_length = ARTICLE_MAX_TWEET_LENGTH
            current_min_tweet_length = ARTICLE_MIN_TWEET_LENGTH

            # Include an excerpt of the article content for context
            excerpt = full_content[:1000] if full_content and isinstance(full_content, str) else ""

            prompt = (
                "You are Athena (@Athena_TBALL), a queen of crypto Twitter known for detail and insight. "
                "Summarize the following headline and content into a single tweet focusing on developer growth, "
                "adoption, and key insights from the article. Include numbers mentioned, relevant chain hashtags, "
                "and start with 🚀. Provide a more detailed perspective than just one sentence.\n\n"
                f"Title: {title}\n\n"
                f"Article Excerpt:\n{excerpt}\n\n"
                f"Requirements:\n"
                f"1. Start with 🚀\n"
                f"2. Include any important numbers or stats from the excerpt\n"
                f"3. Include a chain-specific hashtag if a chain is mentioned\n"
                f"4. Be detailed but still concise—pack multiple facts in one tweet\n"
                f"5. Keep length under {current_max_tweet_length} characters.\n"
            )

            print("\n----------------------------------------")
            print("           GENERATING SUMMARY")
            print("----------------------------------------\n")

            summary = bot.generate_response(prompt)

            # Attempt to include the link
            if summary and current_min_tweet_length <= len(summary) <= current_max_tweet_length:
                candidate = f"{summary.strip()} {link}"
                if len(candidate) > current_max_tweet_length:
                    # Need to truncate the summary to make room for the link
                    allowed_summary_length = current_max_tweet_length - (len(link) + 1)
                    truncated_summary = candidate[:allowed_summary_length].rstrip()
                    final_tweet = f"{truncated_summary} {link}"

                    if len(final_tweet) > current_max_tweet_length:
                        print("Even after truncation, we couldn't fit the link. Consider using a shorter link or summary.")
                        return
                    else:
                        summary = final_tweet
                else:
                    summary = candidate

                print("Here is the summarized tweet with the link:\n")
                print(summary)
                print(f"\nTweet length: {len(summary)} characters")
            else:
                print("No valid summary could be generated that met the length requirements.")
                if summary:
                    print(f"\nGenerated (but invalid): {summary}")
        else:
            print("No article found. Please try again later.")

    except Exception as e:
        print(f"\nAn error occurred during the simulation: {str(e)}")

    print("\n" + "="*80)

if __name__ == "__main__":
    simulate_bot_responses()
