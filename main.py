from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logging
from bot.twitter_client import setup_twitter_client, post_to_twitter

load_dotenv()

def main():
    logger = setup_logging()
    logger.info("Starting PersonalityBot...")
    
    bot = PersonalityBot(model_path="./fine_tuned_personality_bot/", logger=logger)

    client = setup_twitter_client()
    
    print("Enter prompts (type 'quit' to exit):")
    while True:
        prompt = input("Your prompt: ").strip()
        if prompt.lower() == "quit":
            break
        
        response = bot.generate_response(prompt)
        print(f"Response: {response}")
        
        if input("Post to Twitter? (yes/no): ").strip().lower() == "yes":
            post_to_twitter(response, client, logger)

if __name__ == "__main__":
    main()
