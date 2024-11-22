import os
import tweepy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Authenticate with Twitter API
client = tweepy.Client(
    bearer_token=os.getenv('BEARER_TOKEN'),
    consumer_key=os.getenv('API_KEY'),
    consumer_secret=os.getenv('API_SECRET'),
    access_token=os.getenv('ACCESS_TOKEN'),
    access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
)

# Get the bot's user info
user = client.get_me()
print(f"Bot's User ID: {user.data.id}")
print(f"Bot's Username: {user.data.username}")
