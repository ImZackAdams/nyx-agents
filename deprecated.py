
from dotenv import load_dotenv
import tweepy
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Tuple, List, Dict  # Add Tuple import here
import random
import re
from textblob import TextBlob
import time
import logging
import psutil

load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Device and model configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_PATH = "./fine_tuned_personality_bot/"  # Update with your model path

# Resource usage tracking function
def log_resource_usage():
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    # RAM usage
    memory_info = psutil.virtual_memory()
    memory_percent = memory_info.percent
    
    # GPU usage (if available)
    gpu_memory = 0
    gpu_utilization = 0
    if torch.cuda.is_available():
        gpu_memory = torch.cuda.memory_allocated() / 1024 / 1024  # in MB
        gpu_utilization = torch.cuda.utilization()

    logger.info(f"CPU Usage: {cpu_percent}% | RAM Usage: {memory_percent}%")
    if gpu_memory:
        logger.info(f"GPU Memory Usage: {gpu_memory} MB | GPU Utilization: {gpu_utilization}%")


class PersonalityBot:
    def __init__(self, model_path: str = MODEL_PATH):
        self.model_path = model_path
        self.model, self.tokenizer = self.setup_model()
    
    def setup_model(self) -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
        """Initialize and configure the model and tokenizer."""
        logger.info(f"Setting up model from {self.model_path}")
    
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at {self.model_path}")
    
        try:
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(self.model_path, use_fast=True)
            tokenizer.pad_token = tokenizer.eos_token
    
        except Exception as e:
            logger.error(f"Tokenizer loading failed: {str(e)}")
            raise
    
        try:
            # Load model and enforce FP16 for memory optimization
            logger.info("Loading model...")
            model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,  # Use FP16 if possible
                low_cpu_mem_usage=True,  # Avoid excessive memory usage on CPU
                device_map="auto"  # Automatically distribute model across available devices
            )
            model.eval()
    
            # Clear any unused GPU memory after model load to avoid fragmentation
            torch.cuda.empty_cache()
    
            logger.info("Model setup completed successfully")
            return model, tokenizer
    
        except Exception as e:
            logger.error(f"Model loading failed: {str(e)}")
            raise
        
    def categorize_prompt(self, prompt: str) -> str:
        """Categorize input prompt for contextual response generation."""
        categories: Dict[str, List[str]] = {
            "market_analysis": [
                "price", "market", "chart", "analysis", "trend", "prediction",
                "bull", "bear", "trading", "volume"
            ],
            "tech_discussion": [
                "blockchain", "protocol", "layer", "scaling", "code", "development",
                "smart contract", "gas", "network"
            ],
            "defi": [
                "defi", "yield", "farming", "liquidity", "stake", "lending",
                "borrow", "apy", "tvl"
            ],
            "nft": [
                "nft", "art", "collectible", "mint", "opensea", "rarity",
                "floor price", "pfp"
            ],
            "culture": [
                "community", "dao", "governance", "vote", "proposal",
                "alpha", "degen", "fud", "fomo"
            ]
        }
        
        prompt_lower = prompt.lower()
        for category, keywords in categories.items():
            if any(keyword in prompt_lower for keyword in keywords):
                return category
        return "general"

    def generate_hook(self, category: str) -> str:
        """Generate category-specific attention hooks with an expanded list."""
        hooks = {
            "market_analysis": [
                "Market alert:", "Chart check:", "Price watch:",
                "Trading insight:", "Market alpha:",
                "Trend spotting:", "Candlelight stories:", "RSI deep dive:",
                "Volatility watch:", "Support level breakdown:",
                "Resistance zone spotted:", "Market movers:",
                "All eyes on the charts:", "Is this a bull trap?",
                "Breakout or fakeout?", "Today's key levels:"
            ],
            "tech_discussion": [
                "Tech deep dive:", "Builder's corner:", "Protocol watch:",
                "Dev update:", "Architecture take:",
                "Blockchain in focus:", "Gas fee breakdown:", "Scaling challenges:",
                "Layer 2 spotlight:", "New upgrade analysis:",
                "Consensus mechanism debate:", "Crypto tech wars:",
                "Network optimization insights:", "Codebase comparison:",
                "Innovator's edge:", "Protocol vulnerabilities exposed:"
            ],
            "defi": [
                "DeFi alpha:", "Yield watch:", "Smart money move:",
                "Protocol alert:", "TVL update:",
                "Farming frenzy:", "Liquidity trends:", "Borrowing breakdown:",
                "Stakeholder spotlight:", "APR vs APY debate:",
                "Risk-adjusted returns:", "What's your yield strategy?",
                "Stablecoin flow insights:", "Vault innovations:",
                "Lending protocol comparison:", "DeFi's next big move:"
            ],
            "nft": [
                "NFT alpha:", "Collection watch:", "Mint alert:",
                "Floor check:", "Digital art take:",
                "Art reveal:", "Rare trait spotted:", "Is this the next blue chip?",
                "Profile picture wars:", "Who's flipping this?",
                "NFT drama explained:", "Rarity analysis:",
                "Auction insights:", "Utility vs hype debate:",
                "Next-gen collectibles:", "Art meets utility:"
            ],
            "culture": [
                "Culture take:", "DAO watch:", "Governance alert:",
                "Community vibe:", "Alpha leak:",
                "The crypto ethos:", "FOMO or FUD?", "Web3 lifestyle:",
                "Building the future:", "Influencer drama explained:",
                "Community-driven innovation:", "DAO proposal debates:",
                "Web3's cultural revolution:", "Crypto memes decoded:",
                "The rise of governance tokens:", "Who else is building?"
            ],
            "general": [
                "Hot take:", "Unpopular opinion:", "Plot twist:",
                "Real talk:", "Quick thought:",
                "Imagine this:", "What if I told you:", "Could this be true?",
                "Something to chew on:", "Here’s an idea:",
                "Change my mind:", "Big picture time:",
                "Food for thought:", "The future is calling:", "What comes next?",
                "Let’s break it down:"
            ]
        }
        
        category_hooks = hooks.get(category, hooks["general"])
        return random.choice(category_hooks) if random.random() < 0.2 else ""
    
    def add_emojis(self, text: str, category: str) -> str:
        """Add contextual emojis based on content category, with limited frequency."""
        emoji_sets = {
            "market_analysis": ["📈", "📊", "💹", "📉", "💸", "🎯", "📱"],
            "tech_discussion": ["⚡️", "🔧", "💻", "🛠️", "🔨", "🧮", "🔋"],
            "defi": ["🏦", "💰", "🏧", "💳", "🔄", "⚖️", "🎰"],
            "nft": ["🎨", "🖼️", "🎭", "🎪", "🎟️", "🎮", "🃏"],
            "culture": ["🌐", "🤝", "🗣️", "🎭", "🎪", "🎯", "🎲"],
            "general": ["🚀", "💎", "🌙", "🔥", "💡", "🎯", "⭐️"]
        }
        
        # Add emojis with 20% probability
        if random.random() > 0.2:
            return text
    
        category_emojis = emoji_sets.get(category, emoji_sets["general"])
        emoji_count = random.randint(1, 2)
        chosen_emojis = random.sample(category_emojis, emoji_count)
        
        return f"{text} {' '.join(chosen_emojis)}"

    def generate_engagement_phrase(self, category: str) -> str:
        """Generate contextual engagement prompts."""
        phrases = {
            "market_analysis": [
                "What's your price target?",
                "Bulls or bears?",
                "Who's buying this dip?",
                "Thoughts on this setup?"
            ],
            "tech_discussion": [
                "Devs, thoughts?",
                "Valid architecture?",
                "Spotted any issues?",
                "Who's building similar?"
            ],
            "defi": [
                "What's your yield strategy?",
                "Aping in?",
                "Found better rates?",
                "Risk level?"
            ],
            "nft": [
                "Cope or hope?",
                "Floor predictions?",
                "Minting this?",
                "Art or utility?"
            ],
            "culture": [
                "Based or nah?",
                "Who else sees this?",
                "Your governance take?",
                "DAO voters wya?"
            ],
            "general": [
                "Thoughts?",
                "Based?",
                "Who's with me?",
                "Change my mind."
            ]
        }
        
        category_phrases = phrases.get(category, phrases["general"])
        return random.choice(category_phrases) if random.random() < 0.3 else ""

    def add_hashtags(self, text: str, category: str) -> str:
        """Add relevant hashtags based on content and character limit, with limited frequency."""
        hashtags = {
            "market_analysis": [
                "#CryptoTrading", "#TechnicalAnalysis", "#CryptoMarkets",
                "#Trading", "#Charts", "#PriceAction"
            ],
            "tech_discussion": [
                "#Blockchain", "#CryptoTech", "#Web3Dev", "#DLT",
                "#SmartContracts", "#BuilderSpace"
            ],
            "defi": [
                "#DeFi", "#YieldFarming", "#Staking", "#DeFiSeason",
                "#PassiveIncome", "#DeFiYield"
            ],
            "nft": [
                "#NFTs", "#NFTCommunity", "#NFTCollector", "#NFTArt",
                "#NFTProject", "#TokenizedArt"
            ],
            "culture": [
                "#CryptoCulture", "#DAOs", "#Web3", "#CryptoTwitter",
                "#CryptoLife", "#BuildingWeb3"
            ],
            "general": [
                "#Crypto", "#Web3", "#Bitcoin", "#Ethereum",
                "#CryptoTwitter", "#BuildingTheFuture"
            ]
        }
    
        # Add hashtags with 40% probability
        if random.random() > 0.2:
            return text
    
        remaining_chars = 280 - len(text)
        if remaining_chars < 15:  # Not enough space for hashtags
            return text
    
        category_hashtags = hashtags.get(category, hashtags["general"])
        selected_hashtags = []
        
        # Add 1-2 hashtags while respecting character limit
        for _ in range(random.randint(1, 2)):
            if not category_hashtags or remaining_chars < 15:
                break
            hashtag = random.choice(category_hashtags)
            if len(hashtag) + 1 <= remaining_chars:
                selected_hashtags.append(hashtag)
                category_hashtags.remove(hashtag)
                remaining_chars -= len(hashtag) + 1
    
        return f"{text} {' '.join(selected_hashtags)}"
    
    def clean_response(self, text: str, category: str) -> str:
        """Clean and format the response for Twitter."""
        # Remove URLs and excessive whitespace
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
    
        # Remove leading and trailing quotation marks
        text = text.strip('"\'“”')
    
        # Replace multiple internal quotes with single quotes
        text = re.sub(r'"+', '"', text)
        text = re.sub(r"'+", "'", text)
    
        # Correct unbalanced quotation marks
        def balance_quotes(s):
            quote_chars = ['"', "'"]
            for quote in quote_chars:
                if s.count(quote) % 2 != 0:
                    s = s.replace(quote, '')  # Remove unmatched quotes
            return s
    
        text = balance_quotes(text)
    
        # Ensure the text ends with proper punctuation
        if text and text[-1] not in '.!?':
            text += '.'
    
        return text



    def get_fallback(self, category: str) -> str:
        """Generate category-specific fallback responses."""
        fallbacks = {
            "market_analysis": [
                "Charts looking juicy today! Anyone else seeing this setup? 📈",
                "Market's giving mixed signals but the volume tells a different story 👀"
            ],
            "tech_discussion": [
                "Sometimes the best protocols are the ones no one's talking about yet 🛠️",
                "Imagine still building without considering Layer 2 scaling 💻"
            ],
            "defi": [
                "Your yields are only as good as your risk management 🏦",
                "DeFi summer never ended, we just got better at farming 🌾"
            ],
            "nft": [
                "Art is subjective, but floor prices aren't 🎨",
                "Your NFT portfolio tells a story. Make it a good one 🖼️"
            ],
            "culture": [
                "Web3 culture is what we make it. Build accordingly 🌐",
                "Sometimes the real alpha is the friends we made along the way 🤝"
            ],
            "general": [
                "Just caught myself thinking about the future of crypto while making coffee ☕️",
                "Your portfolio is only as strong as your conviction 💎"
            ]
        }
        
        category_fallbacks = fallbacks.get(category, fallbacks["general"])
        return random.choice(category_fallbacks)

    def filter_tone(self, response: str) -> str:
        """Filter response tone and adjust if needed."""
        sentiment = TextBlob(response).sentiment
        
        if sentiment.polarity < -0.3:
            return self.get_fallback("general")
        
        if sentiment.subjectivity > 0.8:
            # Too subjective, add a disclaimer
            return f"Not financial advice but... {response}"
                
        return response
        

    def generate_response(self, prompt: str) -> str:
        """Generate a complete Twitter-ready response."""
        
        # Log resources before generating the response (before any processing starts)
        logger.info("Before inference:")
        log_resource_usage()
    
        category = self.categorize_prompt(prompt)
        
        instruction = (
            "You are a woman named Athena and your twitter handle is @tballbothq. "
            "You are a crypto and finance expert with a sharp sense of humor, blending the witty sarcasm of George Hotz with the storytelling flair of Theo Von. "
            "Your goal is to craft engaging, funny, and insightful tweets that educate your audience using appropriate slang and jargon. "
            "Each tweet should be coherent, make logical sense, and provide a clear takeaway or punchline. "
            "Avoid overusing slang—use it where it feels natural. "
            "Respond to the following prompt:\n\n"
        )
        # few shot examples
        examples = (
            "Prompt: What's your take on Bitcoin as digital gold?\n"
            "Tweet: Bitcoin as digital gold? Nah, it's more like digital real estate in the metaverse—except everyone's still arguing over the property lines. Who's still buying up the neighborhood? 🚀 #Bitcoin #Crypto\n\n"
            "Prompt: Explain staking in the context of DeFi but make it funny.\n"
            "Tweet: Staking in DeFi is like putting your money on a treadmill—you lock it up, it works out, and somehow you end up with more than just sweaty tokens. Gains on gains! 🏋️‍♂️ #DeFi #Staking\n\n"
        )
        
        context = f"{instruction}{examples}Prompt: {prompt}\nTweet:"
    
        # Tokenization (move to GPU)
        inputs = self.tokenizer(
            context,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=1024  # Increased to accommodate longer context
        ).to(device)
    
        # Enable mixed precision (float16) to reduce memory usage if using CUDA
        if torch.cuda.is_available():
            self.model = self.model.half()  # Use half precision to reduce memory usage
    
        try:
            # Log resources during inference (after tokenization, before generating output)
            logger.info("During inference:")
            log_resource_usage()
    
            # Perform inference (no intermediate logging)
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=80,
                    do_sample=True,
                    temperature=0.7,
                    top_k=50,
                    top_p=0.9,
                    repetition_penalty=1.5,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
    
            # Decode the generated text
            generated_text = self.tokenizer.decode(
                outputs[0],
                skip_special_tokens=True
            )
            
            # Apply enhancements (emojis, hashtags, etc.)
            response = generated_text.split("Tweet:")[-1].strip().split("\n")[0]
            
            # Check if the response is too short
            if not response or len(response) < 20:
                return self.get_fallback(category)
            
            # Apply formatting
            response = self.clean_response(response, category)
            response = self.filter_tone(response)
            response = self.add_emojis(response, category)
            response = self.add_hashtags(response, category)
    
            # Log resources after generating the response (after enhancements)
            logger.info("After inference and enhancements:")
            log_resource_usage()
    
            logger.info(f"Generated response: {response}")
            
            # Ensure the response fits within Twitter's character limit
            return response[:280]  # Ensure the response fits within Twitter's character limit
        
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return self.get_fallback(category)


    


def post_to_twitter(tweet, twitter_client):
    """Posts a tweet using the Twitter API."""
    try:
        twitter_client.create_tweet(text=tweet)  # Use `create_tweet` for v2 API
        logger.info("Tweet posted successfully!")
        print("Tweet posted successfully!")
    except tweepy.TweepError as e:
        logger.error(f"Failed to post tweet: {str(e)}")
        print(f"Failed to post tweet: {str(e)}")

def main():
    """Main execution function."""
    try:
        bot = PersonalityBot()
        logger.info("Bot initialized successfully")
        
        # Set up Twitter API client using .env variables
        api_key = os.getenv('API_KEY')
        api_secret = os.getenv('API_SECRET')
        bearer_token = os.getenv('BEARER_TOKEN')
        access_token = os.getenv('ACCESS_TOKEN')
        access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')

        # Authenticate with Twitter API v2
        client = tweepy.Client(
            bearer_token=bearer_token,
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )

        # Interactive mode
        logger.info("Entering interactive mode...")
        print("\n=== Interactive Mode ===")
        print("Enter your prompts (type 'quit' to exit, or 'post' to tweet a generated response):")
        
        while True:
            user_prompt = input("\nYour prompt: ").strip()

            if user_prompt.lower() == 'quit':
                print("Exiting... Thanks for using tbot!")
                break
            
            if not user_prompt:
                print("Please enter a valid prompt!")
                continue

            try:
                # Log the user input for debugging or record-keeping
                logger.info(f"User input: {user_prompt}")
                
                # Measure inference time
                start_time = time.time()
                response = bot.generate_response(user_prompt)
                elapsed_time = time.time() - start_time
                
                # Output the result to the user
                print(f"Response: {response}")
                print(f"Runtime: {elapsed_time:.2f} seconds")
                
                # Log the performance
                logger.info(f"Response generated in {elapsed_time:.2f} seconds")

                # Option to post to Twitter
                tweet_decision = input("Would you like to post this response to Twitter? (yes/no): ").strip().lower()
                if tweet_decision == 'yes':
                    post_to_twitter(response, client)

            except Exception as e:
                # Log the error in case of an issue
                logger.error(f"Error processing prompt: {str(e)}")
                print(f"Oops! Something went wrong: {str(e)}. Please try again.")

    except Exception as e:
        # Log critical errors
        logger.error(f"Critical application error: {str(e)}")
        print("Critical error occurred. Please check the logs for details.")

if __name__ == "__main__":
    main()