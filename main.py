import os
import time
import random
from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logging, clean_text
from bot.twitter_client import setup_twitter_client, search_replies_to_tweet, post_image_with_tweet
import logging
import tweepy

# Load environment variables
load_dotenv()


def validate_env_variables(logger):
    """
    Ensure required environment variables are set.
    """
    required_vars = ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET", "BOT_USER_ID"]
    for var in required_vars:
        if not os.getenv(var):
            logger.error(f"Environment variable {var} is not set.")
            raise EnvironmentError(f"Missing required environment variable: {var}")


def post_tweet(bot, client, api, logger):
    """
    Posts either a text tweet or a random meme with an optional caption.
    """
    logger.info("Starting the post_tweet process...")

    try:
        if random.random() < 0.1:  # 10% chance for meme
            memes_folder = os.path.join(os.getcwd(), 'memes')
            supported_formats = ('.jpg', '.jpeg', '.png', '.gif')

            if not os.path.exists(memes_folder):
                logger.error(f"'memes' folder does not exist at {memes_folder}.")
                return None

            images = [file for file in os.listdir(memes_folder) if file.lower().endswith(supported_formats)]
            if images:
                image_path = os.path.join(memes_folder, random.choice(images))
                
                meme_captions = [
                    "This meme? Pure gold. 🪙✨ #Tetherballcoin",
                    "Some things you just can't unsee. 😂 #CryptoHumor",
                    "Hodlers will understand. 💎🙌 #Tetherballcoin",
                    "Because laughter is the best investment. 😂📈 #CryptoMemes",
                    "Meme game strong, just like our coin. 🚀🔥 #Tetherballcoin",
                    "Surviving the market one meme at a time. 🐻📉 #BlockchainBlues",
                    "When reality is funnier than the meme. 🤯🤣 #Web3Life",
                    "Mood: Exactly this. 👀😂 #CryptoLife",
                    "Who needs financial advice when you've got memes? 📲🤣 #Tetherball",
                    "Come swing with us! @tetherballcoin",
                    "Be a baller $TBALL"
                ]

                caption = random.choice(meme_captions)
                logger.info(f"Selected meme caption: {caption}")
                return post_image_with_tweet(client, api, caption, image_path, logger)
            else:
                logger.warning("No images found in the memes folder. Falling back to text tweet.")

        prompts = [
            "Make a post about Crypto. Be funny, educational, and engage user replies.",
            "Make a post about Tech. Be funny, educational, and engage user replies.",
            "Make a post about AI. Be funny, educational, and engage user replies.",
            "Make a post about NFTs. Be funny, educational, and engage user replies.",
            "Make a post about Web3. Be funny, educational, and engage user replies.",
            "Make a post about Blockchain. Be funny, educational, and engage user replies.",
            "Make a post about Finance. Be funny, educational, and engage user replies.",
            "Make a post about Computer Programming. Be funny, educational, and engage user replies.",
            "Make a joke about being an AI.",
            "Make a post about Cybersecurity. Be funny, educational, and engage user replies.",
            "Make a joke comparing your dating life to blockchain."
        ]

        prompt = random.choice(prompts)
        logger.info(f"Selected prompt: {prompt}")
        tweet = bot.generate_response(prompt)
        logger.info(f"Generated tweet: {tweet}")
        return client.create_tweet(text=tweet).data.get('id')

    except Exception as e:
        logger.error("Error while posting tweet.", exc_info=True)
        return None


def reply_to_last_three(bot, client, logger, tweet_id, since_id=None):
    """
    Reply to the last three comments on a specific tweet.
    """
    try:
        bot_user_id = os.getenv("BOT_USER_ID")
        replies = search_replies_to_tweet(client, tweet_id, bot_user_id)
        if not replies:
            logger.info("No new replies found.")
            return since_id

        sorted_replies = sorted(replies, key=lambda x: x.id)
        new_replies = [reply for reply in sorted_replies if not since_id or reply.id > since_id]
        latest_replies = new_replies[-3:] if new_replies else []
        
        if not latest_replies:
            logger.info("No new replies since last check.")
            return since_id

        for reply in latest_replies:
            logger.info(f"Replying to: {reply.text}")
            response = bot.generate_response(reply.text)
            client.create_tweet(text=response, in_reply_to_tweet_id=reply.id)
        
        return latest_replies[-1].id if latest_replies else since_id

    except Exception as e:
        logger.error("Error while replying to the tweets.", exc_info=True)
        return since_id


def main():
    logger = setup_logging()
    logger.info("Starting the bot...")

    try:
        validate_env_variables(logger)
        bot = PersonalityBot(model_path="./fine_tuned_personality_bot/", logger=logger)
        client = setup_twitter_client()
        api = tweepy.API(tweepy.OAuth1UserHandler(
            consumer_key=os.getenv('API_KEY'),
            consumer_secret=os.getenv('API_SECRET'),
            access_token=os.getenv('ACCESS_TOKEN'),
            access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
        ))

    except Exception as e:
        logger.error("Initialization error", exc_info=True)
        return

    # Initialize timing parameters
    since_id = None
    reply_check_interval = 60 * 10  # Check replies every 10 minutes
    reply_cycles = 2  # Number of reply checking cycles before new tweet
    post_cooldown = 60 * 5  # 5 minutes between posts

    # Add rate limit tracking
    rate_limit_hits = 0
    max_rate_limit_hits = 3  # Maximum number of rate limit hits before longer pause
    daily_post_count = 0
    last_reset_time = time.time()
    daily_post_limit = 100

    while True:
        try:
            current_time = time.time()
            # Reset counters every 24 hours
            if current_time - last_reset_time >= 24 * 60 * 60:
                daily_post_count = 0
                rate_limit_hits = 0
                last_reset_time = current_time
                logger.info("Reset daily counters")

            logger.info(f"Current daily post count: {daily_post_count}/{daily_post_limit}")
            logger.info("Starting a new bot cycle...")

            if daily_post_count >= daily_post_limit:
                logger.warning("Daily post limit reached, waiting for reset...")
                time.sleep(60 * 30)  # Wait 30 minutes before checking again
                continue

            # Step 1: Post a tweet or meme
            tweet_id = post_tweet(bot, client, api, logger)
            if tweet_id:
                daily_post_count += 1
                logger.info(f"Posted tweet with ID: {tweet_id}")
                
                # Step 2: Multiple cycles of checking replies
                for cycle in range(reply_cycles):
                    if daily_post_count >= daily_post_limit:
                        logger.warning("Daily post limit reached during reply cycle")
                        break

                    logger.info(f"Starting reply check cycle {cycle + 1}/{reply_cycles}")
                    
                    since_id = reply_to_last_three(bot, client, logger, tweet_id, since_id)
                    logger.info(f"Completed reply cycle {cycle + 1}")
                    
                    # Only sleep if it's not the last cycle
                    if cycle < reply_cycles - 1:
                        logger.info(f"Sleeping for {reply_check_interval // 60} minutes before next reply check...")
                        time.sleep(reply_check_interval)
            else:
                logger.error("Tweet posting failed. Waiting before retry...")
                time.sleep(post_cooldown)
                continue

            # Cool down before next post
            logger.info(f"Cooling down for {post_cooldown // 60} minutes before next post...")
            time.sleep(post_cooldown)

        except tweepy.errors.TooManyRequests as e:
            rate_limit_hits += 1
            logger.error(f"Rate limit hit #{rate_limit_hits}. Retrying after rate limit reset...")
            
            if rate_limit_hits >= max_rate_limit_hits:
                logger.warning("Multiple rate limits hit. Taking a longer break...")
                time.sleep(60 * 60 * 2)  # 2 hour break
                rate_limit_hits = 0  # Reset counter
                continue
                
            reset_time = int(e.response.headers.get('x-rate-limit-reset', time.time() + 60))
            sleep_time = reset_time - int(time.time())
            logger.info(f"Sleeping for {sleep_time} seconds until rate limit reset.")
            time.sleep(max(0, sleep_time))

        except Exception as e:
            logger.error("Error in main loop", exc_info=True)
            logger.info("Retrying after 15 minutes due to error...")
            time.sleep(60 * 15)


if __name__ == "__main__":
    main()