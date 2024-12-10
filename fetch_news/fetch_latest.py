import feedparser

feed_url = "https://www.coindesk.com/arc/outboundfeeds/rss/?"  # Coindesk RSS feed

def fetch_latest_article(feed_url=feed_url):
    feed = feedparser.parse(feed_url)
    # Print entire feed for debugging
    # print(feed)

    if feed.entries:
        # Just take the first article
        latest_article = feed.entries[0]
        # Return title and link
        return {
            "title": latest_article.get("title", "No title"),
            "link": latest_article.get("link", "No link")
        }
    else:
        return None

if __name__ == "__main__":
    article = fetch_latest_article()
    if article:
        print("Title:", article["title"])
        print("Link:", article["link"])
    else:
        print("No latest article found.")
