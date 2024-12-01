import os
import time
from dotenv import load_dotenv
from bot.bot import PersonalityBot
import logging
import warnings
import random

warnings.filterwarnings("ignore", message=".*MatMul8bitLt.*")
warnings.filterwarnings("ignore", message=".*quantization_config.*")
warnings.filterwarnings("ignore", message=".*Unused kwargs.*")

load_dotenv()
logging.basicConfig(level=logging.ERROR)
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.ERROR)

def main():
    try:
        model_path = "athena_8bit_model"
        bot = PersonalityBot(model_path=model_path, logger=logging.getLogger(__name__))
    except Exception as e:
        print(f"✨ Error: {str(e)} 💅")
        return

    dating_prompts = [
        "Break down why FOMO is like your ex - keeps coming back but never good for you!",
        "Tell us why panic selling is giving the same energy as drunk texting!",
        "Why trusting random DeFi protocols is like swiping right on every profile!",
        "Tell us why diversification is better than commitment issues!",
        "When GPT understands you better than your dating matches!",
        "Why chart patterns are like dating patterns - they keep repeating!"
    ]

    regular_prompts = [
        # Market & Trading
        "Spill the tea on why FOMO is your portfolio's worst enemy!",
        "Break down why panic selling never helps your gains!",
        "Share why watching charts 24/7 isn't the move!",
        
        # Tech & Innovation
        "Explain why blockchain is simpler than everyone thinks!",
        "Break down why smart contracts are the future!",
        "When your AI model serves better predictions than the experts!",
        
        # Security
        "Spill why your seed phrase is your most precious possession!",
        "Why trusting unaudited protocols is playing with fire!",
        "Share why clicking random links is the fastest way to get rekt!",
        
        # DeFi & Investment
        "Break down why sky-high APY is usually a red flag!",
        "Tell us why diversification is the ultimate power move!",
        "When your portfolio strategy actually makes sense!",
        
        # AI & Tech
        "Your neural network is giving genius vibes!",
        "Share why AI models are revolutionizing trading!",
        "Break down why machine learning changes everything!",
        
        # Market Analysis
        "Explain why market analysis needs both tech and fundamentals!",
        "Why technical indicators are your best friends in volatility!",
        "Break down why your trading strategy needs constant updates!",
        
        # Culture & Community
        "Tell us why crypto Twitter has the best alpha!",
        "Share why Web3 communities are changing the game!",
        "Why NFTs are more than just expensive JPEGs!",
        
        # General Wisdom
        "Break down why DYOR is non-negotiable!",
        "Why wallet security should be your top priority!",
        "Share why paper hands never make it in crypto!"
    ]

    def clean_tweet(tweet: str) -> str:
        tweet = ' '.join(tweet.split())
        tweet = tweet.replace('..', '.').replace('!!', '!').replace('??', '?')
        if tweet.count('#') > 2:
            parts = tweet.split('#')
            tweet = parts[0] + '#' + parts[1] + '#' + parts[2]
        if not tweet[-1] in '.!?':
            tweet += '!'
        return tweet.strip()

    def generate_tweet(prompt):
        try:
            output = bot.generate_response(prompt)
            tweet = output.replace('\n', ' ').strip()
            if len(tweet) < 50 or len(tweet) > 280:
                return generate_tweet(prompt)
            tweet = clean_tweet(tweet)
            return tweet
        except Exception as e:
            return f"✨ Error: {str(e)} 💅"

    try:
        # Generate 24 tweets with ~20% dating references
        for i in range(24):
            # 20% chance of selecting a dating prompt
            if random.random() < 0.2:
                prompt = random.choice(dating_prompts)
            else:
                prompt = random.choice(regular_prompts)
            
            tweet = generate_tweet(prompt)
            print(f"\n{tweet}\n")
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n✨ Bye! 💅")

if __name__ == "__main__":
    main()