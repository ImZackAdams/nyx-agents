import os
import time
import random
from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logging
from bot.twitter_client import setup_twitter_client, search_replies_to_tweet
import logging
import tweepy

# Load environment variables
load_dotenv()

def post_image_with_tweet(client, api, tweet_text, image_path, logger):
    """
    Post a tweet with an attached image.

    Args:
        client: The authenticated Tweepy client.
        api: The authenticated Tweepy API object for media uploads.
        tweet_text: The text of the tweet.
        image_path: The local path to the image (JPG).
    """
    try:
        # Upload the image using the API
        media = api.media_upload(image_path)
        logger.info(f"Image uploaded successfully: Media ID {media.media_id}")

        # Post the tweet with the image using the Client
        client.create_tweet(text=tweet_text, media_ids=[media.media_id])
        logger.info("Tweet with image posted successfully!")
    except Exception as e:
        logger.error(f"Error posting tweet with image: {str(e)}", exc_info=True)

def post_tweet_job(bot, client, api, logger):
    """Job to post a tweet with text or a random meme."""
    try:
        logger.info("Starting the post_tweet_job...")

        # Decide whether to post a text tweet or a meme
        post_meme = random.choice([True, False])  # 50% chance to post a meme

        if post_meme:
            # Define the memes folder path
            memes_folder = os.path.join(os.getcwd(), 'memes')

            # Check if the memes folder exists
            if not os.path.exists(memes_folder):
                logger.error(f"The 'memes' folder does not exist at {memes_folder}.")
                return None

            # Get all image files in the memes folder
            supported_formats = ('.jpg', '.jpeg', '.png', '.gif')
            images = [file for file in os.listdir(memes_folder) if file.lower().endswith(supported_formats)]

            if not images:
                logger.warning("No images found in the memes folder. Falling back to text tweet.")
            else:
                # Select a random image
                image_path = os.path.join(memes_folder, random.choice(images))
                tweet_text = "Check out this meme! 🤣 #Tetherball"

                # Post the meme
                post_image_with_tweet(client, api, tweet_text, image_path, logger)
                return None

        # Post a regular text tweet
        prompt = input("Enter a prompt for the tweet: ").strip()
        if not prompt:
            logger.warning("Prompt is empty. Skipping tweet.")
            return None

        logger.info(f"Generating a tweet with the provided prompt: {prompt}")
        tweet = bot.generate_response(prompt)
        logger.info(f"Generated tweet: {tweet}")

        response = client.create_tweet(text=tweet)
        tweet_id = response.data['id']
        logger.info(f"Tweet successfully posted with ID: {tweet_id}")
        return tweet_id
    except Exception as e:
        logger.error(f"Error posting tweet: {str(e)}", exc_info=True)
        return None


def reply_to_last_comment(bot, client, logger, since_id=None, tweet_id=None):
    """Replies to the last user who commented on the bot's tweet."""
    try:
        logger.info("Starting reply_to_last_comment...")

        # Fetch the bot's user ID from environment variables
        bot_user_id = os.getenv("BOT_USER_ID")
        if not bot_user_id:
            raise ValueError("BOT_USER_ID is not set in the .env file")

        logger.info(f"BOT_USER_ID: {bot_user_id}")

        if not tweet_id:
            logger.error("No tweet ID provided. Skipping reply task.")
            return since_id

        # Fetch replies to the latest tweet
        logger.info(f"Fetching replies to the tweet with ID {tweet_id}...")
        replies = search_replies_to_tweet(client, tweet_id, bot_user_id)
        if not replies:
            logger.info(f"No replies found for tweet ID: {tweet_id}")
            return since_id

        logger.info(f"Fetched {len(replies)} replies. Sorting to find the most recent reply...")
        latest_reply = sorted(replies, key=lambda x: x.id, reverse=True)[0]

        if since_id and latest_reply.id <= since_id:
            logger.info(f"No new replies to respond to. Since ID: {since_id}")
            return since_id

        logger.info(f"Latest reply ID: {latest_reply.id}, Reply text: {latest_reply.text}")
        reply_text = latest_reply.text
        reply_id = latest_reply.id

        # Generate a reply
        logger.info(f"Generating a response to the reply: {reply_text}")
        response = bot.generate_response(reply_text)
        logger.info(f"Generated response: {response}")

        # Post the reply
        logger.info(f"Posting reply to tweet ID {reply_id}...")
        client.create_tweet(text=response, in_reply_to_tweet_id=reply_id)
        logger.info(f"Replied to tweet ID {reply_id} successfully!")

        return latest_reply.id
    except Exception as e:
        logger.error(f"Error replying to last comment: {str(e)}", exc_info=True)
        return since_id

def main():
    logger = setup_logging()
    logger.info("Starting the bot...")
    
    # Initialize the bot and Twitter client
    try:
        bot = PersonalityBot(model_path="./fine_tuned_personality_bot/", logger=logger)
        client = setup_twitter_client()

        auth = tweepy.OAuth1UserHandler(
            consumer_key=os.getenv('API_KEY'),
            consumer_secret=os.getenv('API_SECRET'),
            access_token=os.getenv('ACCESS_TOKEN'),
            access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
        )
        api = tweepy.API(auth)
    except Exception as e:
        logger.error("Failed to initialize the bot or Twitter client.", exc_info=True)
        return

    # Track the latest reply ID and tweet ID
    since_id = None
    tweet_id = None

    while True:
        try:
            # Step 1: Post a tweet or meme
            logger.info("Posting a new tweet or meme...")
            tweet_id = post_tweet_job(bot, client, api, logger)
            if not tweet_id:
                logger.warning("No tweet posted. Skipping reply task.")
                continue

            logger.info("Tweet posting completed.")

            # Step 2: Wait 10 seconds to allow indexing
            logger.info("Waiting 10 seconds to allow the tweet to be indexed...")
            time.sleep(10)

            # Step 3: Wait 16 minutes before checking for replies
            logger.info("Waiting 16 minutes before checking for replies...")
            time.sleep(16 * 60)

            # Step 4: Respond to the most recent reply
            logger.info("Checking for replies to the latest tweet...")
            since_id = reply_to_last_comment(bot, client, logger, since_id, tweet_id)
            logger.info("Reply task completed.")

            # Step 5: Wait another 16 minutes before repeating
            logger.info("Waiting 16 minutes before starting the next iteration...")
            time.sleep(16 * 60)

        except Exception as e:
            logger.error(f"An error occurred in the main loop: {str(e)}", exc_info=True)

        # Short delay before starting the next cycle (for debugging purposes)
        time.sleep(1)

if __name__ == "__main__":
    main()
