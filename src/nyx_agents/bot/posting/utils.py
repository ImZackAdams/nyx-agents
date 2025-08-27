import time

def apply_delay(duration, logger=None):
    if logger:
        logger.info(f"Waiting {duration // 60} minutes...")
    time.sleep(duration)

def search_replies_to_tweet(client, tweet_id, bot_user_id, since_id=None, logger=None):
    query = f"conversation_id:{tweet_id} -from:{bot_user_id}"
    try:
        results = client.search_recent_tweets(
            query=query,
            tweet_fields=["author_id", "text", "id"],
            since_id=since_id
        )
        return results.data or []
    except Exception:
        if logger:
            logger.exception(f"Failed to fetch replies for tweet ID {tweet_id}.")
        return []
