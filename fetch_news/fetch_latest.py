import feedparser
import requests
from bs4 import BeautifulSoup

def fetch_latest_article(feed_url="https://www.coindesk.com/arc/outboundfeeds/rss/?"):
    feed = feedparser.parse(feed_url)
    if feed.entries:
        return feed.entries[0]
    else:
        return None

def get_full_article_text(url):
    response = requests.get(url)
    if response.status_code != 200:
        return f"Failed to retrieve article, status code: {response.status_code}"

    soup = BeautifulSoup(response.text, 'html.parser')


    # Uncomment the below line if you need to debug:
    # print(soup.prettify())

    # Attempt 1: Try using the <article> tag
    article_tag = soup.find('article')
    if article_tag:
        paragraphs = article_tag.find_all('p')
        if paragraphs:
            full_text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            if full_text:
                return full_text

    # Attempt 2: Try using a <main> tag
    main_tag = soup.find('main')
    if main_tag:
        paragraphs = main_tag.find_all('p')
        if paragraphs:
            full_text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            if full_text:
                return full_text

    # Attempt 3: Use known or guessed container classes (adjust as needed)
    # Inspect the page's HTML in your browser to find a suitable container.
    possible_selectors = [
        ('div', 'atbd-article-content'),
        ('div', 'article-content'),
        ('section', 'article-body'),
    ]

    for tag, class_name in possible_selectors:
        container = soup.find(tag, class_=class_name)
        if container:
            paragraphs = container.find_all('p')
            if paragraphs:
                full_text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                if full_text:
                    return full_text

    # If all attempts fail, return a message
    return "Could not find main content. Try updating selectors."

def create_summary_prompt(article_text, persona="You are a witty crypto and finance expert who explains things clearly and entertainingly"):
    # Construct a prompt for your local AI to produce a tweet-sized summary
    prompt = f"""{persona}

Summarize the following article in a single tweet (280 characters or fewer), using a slightly witty tone and including relevant hashtags if appropriate:

Article:
{article_text}
"""
    return prompt

if __name__ == "__main__":
    latest_article = fetch_latest_article()
    if latest_article:
        title = latest_article.get("title", "No title")
        link = latest_article.get("link", "No link")
        print("Title:", title)
        print("Link:", link)

        # Get the full article text
        full_content = get_full_article_text(link)
        if "Could not find main content" not in full_content and not full_content.startswith("Failed to"):
            # Generate a prompt for your local AI model
            prompt = create_summary_prompt(full_content)
            print("\nPrompt for your local AI:\n", prompt)
            # Integrate with your local AI model here.
            # local_ai_summary = your_local_ai_inference(prompt)
            # print("AI Summary Tweet:\n", local_ai_summary)
        else:
            print("Could not retrieve or parse the full article content. Please update the selectors.")
    else:
        print("No latest article found.")
