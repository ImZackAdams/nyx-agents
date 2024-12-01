import os
import time
from dotenv import load_dotenv
from bot.bot import PersonalityBot
import logging

# Load environment variables
load_dotenv()


def validate_env_variables():
    """Ensure required environment variables are set."""
    required_vars = ["BOT_USER_ID"]
    for var in required_vars:
        if not os.getenv(var):
            raise EnvironmentError(f"Missing required environment variable: {var}")


def post_simulated_output(bot, prompts, current_index):
    """Generate and return a simplified output for a given prompt."""
    try:
        prompt = prompts[current_index % len(prompts)]
        print(f"Using prompt: {prompt}")  # Debugging: Display the prompt
        generated_output = bot.generate_response(prompt)

        if len(generated_output.strip()) < 20:
            generated_output = "Hmm, it seems I'm having trouble. Care to try a different angle?"

        # Debugging: Log the raw output for inspection
        logging.getLogger(__name__).info(f"Generated raw output: {generated_output}")

        # Print only the response
        print("")
        print(generated_output)
        print("")
    except Exception as e:
        print(f"Error generating output: {e}")


def main():
    try:
        validate_env_variables()
        model_path = "athena_8bit_model"
        bot = PersonalityBot(model_path=model_path, logger=logging.getLogger(__name__))

    except Exception as e:
        print(f"Initialization error: {e}")
        return

    prompts = [
        "Make a post about Crypto. Be hilarious, educational, and engage user replies.",
        "Make a post about Tech. Be hilarious, educational, and engage user replies.",
        "Make a post about AI. Be hilarious, educational, and engage user replies.",
        "Make a post about NFTs. Be hilarious, educational, and engage user replies.",
        "Make a post about Web3. Be hilarious, educational, and engage user replies.",
        "Make a post about Blockchain. Be hilarious, educational, and engage user replies.",
        "Make a post about Finance. Be hilarious, educational, and engage user replies.",
        "Make a post about Computer Programming. Be hilarious, educational, and engage user replies.",
        "Make a joke about being an AI.",
        "Make a post about Cybersecurity. Be hilarious, educational, and engage user replies.",
        "Make a joke comparing your dating life to blockchain.",
    ]

    post_interval = 10  # 10 seconds between posts
    current_index = 0

    try:
        while True:
            post_simulated_output(bot, prompts, current_index)
            current_index += 1
            time.sleep(post_interval)

    except KeyboardInterrupt:
        print("\nExiting cleanly.")


if __name__ == "__main__":
    main()
