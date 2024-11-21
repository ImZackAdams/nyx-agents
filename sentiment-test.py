import os
from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logging

load_dotenv()


def run_tests(bot, logger, test_cases):
    """Run a series of test cases against the bot."""
    logger.info("Starting tests for Athena...")

    results = []

    for i, test_case in enumerate(test_cases, 1):
        prompt = test_case.get("prompt", "").strip()
        expected_sentiment = test_case.get("expected_sentiment", None)
        description = test_case.get("description", "No description provided")

        logger.info(f"Running test case {i}: {description}")
        print(f"\nTest Case {i}: {description}")
        print(f"Prompt: {prompt}")

        try:
            # Generate response
            response = bot.generate_response(prompt)
            print(f"\nGenerated Response:\n{response}")

            # Analyze results (e.g., check length, tone, etc.)
            sentiment = bot._analyze_sentiment(response)
            print(f"Predicted Sentiment: {sentiment}")

            # Log test results
            result = {
                "test_case": i,
                "description": description,
                "prompt": prompt,
                "response": response,
                "predicted_sentiment": sentiment,
                "expected_sentiment": expected_sentiment,
                "passed": expected_sentiment is None or sentiment == expected_sentiment,
            }
            results.append(result)

        except Exception as e:
            logger.error(f"Error during test case {i}: {str(e)}")
            print(f"An error occurred: {str(e)}")

            results.append({
                "test_case": i,
                "description": description,
                "prompt": prompt,
                "response": "Error occurred",
                "predicted_sentiment": "Error",
                "expected_sentiment": expected_sentiment,
                "passed": False,
            })

    return results


def display_results(results):
    """Display the test results."""
    print("\nTest Results Summary:")
    for result in results:
        print(f"Test Case {result['test_case']}: {result['description']}")
        print(f"  Prompt: {result['prompt']}")
        print(f"  Response: {result['response']}")
        print(f"  Predicted Sentiment: {result['predicted_sentiment']}")
        print(f"  Expected Sentiment: {result['expected_sentiment']}")
        print(f"  Passed: {'Yes' if result['passed'] else 'No'}\n")


def main():
    """Main function to run bot tests."""
    logger = setup_logging()
    logger.info("Initializing Athena for testing...")

    bot = PersonalityBot(model_path="./fine_tuned_personality_bot/", logger=logger)

    # Define a variety of test cases
# Define 10 diverse test cases
    test_cases = [
        {
            "description": "Positive sentiment, simple prompt",
            "prompt": "Bitcoin is up 10% today! Should I buy?",
            "expected_sentiment": "positive",
        },
        {
            "description": "Negative sentiment, market crash",
            "prompt": "Crypto markets are crashing! What should I do?",
            "expected_sentiment": "negative",
        },
        {
            "description": "Neutral sentiment, technical question",
            "prompt": "What is the purpose of Layer 2 solutions?",
            "expected_sentiment": "neutral",
        },
        {
            "description": "Funny take on NFTs",
            "prompt": "Why are NFTs so overpriced?",
            "expected_sentiment": None,
        },
        {
            "description": "DeFi explanation, sarcastic tone expected",
            "prompt": "Explain staking but make it funny.",
            "expected_sentiment": None,
        },
        {
            "description": "General market trends with humor",
            "prompt": "Tell me something about crypto market trends.",
            "expected_sentiment": "neutral",
        },
        {
            "description": "Bullish sentiment on Ethereum",
            "prompt": "Ethereum is performing exceptionally well. Thoughts?",
            "expected_sentiment": "positive",
        },
        {
            "description": "Bearish sentiment about meme coins",
            "prompt": "Meme coins are just a fad, aren't they?",
            "expected_sentiment": "negative",
        },
        {
            "description": "Community and culture discussion",
            "prompt": "Why do DAOs matter in Web3?",
            "expected_sentiment": "neutral",
        },
        {
            "description": "Explaining tokenomics humorously",
            "prompt": "Explain tokenomics but make it funny.",
            "expected_sentiment": None,
        },
    ]

    # Run tests
    results = run_tests(bot, logger, test_cases)

    # Display results
    display_results(results)


if __name__ == "__main__":
    main()
