import os
import time
import random
from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logging
from bot.twitter_client import setup_twitter_client, search_replies_to_tweet, post_image_with_tweet
import logging
import tweepy  

# Load environment variables
load_dotenv()


def validate_env_variables(logger):
    required_vars = ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET", "BOT_USER_ID"]
    for var in required_vars:
        if not os.getenv(var):
            logger.error(f"Environment variable {var} is not set.")
            raise EnvironmentError(f"Missing required environment variable: {var}")


import random
import os

def post_tweet(bot, client, api, logger):
    """
    Posts either a text tweet or a random meme with an optional caption.
    """
    logger.info("Starting the post_tweet process...")

    try:
        if random.random() < 0.2:  # Randomly decide between text or meme
            memes_folder = os.path.join(os.getcwd(), 'memes')
            supported_formats = ('.jpg', '.jpeg', '.png', '.gif')

            if not os.path.exists(memes_folder):
                logger.error(f"'memes' folder does not exist at {memes_folder}.")
                return None

            images = [file for file in os.listdir(memes_folder) if file.lower().endswith(supported_formats)]
            if images:
                image_path = os.path.join(memes_folder, random.choice(images))
                
                # List of meme captions
                meme_captions = [
                    "This meme? Pure gold. 🪙✨ #Tetherball",
                    "Some things you just can't unsee. 😂 #CryptoHumor",
                    "Hodlers will understand. 💎🙌 #Tetherball",
                    "Because laughter is the best investment. 😂📈 #CryptoMemes",
                    "Meme game strong, just like our coin. 🚀🔥 #Tetherball",
                    "Surviving the market one meme at a time. 🐻📉 #BlockchainBlues",
                    "When reality is funnier than the meme. 🤯🤣 #Web3Life",
                    "Mood: Exactly this. 👀😂 #CryptoLife",
                    "Who needs financial advice when you’ve got memes? 📲🤣 #Tetherball"
                    
                ]


                caption = random.choice(meme_captions)
                logger.info(f"Selected meme caption: {caption}")
                return post_image_with_tweet(client, api, caption, image_path, logger)
            else:
                logger.warning("No images found in the memes folder. Falling back to text tweet.")

        # List of predefined prompts
        prompts = [
            "If Satoshi Nakamoto invited you to a dinner party, what question would you ask them first?",
            "AI can predict crypto prices, but it still can’t figure out where my missing socks go. What's your take?",
            "Describe the current crypto market using only three emojis!",
            "What’s your life hack for surviving a bear market in crypto? Asking for a friend. 🐻📉",
            "Tell us your favorite blockchain project and why it’s not just another rug pull. 😂",
            "If NFTs could talk, what would your profile picture say about you?",
            "What’s the funniest misconception about Web3 that you’ve heard? (Mine: 'It’s the sequel to Web2.')",
            "If you could automate one part of personal finance using AI, what would it be? (No, 'making me rich' doesn’t count!)",
            "What’s a random fact about blockchain that you love explaining at parties (even if no one asked)?",
            "If Elon Musk tokenized Mars, how much ETH do you think it would cost per square meter?"
        ]

        prompt = random.choice(prompts)
        logger.info(f"Selected prompt: {prompt}")
        tweet = bot.generate_response(prompt)
        logger.info(f"Generated tweet: {tweet}")
        return client.create_tweet(text=tweet).data.get('id')

    except Exception as e:
        logger.error("Error while posting tweet.", exc_info=True)
        return None



def reply_to_latest(bot, client, logger, tweet_id, since_id=None):
    """
    Reply to the latest comment on a specific tweet.
    """
    try:
        bot_user_id = os.getenv("BOT_USER_ID")
        replies = search_replies_to_tweet(client, tweet_id, bot_user_id)
        if not replies:
            logger.info("No new replies found.")
            return since_id

        latest_reply = max(replies, key=lambda x: x.id)
        if since_id and latest_reply.id <= since_id:
            logger.info("No new replies since last check.")
            return since_id

        logger.info(f"Replying to: {latest_reply.text}")
        response = bot.generate_response(latest_reply.text)
        client.create_tweet(text=response, in_reply_to_tweet_id=latest_reply.id)
        return latest_reply.id

    except Exception as e:
        logger.error("Error while replying to the latest tweet.", exc_info=True)
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

    since_id = None
    post_interval = 16 * 60  # 16 minutes in seconds
    reply_interval = 16 * 60

    while True:
        try:
            logger.info("Starting a new bot cycle...")

            # Step 1: Post a tweet or meme
            tweet_id = post_tweet(bot, client, api, logger)
            if tweet_id:
                logger.info(f"Posted tweet with ID: {tweet_id}")
            else:
                logger.error("Tweet posting failed. Skipping to reply step.")

            # Step 2: Wait 16 minutes before replying to a tweet
            logger.info(f"Sleeping for {post_interval // 60} minutes before checking replies...")
            time.sleep(post_interval)

            # Step 3: Respond to a reply on the most recent tweet
            if tweet_id:
                since_id = reply_to_latest(bot, client, logger, tweet_id, since_id)
                logger.info("Finished replying to the latest tweet.")
            else:
                logger.warning("No tweet to check replies for. Skipping reply step.")

            # Step 4: Wait 16 minutes before starting a new cycle
            logger.info(f"Sleeping for {reply_interval // 60} minutes before posting a new tweet...")
            time.sleep(reply_interval)

        except tweepy.errors.TooManyRequests as e:
            logger.error("Rate limit hit. Retrying after rate limit reset...", exc_info=True)
            reset_time = int(e.response.headers.get('x-rate-limit-reset', time.time() + 60))
            sleep_time = reset_time - int(time.time())
            logger.info(f"Sleeping for {sleep_time} seconds until rate limit reset.")
            time.sleep(max(0, sleep_time))  # Ensure no negative sleep time

        except Exception as e:
            logger.error("Error in main loop", exc_info=True)
            logger.info("Retrying after 1 minute due to error...")
            time.sleep(60 * 15)  # Shorter delay on error for retry


if __name__ == "__main__":
    main()
