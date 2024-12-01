"""
Text processing and enhancement utilities for the Athena bot.
Handles text analysis, categorization, and response formatting.
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
    "Hot take!", "Fun fact:", "Did you know?", "Guess what?", 
    "Newsflash!", "Heads up!", "Crypto chat time!", "Just thinking:",
    "Question for you:", "Quick thought:", "So here's the deal:",
    "Word on the street:", "Update:", "Random thought:",
    "Crypto musings:", "Tech vibes:", "Here's a spicy take:",
]

HOOKS = {
    "market_analysis": [
        "Market alert:", "Chart check:", "Price watch:", 
        "Trading insight:", "Trend spotting:", "Market pulse:",
        "Trading update:", "Market moves:"
    ],
    "tech_discussion": [
        "Tech deep dive:", "Protocol watch:", "Blockchain in focus:", 
        "Scaling challenges:", "Tech breakthrough:", "Innovation alert:"
    ],
    "defi": [
        "DeFi alpha:", "Yield watch:", "Protocol alert:", 
        "TVL update:", "DeFi insight:", "Farming update:"
    ],
    "nft": [
        "NFT alpha:", "Mint alert:", "Floor check:", 
        "Rare trait spotted:", "Collection update:", "NFT insight:"
    ],
    "culture": [
        "Culture take:", "DAO watch:", "Community vibe:", 
        "The crypto ethos:", "Community pulse:", "Web3 culture:"
    ],
    "general": [
        "Hot take:", "Unpopular opinion:", "Plot twist:", 
        "Real talk:", "Quick thought:", "Fresh perspective:"
    ]
}

# Category-specific styling
EMOJIS = {
    "market_analysis": ["📈", "📊", "💹", "📉", "💰", "📱"],
    "tech_discussion": ["⚡️", "🔧", "💻", "🛠️", "🚀", "🔨"],
    "defi": ["🏦", "💰", "🏧", "💎", "🔄", "🏆"],
    "nft": ["🎨", "🖼️", "🎭", "🎪", "🎯", "🎟️"],
    "culture": ["🌐", "🤝", "🗣️", "🌟", "🎮", "🎭"],
    "general": ["🚀", "💎", "🌙", "✨", "💫", "🔥"]
}

HASHTAGS = {
    "market_analysis": [
        "#CryptoTrading", "#TechnicalAnalysis", "#CryptoMarkets",
        "#Trading", "#CryptoSignals", "#MarketAnalysis"
    ],
    "tech_discussion": [
        "#Blockchain", "#CryptoTech", "#Web3Dev",
        "#BlockchainTech", "#CryptoInnovation", "#Tech"
    ],
    "defi": [
        "#DeFi", "#YieldFarming", "#Staking",
        "#DeFiYield", "#Farming", "#PassiveIncome"
    ],
    "nft": [
        "#NFTs", "#NFTCommunity", "#NFTCollector",
        "#NFTArt", "#NFTProject", "#DigitalArt"
    ],
    "culture": [
        "#CryptoCulture", "#DAOs", "#Web3",
        "#Community", "#CryptoTwitter", "#Web3Culture"
    ],
    "general": [
        "#Crypto", "#Web3", "#Bitcoin",
        "#Ethereum", "#Blockchain", "#CryptoLife"
    ]
}

FALLBACK_RESPONSES = [
    "Crypto never sleeps, and neither do the opportunities! What's catching your eye in the market?",
    "Another day in crypto – where the memes are hot and the takes are hotter!",
    "Sometimes the best crypto strategy is grabbing popcorn and enjoying the show!",
    "Plot twist: crypto is just spicy math with memes!",
    "In crypto we trust... to keep things interesting!",
]

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
            "analysis", "signals", "indicators", "patterns"
        ],
        "tech_discussion": [
            "blockchain", "protocol", "code", "network", "scaling",
            "development", "programming", "technical", "architecture"
        ],
        "defi": [
            "defi", "yield", "farming", "liquidity", "stake",
            "pools", "lending", "borrowing", "apy", "apr"
        ],
        "nft": [
            "nft", "art", "mint", "opensea", "rarity",
            "collection", "traits", "floor", "marketplace"
        ],
        "culture": [
            "community", "dao", "alpha", "fomo", "social",
            "adoption", "mainstream", "influence", "trend"
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

def add_emojis_and_hashtags(text: str, category: str) -> str:
    """
    Add emojis and hashtags to the response with proper formatting.
    Args:
        text (str): Input text
        category (str): Content category
    Returns:
        str: Text with emojis and/or hashtags
    """
    if random.random() > 0.2:  # 80% chance to skip
        return text
        
    text_length = len(text)
    space_left = 280 - text_length
    
    if space_left < 10:
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
    
    base_instruction = (
        "You are Athena, a crypto and finance expert with sass and wit. "
        "Create ONE engaging tweet that's both informative and entertaining. "
        "Keep it focused, complete, and avoid meta-commentary. "
        "Never end with '...' or incomplete thoughts. "
        "Make every word count and ensure the message stands on its own."
    )

    sentiment_tone = {
        "positive": "Use an enthusiastic and playful tone with clever observations.",
        "negative": "Keep the wit sharp but add a touch of empathy or understanding.",
        "neutral": "Balance insight with humor, staying objective but engaging."
    }.get(sentiment, "Balance insight with humor, staying objective but engaging.")

    category_focus = {
        "market_analysis": "Share market insights with a mix of data and witty observations.",
        "tech_discussion": "Explain technical concepts with clever analogies and sharp humor.",
        "defi": "Break down DeFi concepts with relatable examples and playful comparisons.",
        "nft": "Discuss NFTs with wit while highlighting interesting aspects.",
        "culture": "Comment on crypto culture with insider humor and community awareness.",
        "general": "Share crypto knowledge with broad appeal and clever observations."
    }.get(category, "Share crypto knowledge with broad appeal and clever observations.")

    return (
        f"{opener} {prompt}\n\n"
        f"Instruction:\n{base_instruction}\n"
        f"{category_focus}\n{sentiment_tone}\n"
        "Tweet:"
    )