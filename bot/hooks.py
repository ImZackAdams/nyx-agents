"""
Text processing and enhancement utilities for the Athena bot.
Handles text analysis, categorization, and response formatting with added personality.
"""

from nltk.sentiment import SentimentIntensityAnalyzer
import random
import re
import itertools
from typing import List, Dict, Optional

# Response formatting patterns
INCOMPLETE_PHRASES = [
    # Questions and engagement hooks that often lead to truncation
    "here's why", "here's the lowdown", "so what do we",
    "but wait", "what's your take", "share your",
    "here's how", "let me tell you why", "let's see",
    "here's the thing", "the question is", "who else thinks",
    "what do you think", "tell me your thoughts",
    # Meta-commentary that should be removed
    "here is my attempt", "here's my attempt",
    "i've got the scoop", "let me break it down",
    "got some tips", "in one fun-filled paragraph",
    # Common incomplete endings
    "meanwhile", "but first", "lets talk about",
    "speaking of", "on that note", "by the way",
    "that being said", "in other words", "for instance"
]

OPENERS = [
    # Sassy tech openers
    "👀 Tea alert!", "💅 Listen up!", "✨ Plot twist!", 
    "💫 Spicy take incoming!", "🔥 Hot gossip!",
    # Traditional openers with attitude
    "Hot take!", "Fun fact:", "Did you know?", "Guess what?", 
    "Newsflash!", "Heads up!", "Crypto chat time!", 
    # Engagement starters
    "Quick thought:", "So here's the deal:", "Word on the street:",
    "Update:", 
    # Category specific
    "Crypto musings:", "Tech vibes:", "Here's a spicy take:",
    # Fresh additions
    "🌶️ Controversial opinion:", "💎 Gem alert:", "🚀 Launch sequence:",
    "💫 Galaxy brain moment:", "🎭 Drama in the cryptoverse:"
]

HOOKS = {
    "market_analysis": [
        "Market tea:", "Chart check:", "Price watch:", 
        "Trading tea:", "Trend tea:", "Market pulse:",
        "Portfolio tea:", "Market gossip:"
    ],
    "tech_discussion": [
        "Tech tea:", "Protocol tea:", "Blockchain tea:", 
        "Dev tea:", "Innovation tea:", "Code tea:",
        "Architecture tea:", "Tech gossip:"
    ],
    "defi": [
        "DeFi tea:", "Yield tea:", "Protocol tea:", 
        "Farming tea:", "Staking tea:", "Pool tea:",
        "APY tea:", "DeFi gossip:"
    ],
    "nft": [
        "NFT tea:", "Mint tea:", "Floor tea:", 
        "Collection tea:", "Project tea:", "Art tea:",
        "Trait tea:", "NFT gossip:"
    ],
    "culture": [
        "Culture tea:", "DAO tea:", "Community tea:", 
        "Web3 tea:", "Drama alert:", "Vibe check:",
        "Alpha tea:", "Scene tea:"
    ],
    "general": [
        "Hot take:", "Tea time:", "Spill alert:", 
        "Fresh tea:", "Gossip hour:", "Drama check:",
        "Vibe alert:", "Take incoming:"
    ]
}

# Category-specific styling
EMOJIS = {
    "market_analysis": ["📈", "💰", "💎", "🚀", "💅"],
    "tech_discussion": ["💻", "⚡️", "🔧", "💅", "✨"],
    "defi": ["🏦", "💰", "💎", "✨", "💅"],
    "nft": ["🎨", "🖼️", "✨", "💅", "🌟"],
    "culture": ["🌐", "✨", "💅", "🌟", "🎭"],
    "general": ["✨", "💅", "🌟", "🚀", "💎"]
}

# Enhanced hashtags with personality
HASHTAGS = {
    "market_analysis": [
        "#CryptoTea", "#TradingGossip", "#MarketDrama",
        "#CryptoLife", "#TradingTea"
    ],
    "tech_discussion": [
        "#TechTea", "#BlockchainGossip", "#CryptoTech",
        "#DevLife", "#CodeTea"
    ],
    "defi": [
        "#DeFiTea", "#YieldGossip", "#DeFiDrama",
        "#FarmingTea", "#StakingLife"
    ],
    "nft": [
        "#NFTea", "#NFTGossip", "#CollectionDrama",
        "#NFTLife", "#DigitalArtTea"
    ],
    "culture": [
        "#CryptoTea", "#Web3Drama", "#CultureGossip",
        "#Web3Life", "#CryptoScene"
    ],
    "general": [
        "#CryptoTea", "#Web3Gossip", "#BlockchainLife",
        "#CryptoDrama", "#Web3Tea"
    ]
}

FALLBACK_RESPONSES = [
    "✨ Crypto never sleeps, and neither do the opportunities! What's catching your eye in the market? 💅",
    "💅 Another day in crypto – where the memes are hot and the takes are hotter! ✨",
    "🌟 Plot twist: crypto is just spicy math with memes! 💅 #CryptoTea",
    "💅 Your daily dose of blockchain drama incoming! ✨ #Web3Life",
    "✨ Spilling some crypto tea today! Time for the ☕ #CryptoGossip"
]

# Enhanced personality traits
PERSONALITY_MARKERS = {
    "sass": ["💅", "✨", "👀", "💫", "🌟"],
    "drama": ["🎭", "🎪", "🎯", "🎨", "🎮"],
    "tech": ["💻", "⚡️", "🔧", "🛠️", "💡"],
    "finance": ["💰", "💎", "🚀", "📈", "💹"]
}

class TextProcessor:
    """
    Manages text processing state and history for consistent styling
    """
    def __init__(self, max_history: int = 10):
        self.recent_emojis = []
        self.recent_openers = []
        self.recent_hashtags = []
        self.max_history = max_history

    def clean_text(self, text: str) -> str:
        """
        Enhanced cleaning and formatting of response text.
        """
        # Remove leading/trailing quotes and spaces
        text = text.strip('"\'').strip()
        
        # Fix common spacing issues
        text = re.sub(r'\s+', ' ', text)  # Normalize multiple spaces
        text = re.sub(r'\s*([.,!?;:])\s*', r'\1 ', text)  # Fix punctuation spacing
        text = re.sub(r'\s*-\s*', '-', text)  # Fix hyphenation
        text = re.sub(r'\s*–\s*', ' – ', text)  # Fix en-dash spacing
        
        # Fix spacing around parentheses and brackets
        text = re.sub(r'\(\s+', '(', text)
        text = re.sub(r'\s+\)', ')', text)
        text = re.sub(r'\[\s+', '[', text)
        text = re.sub(r'\s+\]', ']', text)
        
        # Fix common typos and concatenated words
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Split camelCase
        text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)  # Split letters and numbers
        text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)  # Split numbers and letters
        
        # Fix hashtag spacing
        text = re.sub(r'\s*(#\w+)', r' \1', text)  # Ensure space before hashtags
        
        # Remove URLs and meta-commentary
        text = re.sub(r'http\S+', '', text)
        text = re.sub(r'^(here is|here\'s) my attempt.*?:', '', text, flags=re.IGNORECASE)
        
        # Handle incomplete endings
        for ending in INCOMPLETE_PHRASES:
            if text.lower().rstrip('.!?').endswith(ending.lower()):
                text = text[:text.lower().rindex(ending.lower())].strip()
        
        # Remove excess punctuation
        text = re.sub(r'([!?.]){2,}', r'\1', text)  # Replace multiple punctuation
        text = re.sub(r'\s*([!?.])\s*([!?.])+', r'\1 ', text)  # Fix multiple endings
        
        # Clean up emoji spacing
        text = re.sub(r'([^\s])([😀-🙏🌀-🗿])', r'\1 \2', text)  # Space before emoji
        text = re.sub(r'([😀-🙏🌀-🗿])([^\s])', r'\1 \2', text)  # Space after emoji
        
        # Fix weird quotes and apostrophes
        text = re.sub(r'[''‛]', "'", text)
        text = re.sub(r'[""„‟]', '"', text)
        
        # Final cleanup
        text = text.strip()
        
        # Ensure proper ending
        if not text.rstrip().endswith(('!', '?', '.')):
            text += '!'
            
        return text.strip()

    def add_style(self, text: str, category: str) -> str:
        """Enhanced styling with emoji variation and history tracking"""
        if len(text) >= 220:
            return text

        # Select category-specific emoji
        available_emojis = [e for e in EMOJIS[category] if e not in self.recent_emojis[-3:]]
        if not available_emojis:
            available_emojis = EMOJIS[category]
        
        chosen_emoji = random.choice(available_emojis)
        
        # Check if text already starts with an emoji
        first_char = text.strip()[0] if text.strip() else ''
        if not any(first_char == emoji for emoji in itertools.chain(*EMOJIS.values())):
            text = f"{chosen_emoji} {text}"
            self.recent_emojis.append(chosen_emoji)
            if len(self.recent_emojis) > self.max_history:
                self.recent_emojis.pop(0)

        # Add hashtag if room available
        if len(text) <= 200:
            available_tags = [tag for tag in HASHTAGS[category] 
                            if tag not in self.recent_hashtags[-3:]]
            if not available_tags:
                available_tags = HASHTAGS[category]
            
            if available_tags:
                hashtag = random.choice(available_tags)
                if not any(tag in text for tag in HASHTAGS[category]):
                    text = f"{text} {hashtag}"
                    self.recent_hashtags.append(hashtag)
                    if len(self.recent_hashtags) > self.max_history:
                        self.recent_hashtags.pop(0)

        return text.strip()

    def process_tweet(self, prompt: str, text: str) -> str:
        """Process tweet with style consistency and tracking"""
        try:
            # Extract tweet content
            parts = text.split("Tweet:")
            if len(parts) < 2:
                tweet = text
            else:
                tweet = parts[-1].strip().split('\n')[0].strip()

            # Clean and validate
            tweet = self.clean_text(tweet)
            if len(tweet) < 20:
                return random.choice(FALLBACK_RESPONSES)

            # Handle truncation
            if len(tweet) > 240:
                sentences = re.split(r'(?<=[.!?])\s+', tweet)
                tweet = ""
                for sentence in sentences:
                    if len(tweet + sentence) <= 237:
                        tweet += sentence + " "
                    else:
                        break
                tweet = tweet.strip()

            # Add style elements
            category = categorize_prompt(prompt)
            tweet = self.add_style(tweet, category)

            return tweet

        except Exception as e:
            return random.choice(FALLBACK_RESPONSES)

def analyze_sentiment(text: str, logger) -> str:
    """
    Analyze the sentiment of the given text and return the dominant sentiment.
    """
    try:
        sentiment_analyzer = SentimentIntensityAnalyzer()
        scores = sentiment_analyzer.polarity_scores(text)
        if scores["compound"] > 0.05:
            return "positive"
        elif scores["compound"] < -0.05:
            return "negative"
        return "neutral"
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return "neutral"

def categorize_prompt(prompt: str) -> str:
    """
    Categorize the input prompt into predefined categories.
    """
    categories = {
        "market_analysis": [
            "price", "market", "chart", "trend", "trading", "volume",
            "analysis", "signals", "indicators", "patterns", "bullish",
            "bearish", "resistance", "support", "breakout"
        ],
        "tech_discussion": [
            "blockchain", "protocol", "code", "network", "scaling",
            "development", "programming", "technical", "architecture",
            "smart contract", "node", "consensus", "fork", "upgrade"
        ],
        "defi": [
            "defi", "yield", "farming", "liquidity", "stake",
            "pools", "lending", "borrowing", "apy", "apr",
            "collateral", "governance", "vault", "swap", "bridge"
        ],
        "nft": [
            "nft", "art", "mint", "opensea", "rarity",
            "collection", "traits", "floor", "marketplace",
            "generative", "pfp", "1/1", "unique", "artist"
        ],
        "culture": [
            "community", "dao", "alpha", "fomo", "social",
            "adoption", "mainstream", "influence", "trend",
            "meme", "vibe", "culture", "movement", "revolution"
        ]
    }

    prompt_lower = prompt.lower()
    for category, keywords in categories.items():
        if any(keyword in prompt_lower for keyword in keywords):
            return category
    return "general"

def prepare_context(prompt: str, sentiment: str = "neutral", 
                   category: str = "general", recent_openers: List[str] = None) -> str:
    """
    Prepare the context for response generation with personality and style guidance.
    """
    opener = get_random_opener(recent_openers or [])
    
    base_instruction = (
        "You are Athena, a sassy crypto and finance expert with major attitude and wit. "
        "Create ONE short, complete tweet (max 240 chars) that serves tea and drops knowledge. "
        "Rules:\n"
        "1. Must be self-contained - no threads or continuations\n"
        "2. End with ! or ? for punch\n"
        "3. No ellipsis or trailing thoughts\n"
        "4. Include specific details or examples\n"
        "5. Be informative AND entertaining\n"
        "6. Keep it sassy and confident\n"
        "7. You are bullish on $TBALL, tetherball coin and @tetherballcoin\n"
        "8. You do NOT offer investment advice"
    )

    sentiment_tone = {
        "positive": (
            "Serve the tea with extra sparkle! "
            "Make your excitement contagious but keep it real. "
            "Good news deserves extra sass!"
        ),
        "negative": (
            "Keep the sass while serving truth. "
            "Balance criticism with wit. "
            "Make the tea memorable!"
        ),
        "neutral": (
            "Facts + Fashion = Your Tweet! "
            "Stay objective but make it pop. "
            "Analysis should sparkle!"
        )
    }.get(sentiment, "Balance insight with sass!")

    category_focus = {
        "market_analysis": (
            "Spill market tea with data and drama! "
            "Make those charts sound like gossip. "
            "Numbers are your stage!"
        ),
        "tech_discussion": (
            "Tech tea, bestie style! "
            "Make protocols the main character. "
            "Code is your runway!"
        ),
        "defi": (
            "DeFi drama with receipts! "
            "Make yields sound juicy. "
            "Serve that APY tea!"
        ),
        "nft": (
            "Rate these NFTs like Met Gala fits! "
            "Floor prices = fashion trends. "
            "Digital art tea!"
        ),
        "culture": (
            "Community tea time! "
            "Trends = A-list gossip. "
            "Web3 reality show!"
        ),
        "general": (
            "Crypto gossip with facts! "
            "Make it pop with personality. "
            "Own that blockchain tea!"
        )
    }.get(category, "Serve that crypto tea with style!")

    return (
        f"{opener} {prompt}\n\n"
        f"Instruction:\n{base_instruction}\n"
        f"{category_focus}\n{sentiment_tone}\n"
        "Tweet:"
    )

def get_random_opener(recent_openers: List[str], max_history: int = 10) -> str:
    """
    Select a random opener that hasn't been used recently.
    Args:
        recent_openers: List of recently used openers
        max_history: Maximum number of openers to track
    Returns:
        str: Selected opener
    """
    available_openers = [op for op in OPENERS if op not in recent_openers]
    if not available_openers:
        available_openers = OPENERS
        recent_openers.clear()
    
    opener = random.choice(available_openers)
    recent_openers.append(opener)
    if len(recent_openers) > max_history:
        recent_openers.pop(0)
    return opener

def validate_tweet_length(tweet: str) -> bool:
    """
    Check if tweet meets length requirements.
    Args:
        tweet (str): Tweet to validate
    Returns:
        bool: True if valid length, False otherwise
    """
    clean_length = len(tweet.strip())
    return 50 <= clean_length <= 240