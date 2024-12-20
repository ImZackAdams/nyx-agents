def format_tweet(tweet: str) -> str:
    """Formats a tweet to ensure it meets required standards."""
    tweet = tweet.strip()
    if "#CryptoNewsQueen" not in tweet:
        tweet += " #CryptoNewsQueen"
    if not (tweet.endswith("💅") or tweet.endswith("✨")):
        tweet += " 💅"
    return tweet[:280]

def validate_tweet(tweet: str, article_title: str, article_content: str) -> bool:
    """Validates a tweet against criteria like length, hashtags, and content."""
    if len(tweet) > 280 or not tweet.strip():
        return False
    if "#CryptoNewsQueen" not in tweet or not (tweet.endswith("💅") or tweet.endswith("✨")):
        return False
    # Check if the tweet includes some terms from the article title
    if any(term in tweet.lower() for term in article_title.lower().split()[:3]):
        return True
    return False
