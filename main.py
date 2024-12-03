import os
import time
import random
import logging
import tweepy
import warnings
import re
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from bot.bot import PersonalityBot
from bot.utilities import setup_logger
from bot.twitter_client import setup_twitter_client, search_replies_to_tweet, post_image_with_tweet

# Configuration Constants
MAX_TWEET_LENGTH = 280
MIN_TWEET_LENGTH = 50
MAX_GENERATION_ATTEMPTS = 3
REPLY_DELAY_SECONDS = 2
MEME_POSTING_CHANCE = 0.1

# Suppress specific warnings
warnings.filterwarnings("ignore", message=".*MatMul8bitLt.*")
warnings.filterwarnings("ignore", message=".*quantization_config.*")
warnings.filterwarnings("ignore", message=".*Unused kwargs.*")

# Load environment variables
load_dotenv()

class TweetCleaner:
    """Handles tweet text cleaning and formatting."""
    
    @staticmethod
    def clean_tweet(tweet: str) -> str:
        """Cleans and formats the generated tweet for consistent spacing and readability."""
        if not tweet:
            return ""
        
        tweet = ' '.join(tweet.split())  # Normalize whitespace
        tweet = re.sub(r'\s+([.,!?])', r'\1', tweet)  # Fix punctuation spacing
        tweet = re.sub(r'([.,!?])\s+', r'\1 ', tweet)  # Space after punctuation
        tweet = re.sub(r"(?<!\w)(dont|wont|im|ive|its|lets|youre|whats|cant|ill|id)(?!\w)", 
                      lambda m: m.group(1).capitalize(), tweet, flags=re.IGNORECASE)
        tweet = re.sub(r'([!?.]){2,}', r'\1', tweet)  # Reduce repeated punctuation
        tweet = re.sub(r'(\w)([💅✨👏🌟🚀💎🔓🎨⚡️🔧])', r'\1 \2', tweet)  # Space before emojis
        tweet = re.sub(r'(?<!\s)([#@])', r' \1', tweet)  # Space before hashtags
        
        # Limit hashtags to 2
        if tweet.count('#') > 2:
            hashtags = re.findall(r'#\w+', tweet)
            main_text = re.sub(r'#\w+', '', tweet).strip()
            tweet = f"{main_text} {' '.join(hashtags[:2])}"
            
        # Ensure proper ending
        if not tweet.endswith(('.', '!', '?')):
            tweet += '!'
            
        return tweet.strip()

class RateLimitTracker:
    """Tracks and manages rate limit occurrences."""
    
    def __init__(self, window_minutes: int = 15, threshold: int = 3, backoff_hours: int = 3):
        self.rate_limits: List[float] = []
        self.window_minutes = window_minutes
        self.threshold = threshold
        self.backoff_hours = backoff_hours

    def add_rate_limit(self) -> None:
        """Record a new rate limit hit and clean old ones."""
        current_time = time.time()
        self.rate_limits.append(current_time)
        window_start = current_time - (self.window_minutes * 60)
        self.rate_limits = [t for t in self.rate_limits if t > window_start]

    def should_extended_sleep(self) -> bool:
        """Determine if we need an extended sleep period."""
        return len(self.rate_limits) >= self.threshold

    def get_sleep_time(self, reset_time: int) -> int:
        """Calculate appropriate sleep time based on rate limit history."""
        if self.should_extended_sleep():
            self.rate_limits.clear()
            return self.backoff_hours * 60 * 60
        return max(0, reset_time - int(time.time()))

def get_prompts() -> Dict[str, List[str]]:
    """Returns all available prompts organized by category."""
    return {
        'dating_prompts': [
            "FOMO is like your ex—teaches you lessons but always leaves you wanting something better! 🌟",
            "Panic selling? It's like ghosting after a great date—you’re only hurting yourself! 🥂",
            "Trusting random DeFi protocols is like blind dates—sometimes surprising, often thrilling, always a story! 💼💖",
            "Diversification: because keeping your options open is the ultimate power move. 💅",
            "When GPT understands you better than your dates—because it's smarter and listens more! 🤖✨",
            "Chart patterns are like dating—they always have a story to tell if you're paying attention! 💘📉"
        ],
        'crypto_prompts': [
            "FOMO might knock, but patience builds the mansion. 🏡💎",
            "Panic selling is like yelling during turbulence—sit tight, the skies clear eventually! ✈️✨",
            "Blockchain: Proof that simplicity can be revolutionary! 🔗🚀",
            "What’s the crypto wisdom you wish you had sooner? Let's spread the wealth of knowledge! 💡💰",
            "Luck vs. strategy in crypto? Spoiler: Strategy wins every time, but luck makes the ride fun! 🍀📈",
            "If Bitcoin hadn’t paved the way, Web3 wouldn't be the wild adventure it is today. 🙌💻",
            "Blockchain in one sentence: It's the internet’s way of finally growing up! 🛠️✨",
            "NFTs aren't just pictures—they're the first draft of a new internet! 🌐🎨",
            "Market crashes test patience, but the calm ones always catch the rebound! 🪂💹"
        ],
        'ai_prompts': [
            "Why does GPT sound smarter than me? Because it’s powered by ambition, not coffee. ☕🤖✨",
            "AI predicting your every move? Don't worry, it's just here to make life smoother than your ex ever did. 😉💻",
            "Training AI is like raising a star athlete: an investment in future wins! 🏆💡",
            "AI models are like your best friend—they know your quirks and make you look smarter. 👩‍💻🤖",
            "Overfitting expectations? Relax, even AI knows how to adapt to greatness. ✨📈",
            "Machine learning: Turning GPUs into the engines of tomorrow’s innovations. 🔥🚀",
            "AI dreaming big—one hallucination at a time. Don’t we all? 🤩🤖"
        ],
        'finance_prompts': [
            "Budgeting tip: Diversify smarter, not harder—Dogecoin’s fun, but so is balance! 🌈💸",
            "Financial planners are like GPS for your money—they keep you from driving into a ditch! 🚗💰",
            "Retirement plans are like blue-chip investments—solid, steady, and worth the wait. 🕰️📊",
            "Index funds vs. day trading: Are you a steady achiever or a thrill-seeker? 🏖️📈",
            "If investing were easy, everyone would have their own yacht—Warren Buffett’s got the blueprint! 🚤✨"
        ],
        'jokes_and_fun_prompts': [
            "Neural networks: Making spreadsheets look like amateurs since forever. 📊✨",
            "If crypto coins had personalities, which one’s stealing the spotlight at parties? 🎉💸",
            "What’s your funniest ‘learning moment’ in crypto? Share the love and laughs! 😂📈",
            "If Satoshi Nakamoto had a Twitter account, what would their bio say? 🤔✨",
            "Blockchain: Spreadsheets with swagger and a purpose. 🌶️🔗",
            "NFTs: The spicy intersection of art, ownership, and possibilities! 🎨💎"
        ]
    }


class TwitterBot:
    """Main Twitter bot implementation."""
    
    def __init__(self):
        self.logger = setup_logger("athena")
        self.logger.info("Starting the bot...")
        self._initialize_components()
        
    def _initialize_components(self) -> None:
        """Initialize all required components and connections."""
        self._validate_env_variables()
        self.bot = PersonalityBot(model_path="athena_8bit_model", logger=self.logger)
        self.client = setup_twitter_client()
        self.api = self._setup_tweepy_api()
        self.rate_limit_tracker = RateLimitTracker()
        self.tweet_cleaner = TweetCleaner()

    def _validate_env_variables(self) -> None:
        """Ensure all required environment variables are set."""
        required_vars = ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET", "BOT_USER_ID"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def _setup_tweepy_api(self) -> tweepy.API:
        """Set up and return Tweepy API instance."""
        return tweepy.API(tweepy.OAuth1UserHandler(
            consumer_key=os.getenv('API_KEY'),
            consumer_secret=os.getenv('API_SECRET'),
            access_token=os.getenv('ACCESS_TOKEN'),
            access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
        ))

    def _generate_tweet_response(self, prompt: str, max_attempts: int = 3) -> str:
        """Generate a tweet response with retry logic."""
        for attempt in range(max_attempts):
            try:
                response = self.bot.generate_response(prompt)
                if MIN_TWEET_LENGTH <= len(response) <= MAX_TWEET_LENGTH:
                    return response
            except Exception as e:
                self.logger.warning(f"Generation attempt {attempt + 1} failed: {str(e)}")
        
        return self._get_fallback_tweet()

    def _get_fallback_tweet(self) -> str:
        """Return a fallback tweet when generation fails."""
        fallbacks = [
            "Crypto markets never sleep, and neither should your strategies! 💅 #CryptoLife",
            "DYOR and don't let FOMO get you—research is key to success! ✨ #CryptoWisdom",
            "Diversification is the spice of life, even in the crypto world! 🌟 #CryptoInvesting",
            "Don't let panic sell-offs drain your gains. Stay calm and HODL! 🚀 #CryptoTips",
            "Your seed phrase is sacred—treat it like your most prized possession! 🔐 #CryptoSecurity"
        ]
        return random.choice(fallbacks)

    def _handle_meme_post(self) -> Optional[str]:
        """Handle posting a meme with caption."""
        memes_folder = os.path.join(os.getcwd(), 'memes')
        if not os.path.exists(memes_folder):
            self.logger.error(f"Memes folder not found at {memes_folder}")
            return None

        supported_formats = ('.jpg', '.jpeg', '.png', '.gif')
        images = [f for f in os.listdir(memes_folder) if f.lower().endswith(supported_formats)]
        
        if not images:
            return None

        image_path = os.path.join(memes_folder, random.choice(images))
        caption = random.choice([
            "This meme? Pure gold. 🪙✨ #Tetherballcoin",
            "Some things you just can't unsee. 😂 #CryptoHumor",
            "Hodlers will understand. 💎🙌 #Tetherballcoin",
            "Because laughter is the best investment. 😂📈 #CryptoMemes",
            "Meme game strong, just like our coin. 🚀🔥 #Tetherballcoin"
        ])
        
        return post_image_with_tweet(self.client, self.api, caption, image_path, self.logger)

    def post_tweet(self) -> Optional[str]:
        """Post a new tweet, either text or meme."""
        self.logger.info("Starting tweet posting process...")
        
        try:
            # Handle meme posting chance
            if random.random() < MEME_POSTING_CHANCE:
                return self._handle_meme_post()

            # Handle text tweet
            prompt = random.choice([prompt for prompts in get_prompts().values() for prompt in prompts])
            self.logger.info(f"Selected prompt: {prompt}")
            
            tweet = self._generate_tweet_response(prompt)
            tweet = self.tweet_cleaner.clean_tweet(tweet)
            self.logger.info(f"Generated tweet: {tweet}")
            
            result = self.client.create_tweet(text=tweet)
            return result.data.get('id')

        except Exception as e:
            self.logger.error(f"Error posting tweet: {str(e)}", exc_info=True)
            return None

    def reply_to_last_three(self, tweet_id: str, since_id: Optional[str] = None) -> Optional[str]:
        """Reply to the last three comments on a specific tweet."""
        try:
            bot_user_id = os.getenv("BOT_USER_ID")
            replies = search_replies_to_tweet(self.client, tweet_id, bot_user_id)
            
            if not replies:
                self.logger.info("No new replies found.")
                return since_id

            sorted_replies = sorted(replies, key=lambda x: x.id)
            new_replies = [reply for reply in sorted_replies if not since_id or reply.id > since_id]
            latest_replies = new_replies[-3:] if new_replies else []
            
            if not latest_replies:
                self.logger.info("No new replies since last check.")
                return since_id

            for reply in latest_replies:
                try:
                    self.logger.info(f"Processing reply: {reply.text}")
                    response = self._generate_tweet_response(reply.text)
                    response = self.tweet_cleaner.clean_tweet(response)
                    
                    if not response:
                        response = f"@{reply.author.username} Thanks for engaging! 🤔"
                    
                    self.client.create_tweet(text=response, in_reply_to_tweet_id=reply.id)
                    time.sleep(REPLY_DELAY_SECONDS)
                    
                except Exception as e:
                    self.logger.error(f"Error replying to tweet {reply.id}: {str(e)}")
                    continue

            return max(reply.id for reply in latest_replies) if latest_replies else since_id

        except Exception as e:
            self.logger.error(f"Error in reply process: {str(e)}", exc_info=True)
            return since_id

    def run(self):
        """Main bot running loop."""
        since_id = None
        reply_check_interval = 60 * 15  # 15 minutes
        reply_cycles = 3
        post_cooldown = 60 * 60  # 45 minutes
        initial_wait = 60 * 10  # 10 minutes

        while True:
            try:
                self.logger.info("Starting new bot cycle...")
                
                # Do one final check for replies from previous tweet if we have a tweet_id
                if hasattr(self, 'last_tweet_id') and self.last_tweet_id:
                    self.logger.info("Checking for final replies on previous tweet...")
                    since_id = self.reply_to_last_three(self.last_tweet_id, since_id)
                
                tweet_id = self.post_tweet()
                if tweet_id:
                    self.logger.info(f"Posted tweet: {tweet_id}")
                    self.last_tweet_id = tweet_id  # Store for next cycle's final check

                    self.logger.info(f"Waiting {initial_wait // 60} minutes before starting reply cycles...")
                    time.sleep(initial_wait)
                    
                    for cycle in range(reply_cycles):
                        self.logger.info(f"Starting reply cycle {cycle + 1}/{reply_cycles}")
                        since_id = self.reply_to_last_three(tweet_id, since_id)
                        self.logger.info(f"Completed reply cycle {cycle + 1}")
                        
                        if cycle < reply_cycles - 1:
                            self.logger.info(f"Sleeping for {reply_check_interval // 60} minutes...")
                            time.sleep(reply_check_interval)

                    self.logger.info(f"Cooling down for {post_cooldown // 60} minutes...")
                    time.sleep(post_cooldown)
                else:
                    self.logger.error("Tweet posting failed. Retrying after cooldown...")
                    time.sleep(post_cooldown)
                    continue

            except tweepy.errors.TooManyRequests as e:
                self.rate_limit_tracker.add_rate_limit()
                reset_time = int(e.response.headers.get('x-rate-limit-reset', time.time() + 60))
                sleep_time = self.rate_limit_tracker.get_sleep_time(reset_time)
                
                if self.rate_limit_tracker.should_extended_sleep():
                    self.logger.error(
                        f"Rate limit hit {self.rate_limit_tracker.threshold} times in "
                        f"{self.rate_limit_tracker.window_minutes} minutes. "
                        f"Sleeping for {self.rate_limit_tracker.backoff_hours} hours..."
                    )
                else:
                    self.logger.error("Rate limit hit. Retrying after cooldown...")
                
                self.logger.info(f"Sleeping for {sleep_time} seconds...")
                time.sleep(sleep_time)

            except Exception as e:
                self.logger.error("Error in main loop", exc_info=True)
                self.logger.info("Retrying after 15 minutes...")
                time.sleep(60 * 15)

def main():
    """Main entry point for the bot."""
    try:
        bot = TwitterBot()
        bot.run()
    except Exception as e:
        logging.error("Fatal error in main", exc_info=True)
        raise

if __name__ == "__main__":
    main()