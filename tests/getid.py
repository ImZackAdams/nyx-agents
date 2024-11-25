import os
from dotenv import load_dotenv
import tweepy

# Load environment variables
load_dotenv()

def get_bot_user_id():
    api_key = os.getenv('API_KEY')
    api_secret = os.getenv('API_SECRET')
    access_token = os.getenv('ACCESS_TOKEN')
    access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')
    bearer_token = os.getenv('BEARER_TOKEN')

    # Set up Twitter client
    client = tweepy.Client(bearer_token=bearer_token)

    # Replace 'YourBotUsername' with your bot's username (without @)
    bot_username = "Tballbothq"

    # Fetch user info
    try:
        user = client.get_user(username=bot_username)
        print(f"User ID for {bot_username}: {user.data.id}")
        return user.data.id
    except Exception as e:
        print(f"Error fetching user ID: {e}")

if __name__ == "__main__":
    get_bot_user_id()
