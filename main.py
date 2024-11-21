import os
from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logging
from bot.twitter_client import setup_twitter_client, post_to_twitter

load_dotenv()

def main():
    """Main function to interact with the bot."""
    logger = setup_logging()
    logger.info("Starting Athena...")

    bot = PersonalityBot(model_path="./fine_tuned_personality_bot/", logger=logger)
    client = setup_twitter_client()

    print("Enter prompts (type 'quit' to exit):")
    while True:
        prompt = input("Your prompt: ").strip()
        if prompt.lower() == "quit":
            print("Exiting... Goodbye!")
            break

        try:
            # Generate response
            response = bot.generate_response(prompt)
            print("\nGenerated response:")
            print(response)

            # Ask if user wants to post to Twitter
            tweet_decision = input("\nPost to Twitter? (yes/no): ").strip().lower()
            if tweet_decision == "yes":
                post_to_twitter(response, client, logger)
                print("Tweet posted successfully!")
            elif tweet_decision == "no":
                print("Tweet not posted.")
            else:
                print("Invalid input. Skipping tweet.")

        except Exception as e:
            logger.error(f"Error: {str(e)}")
            print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
