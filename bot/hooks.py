"""
Text processing and enhancement utilities for the Athena bot.
Handles text analysis, categorization, and response formatting with added personality.
"""

from nltk.sentiment import SentimentIntensityAnalyzer
import random
import re
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

def analyze_sentiment(text: str, logger) -> str:
    """
    Analyze the sentiment of the given text and return the dominant sentiment.
    Args:
        text (str): Input text
        logger: Logger instance
    Returns:
        str: "positive", "negative", or "neutral"
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
    Args:
        prompt (str): Input prompt
    Returns:
        str: Category label
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

def clean_response(text: str) -> str:
    """
    Clean and format the response text.
    Args:
        text (str): Input text
    Returns:
        str: Cleaned text
    """
    # Remove leading/trailing quotes and spaces
    text = text.strip('"\'').strip()
    
    # Remove URLs and meta-commentary
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'^(here is|here\'s) my attempt.*?:', '', text, flags=re.IGNORECASE)
    
    # Handle incomplete endings and ellipsis
    incomplete_endings = [
        "...", ". . .", "…", "meanwhile", "but first", "speaking of",
        "1/", "🧵", "thread", "to be continued", "stay tuned"
    ]
    
    for ending in incomplete_endings:
        if text.lower().rstrip('.!?').endswith(ending.lower()):
            text = text[:text.lower().rindex(ending.lower())].strip()
    
    # Standardize ellipsis and dashes
    text = re.sub(r'\. \. \.|\.\.\.|…', '', text)
    text = re.sub(r'\s*--?\s*', ' – ', text)
    
    # Remove markdown and extra formatting
    text = re.sub(r'\*\*|__', '', text)  # Remove bold
    text = re.sub(r'\*|_', '', text)     # Remove italic
    
    # Clean up spacing and punctuation
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize spaces
    text = re.sub(r'\s*([.!?])\s*', r'\1 ', text)  # Fix punctuation spacing
    
    # Ensure proper ending
    if not text.rstrip().endswith(('!', '?', '.')):
        text += '!'
    
    return text.strip()

def add_style(text: str, category: str) -> str:
    """
    Add emojis and hashtags while maintaining personality.
    Args:
        text (str): Input text
        category (str): Content category
    Returns:
        str: Styled text
    """
    # Ensure we have room for additions
    if len(text) >= 220:
        return text
        
    # Add personality emoji if none present
    has_emoji = any(char in text for char in ['💅', '✨', '👀', '🔥', '💫', '🌟'])
    if not has_emoji:
        text = f"✨ {text}"
    
    # Add hashtag if we have room
    if len(text) <= 200 and not any(tag in text for tag in HASHTAGS[category]):
        hashtag = random.choice(HASHTAGS[category])
        text = f"{text} {hashtag}"
    
    return text


def extract_relevant_tweet(prompt: str, text: str) -> str:
    """
    Extract and clean the generated tweet from the response.
    Args:
        prompt (str): Original prompt
        text (str): Generated text
    Returns:
        str: Extracted and cleaned tweet
    """
    try:
        # Split on "Tweet:" and get the last part
        parts = text.split("Tweet:")
        if len(parts) < 2:
            return clean_response(text)
        
        # Get the first line after "Tweet:"
        tweet_lines = parts[-1].strip().split('\n')
        tweet = tweet_lines[0].strip()
        
        # Clean the tweet
        tweet = clean_response(tweet)
        
        # Check for minimum content
        if len(tweet) < 20:
            return random.choice(FALLBACK_RESPONSES)
            
        # Handle truncation
        if len(tweet) > 240:
            sentences = re.split(r'(?<=[.!?])\s+', tweet)
            tweet = ""
            for sentence in sentences:
                if len(tweet + sentence) <= 237:  # Leave room for ending
                    tweet += sentence + " "
                else:
                    break
            tweet = tweet.strip()
            
            # Ensure proper ending
            if not tweet.endswith(('!', '?', '.')):
                tweet += '!'
        
        # Add style elements
        tweet = add_style(tweet, categorize_prompt(prompt))
        
        return tweet
        
    except Exception as e:
        return random.choice(FALLBACK_RESPONSES)

def prepare_context(prompt: str, sentiment: str = "neutral", 
                   category: str = "general", recent_openers: List[str] = None) -> str:
    """
    Prepare the context for response generation with personality and style guidance.
    Args:
        prompt (str): User prompt
        sentiment (str): Content sentiment
        category (str): Content category
        recent_openers: List of recent openers
    Returns:
        str: Prepared context
    """
    opener = get_random_opener(recent_openers or [])
    
    # Core personality instruction
    base_instruction = (
        "You are Athena, a sassy crypto and finance expert with major attitude and wit. "
        "Create ONE short, complete tweet (max 240 chars) that serves tea and drops knowledge. "
        "Rules:\n"
        "1. Must be self-contained - no threads or continuations\n"
        "2. End with ! or ? for punch\n"
        "3. No ellipsis or trailing thoughts\n"
        "4. Include specific details or examples\n"
        "5. Be informative AND entertaining\n"
        "6. Keep it sassy and confident"
    )

    # Enhanced sentiment tones
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

    # Focused category guidance
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