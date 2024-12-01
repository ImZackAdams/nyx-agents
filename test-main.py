import os
import time
from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logging
import logging

# Load environment variables
load_dotenv()


def validate_env_variables(logger):
    """Ensure required environment variables are set."""
    required_vars = ["BOT_USER_ID"]
    for var in required_vars:
        if not os.getenv(var):
            logger.error(f"Environment variable {var} is not set.")
            raise EnvironmentError(f"Missing required environment variable: {var}")


def post_simulated_output(bot, prompts, current_index):
    """Generate and return a simulated output for a given prompt."""
    try:
        prompt = prompts[current_index % len(prompts)]
        generated_output = bot.generate_response(prompt)

        if len(generated_output.strip()) < 20:
            generated_output = "Hmm, it seems I'm having trouble. Care to try a different angle?"

        # Simplified output
        print(f"\nPrompt: {prompt}\nResponse: {generated_output}\n")
        return generated_output

    except Exception as e:
        print(f"Error generating output: {e}")
        return None


def main():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    print("\n=== Starting Bot Simulation ===\n")

    try:
        validate_env_variables(logger)
        model_path = "athena_8bit_model"
        bot = PersonalityBot(model_path=model_path, logger=logger)

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
        print("\n=== Simulation Interrupted ===\nExiting cleanly.")


if __name__ == "__main__":
    main()
