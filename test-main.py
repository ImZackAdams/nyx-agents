import os
import time
from dotenv import load_dotenv
from bot.bot import PersonalityBot
import logging
import warnings
import random
import re

# Suppress specific warnings
warnings.filterwarnings("ignore", message=".*MatMul8bitLt.*")
warnings.filterwarnings("ignore", message=".*quantization_config.*")
warnings.filterwarnings("ignore", message=".*Unused kwargs.*")

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.ERROR)
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.ERROR)

def main():
    try:
        # Initialize the bot
        model_path = "athena_8bit_model"
        bot = PersonalityBot(model_path=model_path, logger=logging.getLogger(__name__))
    except Exception as e:
        print(f"✨ Error: {str(e)} 💅")
        return

    # Define dating-related prompts
    dating_prompts = [
        "Break down why FOMO is like your ex - keeps coming back but never good for you!",
        "Tell us why panic selling is giving the same energy as drunk texting!",
        "Why trusting random DeFi protocols is like swiping right on every profile!",
        "Tell us why diversification is better than commitment issues!",
        "When GPT understands you better than your dating matches!",
        "Why chart patterns are like dating patterns - they keep repeating!"
    ]

    # Define regular prompts
    regular_prompts = [
        "Spill the tea on why FOMO is your portfolio's worst enemy!",
        "Break down why panic selling never helps your gains!",
        "Share why watching charts 24/7 isn't the move!",
        "Explain why blockchain is simpler than everyone thinks!",
        "Break down why smart contracts are the future!",
        "When your AI model serves better predictions than the experts!",
        "Spill why your seed phrase is your most precious possession!",
        "Why trusting unaudited protocols is playing with fire!",
        "Share why clicking random links is the fastest way to get rekt!",
        "Break down why sky-high APY is usually a red flag!",
        "Tell us why diversification is the ultimate power move!",
        "When your portfolio strategy actually makes sense!",
        "Your neural network is giving genius vibes!",
        "Share why AI models are revolutionizing trading!",
        "Break down why machine learning changes everything!",
        "Explain why market analysis needs both tech and fundamentals!",
        "Why technical indicators are your best friends in volatility!",
        "Break down why your trading strategy needs constant updates!",
        "Tell us why crypto Twitter has the best alpha!",
        "Share why Web3 communities are changing the game!",
        "Why NFTs are more than just expensive JPEGs!",
        "Break down why DYOR is non-negotiable!",
        "Why wallet security should be your top priority!",
        "Share why paper hands never make it in crypto!"
    ]

    # Fallback responses for invalid or failed tweets
    fallbacks = [
        "Crypto markets never sleep, and neither should your strategies! 💅 #CryptoLife",
        "DYOR and don't let FOMO get you—research is key to success! ✨ #CryptoWisdom",
        "Diversification is the spice of life, even in the crypto world! 🌟 #CryptoInvesting",
        "Don't let panic sell-offs drain your gains. Stay calm and HODL! 🚀 #CryptoTips",
        "Your seed phrase is sacred—treat it like your most prized possession! 🔐 #CryptoSecurity",
        "In the volatile crypto world, patience and research are your best allies! 🌟 #InvestSmart",
        "The only trend worth following is the one backed by data and fundamentals! 📊 #CryptoAdvice",
        "Avoid scams by sticking with verified platforms—protect your portfolio! 🛡️ #CryptoSafety",
        "Every bull run starts with believers. Stay informed, stay strong! 🐂 #CryptoMotivation",
        "FOMO is temporary, but bad investments last forever. Think before you leap! 🤔 #CryptoMindset",
        "Your wallet's security is your responsibility—never share your private keys! 🔓 #CryptoTips",
        "A true investor sees beyond the hype. Analyze the fundamentals, always! ✨ #InvestWisely",
        "Panic selling leads to regret. Keep calm and trust your strategy! 🚀 #HODL",
        "Good research is better than lucky guesses. Build your edge in the market! 💡 #CryptoWisdom",
        "The key to success? Balance risk and reward—don't go all in blindly! ⚖️ #CryptoInvesting"
    ]

        # Function to clean and format the generated tweet
    def clean_tweet(tweet: str) -> str:
        """Cleans and formats the generated tweet for consistent spacing and readability."""
        # Normalize whitespace
        tweet = ' '.join(tweet.split())

        # Fix punctuation spacing
        tweet = re.sub(r'\s+([.,!?])', r'\1', tweet)  # No space before punctuation
        tweet = re.sub(r'([.,!?])\s+', r'\1 ', tweet)  # Space after punctuation

        # Ensure proper capitalization
        tweet = re.sub(r"(?<!\w)(dont|wont|im|ive|its|lets|youre|whats|cant|ill|id)(?!\w)", 
                    lambda m: m.group(1).capitalize(), tweet, flags=re.IGNORECASE)

        # Reduce repeated punctuation
        tweet = re.sub(r'([!?.]){2,}', r'\1', tweet)  # Limit to one punctuation mark

        # Add space before emojis if missing
        tweet = re.sub(r'(\w)([💅✨👏🌟🚀💎🔓🎨⚡️🔧])', r'\1 \2', tweet)

        # Ensure space before hashtags
        tweet = re.sub(r'(?<!\s)([#@])', r' \1', tweet)

        # Limit hashtags to two and ensure proper spacing
        if tweet.count('#') > 2:
            hashtags = re.findall(r'#\w+', tweet)
            main_text = re.sub(r'#\w+', '', tweet).strip()
            tweet = f"{main_text} {' '.join(hashtags[:2])}"

        # Ensure ending punctuation
        if not tweet.endswith(('.', '!', '?')):
            tweet += '!'

        return tweet.strip()


    # Function to generate a tweet from a prompt
    def generate_tweet(prompt):
        try:
            output = bot.generate_response(prompt)
            tweet = output.replace('\n', ' ').strip()
            if len(tweet) < 50 or len(tweet) > 280 or "Tea's brewing" in tweet:
                return random.choice(fallbacks)
            return clean_tweet(tweet)
        except Exception as e:
            return random.choice(fallbacks)

    try:
        # Process all dating prompts
        for prompt in dating_prompts:
            tweet = generate_tweet(prompt)
            print(f"\n{tweet}")

        # Process all regular prompts
        for prompt in regular_prompts:
            tweet = generate_tweet(prompt)
            print(f"\n{tweet}")

    except KeyboardInterrupt:
        print("\n✨ Bye! 💅")

if __name__ == "__main__":
    main()
