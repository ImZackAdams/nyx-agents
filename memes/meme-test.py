import tweepy
import os
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def post_image_with_tweet(client, api, tweet_text, image_path):
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
        print(f"Image uploaded successfully: Media ID {media.media_id}")

        # Post the tweet with the image using the Client
        client.create_tweet(text=tweet_text, media_ids=[media.media_id])
        print("Tweet posted successfully!")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Set up Tweepy Client and API
    client = tweepy.Client(
        consumer_key=os.getenv('API_KEY'),
        consumer_secret=os.getenv('API_SECRET'),
        access_token=os.getenv('ACCESS_TOKEN'),
        access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
    )

    auth = tweepy.OAuth1UserHandler(
        consumer_key=os.getenv('API_KEY'),
        consumer_secret=os.getenv('API_SECRET'),
        access_token=os.getenv('ACCESS_TOKEN'),
        access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
    )
    api = tweepy.API(auth)

    # Get all image files in the current directory
    supported_formats = ('.jpg', '.jpeg', '.png', '.gif')
    images = [file for file in os.listdir('.') if file.lower().endswith(supported_formats)]

    if not images:
        print("No images found in the current directory.")
    else:
        # Select a random image
        image_path = random.choice(images)
        tweet_text = "Check out this meme! 🤣 #Tetherball"

        # Call the function to post the tweet
        post_image_with_tweet(client, api, tweet_text, image_path)
