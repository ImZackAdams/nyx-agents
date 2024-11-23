import os
from unittest.mock import MagicMock
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def post_image_with_tweet(client, tweet_text, image_path):
    """
    Post a tweet with an attached image (mocked for testing).

    Args:
        client: The mocked Tweepy client.
        tweet_text: The text of the tweet.
        image_path: The local path to the image (JPG).
    """
    try:
        # Mock the image upload
        media = client.media_upload(image_path)
        print(f"Image uploaded successfully: Media ID {media['media_id']}")

        # Mock the tweet creation
        client.create_tweet(text=tweet_text, media_ids=[media['media_id']])
        print("Tweet posted successfully!")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Create a mock Tweepy client
    client = MagicMock()

    # Mock the media_upload method
    client.media_upload.return_value = {"media_id": "1234567890"}

    # Mock the create_tweet method
    client.create_tweet.return_value = {"id": "987654321", "text": "Test tweet"}

    # Define the tweet text and image path
    tweet_text = "Check out this meme! 🤣 #SignMeme #TwitterBot"
    image_path = "signmeme.jpg"  # File name of your image

    # Call the function to test
    post_image_with_tweet(client, tweet_text, image_path)
