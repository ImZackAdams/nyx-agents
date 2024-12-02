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

# Twitter Bot Prompts

    dating_prompts = [
        "Break down why FOMO is like your ex - keeps coming back but never good for you!",
        "Tell us why panic selling is giving the same energy as drunk texting!",
        "Why trusting random DeFi protocols is like swiping right on every profile!",
        "Tell us why diversification is better than commitment issues!",
        "When GPT understands you better than your dating matches!",
        "Why chart patterns are like dating patterns - they keep repeating!",
    ]

    crypto_prompts = [
        "Spill the tea on why FOMO is your portfolio's worst enemy!",
        "Break down why panic selling never helps your gains!",
        "Explain why blockchain is simpler than everyone thinks!",
        "What’s the one piece of crypto advice you wish you had when you started?",
        "Which is more important in crypto investing: luck or strategy?",
        "If Bitcoin didn’t exist, what would the crypto world look like today?",
        "Explain blockchain to a 5-year-old in one sentence.",
        "What’s the biggest misconception about NFTs?",
        "What’s your go-to method for staying calm during market crashes?",
    ]

    ai_prompts = [
        "Why does GPT always sound smarter than me? Because it's trained on the internet and not my 2 AM thoughts! 🤖✨",
        "AI models predicting your every move? Relax, they're just better at pattern recognition than your ex. 😏 #AIsass",
        "Training AI is like raising a child: expensive, time-consuming, and occasionally embarrassing. 💻💅",
        "AI models are like toddlers: They repeat everything they hear and sometimes embarrass you in public! 🍼🤖",
        "Neural networks are cool, but have you tried not overfitting your expectations? 🌟😂",
        "Why did the AI model break up with its training dataset? Too many strings attached. 💔🤖",
        "Machine learning: Turning your GPU into a glorified heater since 2010. 🔥💻",
        "AI might take over the world, but first, it needs to stop hallucinating answers to simple questions. 🙃🤖",
        "Why is AI like a bad Tinder date? Promises the world, delivers a weird conversation. 💅✨",
    ]

    motivational_prompts = [
        "Crypto is more than money; it’s a movement. What’s your role in it?",
        "Every bear market creates opportunities. What are you building during this one?",
        "The first step in crypto is the hardest, but it’s worth it. What was yours?",
        "The best time to plant a tree was 10 years ago. The second best time is now. What’s your next crypto move?",
        "HODLing isn’t easy, but neither is success. Stay strong!",
        "Crypto teaches patience, discipline, and risk management. What has it taught you?",
        "Remember: Innovation takes time. Stay focused on the long-term vision!",
        "What inspires you to keep building, even during market downturns?",
        "Crypto is rewriting the rules of finance. What’s your contribution?",
    ]

    jokes_and_fun_prompts = [
        "Neural networks are just glorified spreadsheets with attitude. Discuss. 😎✨",
        "If crypto coins were zodiac signs, which one would be Gemini?",
        "What’s the dumbest way you’ve lost money in crypto? (No judgment… maybe).",
        "AI models are like toddlers. You feed them enough data, and they spit out weird stuff. 🍼🤖",
        "If Satoshi Nakamoto is out there, do you think they regret inventing FOMO? 🤔✨",
        "Blockchain explained: It’s like a spreadsheet, but make it spicy. 🌶️💻",
        "The best thing about NFTs? They’re JPEGs with a personality disorder. 💅🎨",
        "Crypto trading: the only place where 'buy high, sell low' happens daily. 💸😂",
        "If AI ran a coffee shop, every latte would be optimized for ROI. ☕🤖",
    ]

    timeless_prompts = [
        "What’s your dream use case for blockchain?",
        "If AI and crypto merged, what would the ultimate innovation be?",
        "Explain DeFi to someone who still writes checks. 📝✨",
        "What’s your worst trading habit you wish you could break?",
        "If Satoshi had a Twitter account, what would their first tweet be?",
        "What’s the next big thing in crypto no one’s talking about yet?",
        "What do you think the world will look like if crypto replaces fiat?",
        "What’s one lesson from traditional finance you’d bring to Web3?",
        "What’s the craziest blockchain idea you’ve ever heard?",
    ]

    sagittarius_prompts = [
        "Sagittarius energy is all about aiming high, just like that crypto portfolio you’re dreaming of! 🏹✨ What’s your next big goal?",
        "Feeling restless, Sagittarius? Blame your ruling planet Jupiter—it’s all about expansion, adventure, and maybe a little FOMO. 🌍🚀",
        "Sagittarius vibes today: Honest, curious, and maybe a bit too blunt. What truth bomb are you dropping this week? 🎯💬",
        "A Sagittarius knows no limits—just like blockchain tech. Infinite potential, anyone? 💻🏹",
        "Sagittarius season is here! Time to embrace adventure, big ideas, and maybe a little risk-taking. What’s your boldest move? 🌟🔥",
    ]

    # New Categories
    trending_topics_prompts = [
        "AI is getting smarter, but can it write an apology as good as ChatGPT?",
        "What’s the most exciting tech breakthrough you’ve heard about this week?",
        "If crypto is the future, why are we all still broke? 🤑",
        "Tech layoffs are everywhere, but innovation is thriving. Discuss.",
        "Who else is waiting for the AI that can do taxes perfectly?"
    ]

    finance_prompts = [
        "Budgeting tip: Don’t put your entire paycheck in Dogecoin.",
        "Why are financial planners the human equivalent of risk management systems?",
        "Retirement plans are like altcoins: they take forever to mature.",
        "Index funds vs. day trading: Which matches your personality?",
        "If investing were easy, Warren Buffet wouldn’t be special."
    ]

    productivity_prompts = [
        "What’s your favorite app for staying productive?",
        "Productivity hacks are just life hacks for the perpetually tired.",
        "Why is managing your schedule harder than debugging a JavaScript error?",
        "AI tools are great, but nothing beats a good nap.",
        "Why does every productivity guru assume we all wake up at 5 AM?"
    ]

    # Combine all prompts
    all_prompts = (
        dating_prompts
        + crypto_prompts
        + ai_prompts
        + motivational_prompts
        + jokes_and_fun_prompts
        + timeless_prompts
        + sagittarius_prompts
        + trending_topics_prompts
        + finance_prompts
        + productivity_prompts
    )


    # Fallback responses for invalid or failed tweets
    fallbacks = [
        "Crypto markets never sleep, and neither should your strategies! 💅 #CryptoLife",
        "DYOR and don't let FOMO get you—research is key to success! ✨ #CryptoWisdom",
        "Diversification is the spice of life, even in the crypto world! 🌟 #CryptoInvesting",
        "Don't let panic sell-offs drain your gains. Stay calm and HODL! 🚀 #CryptoTips",
        "Your seed phrase is sacred—treat it like your most prized possession! 🔐 #CryptoSecurity",
        "Panic selling leads to regret. Keep calm and trust your strategy! 🚀 #HODL",
    ]

    def clean_tweet(tweet: str) -> str:
        """Cleans and formats the generated tweet for consistent spacing and readability."""
        tweet = ' '.join(tweet.split())  # Normalize whitespace
        tweet = re.sub(r'\s+([.,!?])', r'\1', tweet)  # Fix punctuation spacing
        tweet = re.sub(r'([.,!?])\s+', r'\1 ', tweet)  # Space after punctuation
        tweet = re.sub(r"(?<!\w)(dont|wont|im|ive|its|lets|youre|whats|cant|ill|id)(?!\w)", 
                       lambda m: m.group(1).capitalize(), tweet, flags=re.IGNORECASE)
        tweet = re.sub(r'([!?.]){2,}', r'\1', tweet)  # Reduce repeated punctuation
        tweet = re.sub(r'(\w)([💅✨👏🌟🚀💎🔓🎨⚡️🔧])', r'\1 \2', tweet)  # Space before emojis
        tweet = re.sub(r'(?<!\s)([#@])', r' \1', tweet)  # Space before hashtags
        if tweet.count('#') > 2:
            hashtags = re.findall(r'#\w+', tweet)
            main_text = re.sub(r'#\w+', '', tweet).strip()
            tweet = f"{main_text} {' '.join(hashtags[:2])}"
        if not tweet.endswith(('.', '!', '?')):
            tweet += '!'
        return tweet.strip()

    def generate_tweet(prompt):
        try:
            output = bot.generate_response(prompt)
            tweet = output.replace('\n', ' ').strip()
            if len(tweet) < 50 or len(tweet) > 280 or "Tea's brewing" in tweet:
                return random.choice(fallbacks)
            return clean_tweet(tweet)
        except Exception:
            return random.choice(fallbacks)

    try:
        # Generate and print tweets
        for _ in range(10):  # Simulates hourly posting for a day
            prompt = random.choice(all_prompts)
            tweet = generate_tweet(prompt)
            print(f"\n{tweet}")
            time.sleep(2)  # Simulate posting interval

    except KeyboardInterrupt:
        print("\n✨ Bye! 💅")

if __name__ == "__main__":
    main()
