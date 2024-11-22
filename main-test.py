import os
from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logging

load_dotenv()

def main():
    """Main function to test the bot with example prompts."""
    logger = setup_logging()
    logger.info("Starting Athena...")




    # Initialize the bot
    bot = PersonalityBot(model_path="./fine_tuned_personality_bot/", logger=logger)

    # List of example prompts
    example_prompts = [
        "What's your take on Bitcoin as digital gold?",
        "Explain staking in the context of DeFi but make it funny.",
        "What do you think about NFTs and their future?",
        "Give a market analysis of Solana's price trend.",
        "How does blockchain scaling impact network performance?",
        "Why is liquidity important in DeFi protocols?",
        "What are DAOs, and why do they matter?",
        "What's your take on Ethereum gas fees?",
        "Are we in a crypto bull run or a bear market?",
        "What is the role of art in the NFT community?"
    ]

    # Generate and print responses for each prompt
    print("\nTesting bot with 10 example prompts:\n")
    for idx, prompt in enumerate(example_prompts, 1):
        try:
            response = bot.generate_response(prompt)
            print(f"{idx}. Prompt: {prompt}")
            print("")
            print(f"   Response: {response}\n")
        except Exception as e:
            logger.error(f"Error generating response for prompt '{prompt}': {str(e)}")
            print(f"Error generating response for prompt '{prompt}': {str(e)}\n")

if __name__ == "__main__":
    main()
