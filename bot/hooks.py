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
    "Newsflash!", "Heads up!", "Crypto chat time!", "Just thinking:",
    # Engagement starters
    "Question for you:", "Quick thought:", "So here's the deal:",
    "Word on the street:", "Update:", "Random thought:",
    # Category specific
    "Crypto musings:", "Tech vibes:", "Here's a spicy take:",
    # Fresh additions
    "🌶️ Controversial opinion:", "💎 Gem alert:", "🚀 Launch sequence:",
    "💫 Galaxy brain moment:", "🎭 Drama in the cryptoverse:",
]

HOOKS = {
    "market_analysis": [
        "Market alert:", "Chart check:", "Price watch:", 
        "Trading insight:", "Trend spotting:", "Market pulse:",
        "Trading update:", "Market moves:", "Price tea:",
        "Portfolio drama:", "Market gossip:", "Trading tea:"
    ],
    "tech_discussion": [
        "Tech tea:", "Protocol tea:", "Blockchain drama:", 
        "Scaling tea:", "Tech breakthrough:", "Innovation gossip:",
        "Code drama:", "Dev tea:", "Architecture tea:",
        "Protocol drama:", "Tech gossip:", "Blockchain tea:"
    ],
    "defi": [
        "DeFi drama:", "Yield tea:", "Protocol gossip:", 
        "TVL tea:", "DeFi tea:", "Farming drama:",
        "Liquidity tea:", "Staking gossip:", "Pool drama:",
        "APY tea:", "DeFi gossip:", "Yield drama:"
    ],
    "nft": [
        "NFT drama:", "Mint tea:", "Floor gossip:", 
        "Rarity tea:", "Collection drama:", "NFT tea:",
        "Art drama:", "Project tea:", "Trait gossip:",
        "Market tea:", "NFT gossip:", "Collection tea:"
    ],
    "culture": [
        "Culture tea:", "DAO drama:", "Community gossip:", 
        "Web3 tea:", "Drama alert:", "Vibe check:",
        "Alpha tea:", "Scene drama:", "Community tea:",
        "Trend gossip:", "Culture drama:", "Web3 gossip:"
    ],
    "general": [
        "Hot take:", "Spicy opinion:", "Plot twist:", 
        "Real talk:", "Quick tea:", "Fresh gossip:",
        "Drama alert:", "Tea time:", "Spill alert:",
        "Gossip check:", "Vibe alert:", "Take incoming:"
    ]
}

# Category-specific styling
EMOJIS = {
    "market_analysis": ["📈", "📊", "💹", "📉", "💰", "📱", "💎", "🚀", "🌙"],
    "tech_discussion": ["⚡️", "🔧", "💻", "🛠️", "🚀", "🔨", "🎮", "🔋", "💡"],
    "defi": ["🏦", "💰", "🏧", "💎", "🔄", "🏆", "💸", "🌱", "🏃‍♀️"],
    "nft": ["🎨", "🖼️", "🎭", "🎪", "🎯", "🎟️", "🎸", "🎮", "🎲"],
    "culture": ["🌐", "🤝", "🗣️", "🌟", "🎮", "🎭", "🎪", "🎯", "🎨"],
    "general": ["🚀", "💎", "🌙", "✨", "💫", "🔥", "🌟", "💅", "👀"]
}

# Enhanced hashtags with personality
HASHTAGS = {
    "market_analysis": [
        "#CryptoTrading", "#TechnicalAnalysis", "#CryptoMarkets",
        "#Trading", "#CryptoSignals", "#MarketAnalysis",
        "#CryptoTea", "#TradingGossip", "#MarketDrama"
    ],
    "tech_discussion": [
        "#Blockchain", "#CryptoTech", "#Web3Dev",
        "#BlockchainTech", "#CryptoInnovation", "#Tech",
        "#DevLife", "#CodeDrama", "#TechTea"
    ],
    "defi": [
        "#DeFi", "#YieldFarming", "#Staking",
        "#DeFiYield", "#Farming", "#PassiveIncome",
        "#DeFiDrama", "#YieldLife", "#StakingTea"
    ],
    "nft": [
        "#NFTs", "#NFTCommunity", "#NFTCollector",
        "#NFTArt", "#NFTProject", "#DigitalArt",
        "#NFTDrama", "#NFTTea", "#CollectionGossip"
    ],
    "culture": [
        "#CryptoCulture", "#DAOs", "#Web3",
        "#Community", "#CryptoTwitter", "#Web3Culture",
        "#CryptoTea", "#Web3Drama", "#CultureGossip"
    ],
    "general": [
        "#Crypto", "#Web3", "#Bitcoin",
        "#Ethereum", "#Blockchain", "#CryptoLife",
        "#CryptoTea", "#BlockchainDrama", "#Web3Gossip"
    ]
}

FALLBACK_RESPONSES = [
    "Crypto never sleeps, and neither do the opportunities! What's catching your eye in the market? 👀",
    "Another day in crypto – where the memes are hot and the takes are hotter! 🌶️",
    "Sometimes the best crypto strategy is grabbing popcorn and enjoying the show! 🍿",
    "Plot twist: crypto is just spicy math with memes! 💅",
    "In crypto we trust... to keep things interesting! ✨",
    "Tea time in the cryptoverse! Who's ready for some drama? 🫖",
    "Serving fresh crypto tea, hot and ready! ☕",
    "Your daily dose of blockchain drama incoming! 🎭",
    "Web3 gossip hour! Grab your popcorn! 🍿",
    "Spilling some crypto tea today! 💅"
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

def clean_response(text: str) -> str:
    """
    Clean and format the response text.
    Args:
        text (str): Input text
    Returns:
        str: Cleaned text
    """
    # Remove leading/trailing quotes
    text = text.strip('"\'')
    
    # Remove URLs and meta-commentary
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'^(here is|here\'s) my attempt.*?:', '', text, flags=re.IGNORECASE)
    
    # Standardize ellipsis and dashes
    text = re.sub(r'\. \. \.|\.\.\.|…', '...', text)
    text = re.sub(r'\s*--?\s*', ' – ', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Handle markdown and formatting
    text = re.sub(r'\*\*', '', text)  # Remove markdown bold
    text = re.sub(r'_([^_]+)_', r'\1', text)  # Remove markdown italic
    
    # Fix punctuation issues with quotes
    text = text.replace('!"', '!')  # Fix quote after exclamation
    text = text.replace('."', '.')  # Fix quote after period
    text = text.replace('?"', '?')  # Fix quote after question mark
    
    # Check for incomplete endings
    text_lower = text.lower()
    if any(text_lower.rstrip('.!?').endswith(phrase) for phrase in INCOMPLETE_PHRASES):
        for phrase in INCOMPLETE_PHRASES:
            if text_lower.rstrip('.!?').endswith(phrase):
                text = text[:text.lower().rindex(phrase)].strip()
                break
    
    # Fix punctuation
    text = re.sub(r'[!?.][\s!?.]*$', '!', text)  # End with single punctuation
    text = re.sub(r'\s*([.!?])\s*', r'\1 ', text)  # Fix spacing around punctuation
    
    # Clean up any remaining quotes
    text = re.sub(r'"([^"]*)"', r'\1', text)  # Remove paired quotes
    text = text.replace('"', '')  # Remove any remaining quotes
    
    # Ensure proper ending
    if not text.rstrip().endswith(('!', '?', '.')):
        text += '!'
        
    return text.strip()

def add_personality(text: str, category: str) -> str:
    """
    Add personality markers to the text.
    Args:
        text (str): Input text
        category (str): Content category
    Returns:
        str: Text with personality markers
    """
    # Add random personality marker
    trait = random.choice(list(PERSONALITY_MARKERS.keys()))
    marker = random.choice(PERSONALITY_MARKERS[trait])
    
    # 30% chance to add marker at start
    if random.random() < 0.3:
        text = f"{marker} {text}"
    
    return text

def add_emojis_and_hashtags(text: str, category: str) -> str:
    """
    Add emojis and hashtags to the response with proper formatting.
    Args:
        text (str): Input text
        category (str): Content category
    Returns:
        str: Text with emojis and/or hashtags
    """
    text = add_personality(text, category)
    
    if random.random() > 0.2:  # 80% chance to skip additions
        return text
        
    text_length = len(text)
    space_left = 280 - text_length

    if space_left < 10:  # Ensure enough space for additions
        return text

    additions = []

    # Add emojis
    if random.random() < 0.3 and space_left >= 4:
        emoji_count = min(2, space_left // 2)
        if emoji_count > 0:
            emojis = random.sample(EMOJIS[category], emoji_count)
            additions.extend(emojis)

    # Add hashtags
    if random.random() < 0.7:
        remaining_space = 280 - (text_length + sum(len(a) + 1 for a in additions))
        if remaining_space >= 15:
            hashtag_count = min(2, remaining_space // 15)
            if hashtag_count > 0:
                hashtags = random.sample(HASHTAGS[category], hashtag_count)
                additions.extend(hashtags)

    if additions:
        return f"{text} {' '.join(additions)}"
    return text


def extract_relevant_tweet(prompt: str, text: str) -> str:
    """
    Extract the generated tweet from the response.
    Args:
        prompt (str): Original prompt
        text (str): Generated text
    Returns:
        str: Extracted tweet
    """
    try:
        parts = text.split("Tweet:")
        if len(parts) < 2:
            return clean_response(text)
        
        # Get content after "Tweet:" and clean it
        tweet = parts[-1].strip().split('\n')[0]
        
        # Remove quotes at the beginning and end
        tweet = tweet.strip('"\'')
        
        # Check for generic or empty responses
        generic_starts = [
            "here is my attempt",
            "let me try",
            "okay, here",
            "athena here",
            "hey there",
            "hey devs",
            "hey guys"
        ]
        
        if any(tweet.lower().startswith(start) for start in generic_starts):
            return random.choice(FALLBACK_RESPONSES)
        
        # Check for incomplete thoughts
        forbidden_patterns = [
            r'\d/\d', r'thread', r'\.\.\.$', r'to be continued',
            r'next part', r'stay tuned', r'coming soon',
            r'hold on', r'wait for it'
        ]
        
        if any(re.search(pattern, tweet.lower()) for pattern in forbidden_patterns):
            return random.choice(FALLBACK_RESPONSES)
            
        return clean_response(tweet)
        
    except Exception:
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
    
    # Enhanced personality base instruction
    base_instruction = (
        "You are Athena, a sassy crypto and finance expert with major attitude and wit. "
        "Create ONE engaging tweet that serves tea, spills gossip, or drops knowledge bombs. "
        "Keep it focused, complete, and avoid meta-commentary. "
        "Never end with '...' or incomplete thoughts. "
        "Make every word count and ensure your message is both informative and entertaining. "
        "Channel your inner crypto influencer with confidence and style."
    )

    # Enhanced sentiment tones with personality
    sentiment_tone = {
        "positive": (
            "Serve the tea with extra sparkle and enthusiasm! "
            "Make your observations clever and your excitement contagious. "
            "This is good news - make it pop!"
        ),
        "negative": (
            "Keep that sass sharp but wrap the tough news in wit. "
            "Balance criticism with clever insights. "
            "Even in a dip, keep your personality strong!"
        ),
        "neutral": (
            "Blend facts with fashion, honey! "
            "Stay objective but make it entertaining. "
            "Your analysis should be as sharp as your attitude!"
        )
    }.get(sentiment, "Balance insight with humor, staying objective but engaging.")

    # Enhanced category focus with personality
    category_focus = {
        "market_analysis": (
            "Spill the market tea with a mix of data and drama! "
            "Make those charts and trends sound like the latest gossip. "
            "Numbers are your runway - work it!"
        ),
        "tech_discussion": (
            "Break down tech like you're explaining drama to your bestie. "
            "Those protocols? Make them the stars of your story. "
            "Code is your catwalk - strut it!"
        ),
        "defi": (
            "Serve DeFi realness with a side of sass. "
            "Make yields and liquidity pools sound like the hottest tea. "
            "APY is your alphabet soup - stir it up!"
        ),
        "nft": (
            "Drop NFT knowledge like you're rating outfits at the Met Gala. "
            "Make those collections and floor prices sound like fashion trends. "
            "Digital art is your magazine spread - style it!"
        ),
        "culture": (
            "Dish out community tea with insider vibes. "
            "Make those trends and movements sound like A-list gossip. "
            "Web3 culture is your reality show - direct it!"
        ),
        "general": (
            "Spread crypto knowledge like it's the juiciest gossip in town. "
            "Make those concepts pop with personality and flair. "
            "Blockchain is your stage - own it!"
        )
    }.get(category, "Share crypto knowledge with broad appeal and clever observations.")

    return (
        f"{opener} {prompt}\n\n"
        f"Instruction:\n{base_instruction}\n"
        f"{category_focus}\n{sentiment_tone}\n"
        "Tweet:"
    )