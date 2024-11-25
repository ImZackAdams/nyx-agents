import tweepy
import os
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
        image_path: The local path to the image (JPG).clear
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

    # Define the tweet text and image path
    tweet_text = "Check out this meme! 🤣 #SignMeme #TwitterBot"
    image_path = "signmeme.jpeg"  # File name of your image

    # Call the function to post the tweet
    post_image_with_tweet(client, api, tweet_text, image_path)
