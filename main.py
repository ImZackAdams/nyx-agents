import os
import time
import random
from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logger
from bot.twitter_client import setup_twitter_client, search_replies_to_tweet, post_image_with_tweet
import logging
import tweepy
import warnings
import re

# Suppress specific warnings
warnings.filterwarnings("ignore", message=".*MatMul8bitLt.*")
warnings.filterwarnings("ignore", message=".*quantization_config.*")
warnings.filterwarnings("ignore", message=".*Unused kwargs.*")

# Load environment variables
load_dotenv()

def validate_env_variables(logger):
    """Ensure required environment variables are set."""
    required_vars = ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET", "BOT_USER_ID"]
    for var in required_vars:
        if not os.getenv(var):
            logger.error(f"Environment variable {var} is not set.")
            raise EnvironmentError(f"Missing required environment variable: {var}")

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

def get_prompts():
    """Returns all available prompts organized by category."""
    return {
        'dating_prompts': [
            "Break down why FOMO is like your ex - keeps coming back but never good for you!",
            "Tell us why panic selling is giving the same energy as drunk texting!",
            "Why trusting random DeFi protocols is like swiping right on every profile!",
            "Tell us why diversification is better than commitment issues!",
            "When GPT understands you better than your dating matches!",
            "Why chart patterns are like dating patterns - they keep repeating!"
        ],
        'crypto_prompts': [
            "Spill the tea on why FOMO is your portfolio's worst enemy!",
            "Break down why panic selling never helps your gains!",
            "Explain why blockchain is simpler than everyone thinks!",
            "What's the one piece of crypto advice you wish you had when you started?",
            "Which is more important in crypto investing: luck or strategy?",
            "If Bitcoin didn't exist, what would the crypto world look like today?",
            "Explain blockchain to a 5-year-old in one sentence.",
            "What's the biggest misconception about NFTs?",
            "What's your go-to method for staying calm during market crashes?"
        ],
        'ai_prompts': [
            "Why does GPT always sound smarter than me? Because it's trained on the internet and not my 2 AM thoughts! 🤖✨",
            "AI models predicting your every move? Relax, they're just better at pattern recognition than your ex. 😏 #AIsass",
            "Training AI is like raising a child: expensive, time-consuming, and occasionally embarrassing. 💻💅",
            "AI models are like toddlers: They repeat everything they hear and sometimes embarrass you in public! 🍼🤖",
            "Neural networks are cool, but have you tried not overfitting your expectations? 🌟😂",
            "Machine learning: Turning your GPU into a glorified heater since 2010. 🔥💻",
            "AI might take over the world, but first, it needs to stop hallucinating answers to simple questions. 🙃🤖"
        ],
        'finance_prompts': [
            "Budgeting tip: Don't put your entire paycheck in Dogecoin.",
            "Why are financial planners the human equivalent of risk management systems?",
            "Retirement plans are like altcoins: they take forever to mature.",
            "Index funds vs. day trading: Which matches your personality?",
            "If investing were easy, Warren Buffet wouldn't be special."
        ],
        'jokes_and_fun_prompts': [
            "Neural networks are just glorified spreadsheets with attitude. Discuss. 😎✨",
            "If crypto coins were zodiac signs, which one would be Gemini?",
            "What's the dumbest way you've lost money in crypto? (No judgment… maybe).",
            "If Satoshi Nakamoto is out there, do you think they regret inventing FOMO? 🤔✨",
            "Blockchain explained: It's like a spreadsheet, but make it spicy. 🌶️💻",
            "The best thing about NFTs? They're JPEGs with a personality disorder. 💅🎨"
        ]
    }

def post_tweet(bot, client, api, logger):
    """Posts either a text tweet or a random meme with an optional caption."""
    logger.info("Starting the post_tweet process...")

    try:
        # Handle meme posting (10% chance)
        if random.random() < 0.1:
            memes_folder = os.path.join(os.getcwd(), 'memes')
            supported_formats = ('.jpg', '.jpeg', '.png', '.gif')

            if not os.path.exists(memes_folder):
                logger.error(f"'memes' folder does not exist at {memes_folder}.")
                return None

            images = [f for f in os.listdir(memes_folder) if f.lower().endswith(supported_formats)]
            if images:
                image_path = os.path.join(memes_folder, random.choice(images))
                
                meme_captions = [
                    "This meme? Pure gold. 🪙✨ #Tetherballcoin",
                    "Some things you just can't unsee. 😂 #CryptoHumor",
                    "Hodlers will understand. 💎🙌 #Tetherballcoin",
                    "Because laughter is the best investment. 😂📈 #CryptoMemes",
                    "Meme game strong, just like our coin. 🚀🔥 #Tetherballcoin"
                ]

                caption = random.choice(meme_captions)
                logger.info(f"Selected meme caption: {caption}")
                return post_image_with_tweet(client, api, caption, image_path, logger)

        # Text tweet generation
        all_prompts = []
        for category_prompts in get_prompts().values():
            all_prompts.extend(category_prompts)

        # Fallback responses for when generation fails
        fallbacks = [
            "Crypto markets never sleep, and neither should your strategies! 💅 #CryptoLife",
            "DYOR and don't let FOMO get you—research is key to success! ✨ #CryptoWisdom",
            "Diversification is the spice of life, even in the crypto world! 🌟 #CryptoInvesting",
            "Don't let panic sell-offs drain your gains. Stay calm and HODL! 🚀 #CryptoTips",
            "Your seed phrase is sacred—treat it like your most prized possession! 🔐 #CryptoSecurity"
        ]

        try:
            prompt = random.choice(all_prompts)
            logger.info(f"Selected prompt: {prompt}")
            tweet = bot.generate_response(prompt)
            
            if len(tweet) < 50 or len(tweet) > 280 or "Tea's brewing" in tweet:
                tweet = random.choice(fallbacks)
            
            tweet = clean_tweet(tweet)
            logger.info(f"Generated tweet: {tweet}")
            return client.create_tweet(text=tweet).data.get('id')

        except Exception as e:
            logger.error(f"Error generating tweet: {str(e)}")
            tweet = random.choice(fallbacks)
            return client.create_tweet(text=tweet).data.get('id')

    except Exception as e:
        logger.error("Error while posting tweet.", exc_info=True)
        return None

# [Rest of the code remains the same: reply_to_last_three and main functions]
def reply_to_last_three(bot, client, logger, tweet_id, since_id=None):
    """Reply to the last three comments on a specific tweet."""
    try:
        bot_user_id = os.getenv("BOT_USER_ID")
        replies = search_replies_to_tweet(client, tweet_id, bot_user_id)
        if not replies:
            logger.info("No new replies found.")
            return since_id

        sorted_replies = sorted(replies, key=lambda x: x.id)
        new_replies = [reply for reply in sorted_replies if not since_id or reply.id > since_id]
        latest_replies = new_replies[-3:] if new_replies else []
        
        if not latest_replies:
            logger.info("No new replies since last check.")
            return since_id

        for reply in latest_replies:
            logger.info(f"Replying to: {reply.text}")
            response = bot.generate_response(reply.text)
            response = clean_tweet(response)  # Clean the reply tweet as well
            client.create_tweet(text=response, in_reply_to_tweet_id=reply.id)
        
        return latest_replies[-2].id if latest_replies else since_id

    except Exception as e:
        logger.error("Error while replying to the tweets.", exc_info=True)
        return since_id

def main():
    logger = setup_logger("athena")
    logger.info("Starting the bot...")

    try:
        validate_env_variables(logger)
        bot = PersonalityBot(model_path="athena_8bit_model", logger=logger)
        client = setup_twitter_client()
        api = tweepy.API(tweepy.OAuth1UserHandler(
            consumer_key=os.getenv('API_KEY'),
            consumer_secret=os.getenv('API_SECRET'),
            access_token=os.getenv('ACCESS_TOKEN'),
            access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
        ))

    except Exception as e:
        logger.error("Initialization error", exc_info=True)
        return

    # Initialize timing parameters
    since_id = None
    reply_check_interval = 60 * 10  # Check replies every 10 minutes
    reply_cycles = 3  # Number of reply checking cycles before new tweet
    post_cooldown = 60 * 5  # 5 minutes between posts

    # Add rate limit tracking
    rate_limit_hits = 0
    max_rate_limit_hits = 3
    daily_post_count = 0
    last_reset_time = time.time()
    daily_post_limit = 100

    while True:
        try:
            current_time = time.time()
            if current_time - last_reset_time >= 24 * 60 * 60:
                daily_post_count = 0
                rate_limit_hits = 0
                last_reset_time = current_time
                logger.info("Reset daily counters")

            logger.info(f"Current daily post count: {daily_post_count}/{daily_post_limit}")
            logger.info("Starting a new bot cycle...")

            if daily_post_count >= daily_post_limit:
                logger.warning("Daily post limit reached, waiting for reset...")
                time.sleep(60 * 30)
                continue

            tweet_id = post_tweet(bot, client, api, logger)
            if tweet_id:
                daily_post_count += 1
                logger.info(f"Posted tweet with ID: {tweet_id}")
                
                for cycle in range(reply_cycles):
                    if daily_post_count >= daily_post_limit:
                        logger.warning("Daily post limit reached during reply cycle")
                        break

                    logger.info(f"Starting reply check cycle {cycle + 1}/{reply_cycles}")
                    since_id = reply_to_last_three(bot, client, logger, tweet_id, since_id)
                    logger.info(f"Completed reply cycle {cycle + 1}")
                    
                    if cycle < reply_cycles - 1:
                        logger.info(f"Sleeping for {reply_check_interval // 60} minutes...")
                        time.sleep(reply_check_interval)
            else:
                logger.error("Tweet posting failed. Waiting before retry...")
                time.sleep(post_cooldown)
                continue

            logger.info(f"Cooling down for {post_cooldown // 60} minutes...")
            time.sleep(post_cooldown)

        except tweepy.errors.TooManyRequests as e:
            rate_limit_hits += 1
            logger.error(f"Rate limit hit #{rate_limit_hits}...")
            
            if rate_limit_hits >= max_rate_limit_hits:
                logger.warning("Multiple rate limits hit. Taking a longer break...")
                time.sleep(60 * 60 * 2)  # 2 hour break
                rate_limit_hits = 0
                continue
                
            reset_time = int(e.response.headers.get('x-rate-limit-reset', time.time() + 60))
            sleep_time = reset_time - int(time.time())
            logger.info(f"Sleeping for {sleep_time} seconds until rate limit reset.")
            time.sleep(max(0, sleep_time))

        except Exception as e:
            logger.error("Error in main loop", exc_info=True)
            logger.info("Retrying after 15 minutes due to error...")
            time.sleep(60 * 15)

if __name__ == "__main__":
    main()