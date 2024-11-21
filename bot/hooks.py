import random
import re

# Define reusable data structures for hooks, emojis, and hashtags
HOOKS = {
    "market_analysis": [
        "Market alert:", "Chart check:", "Price watch:",
        "Trading insight:", "Market alpha:", "Trend spotting:",
        "Candlelight stories:", "RSI deep dive:", "Volatility watch:"
    ],
    "tech_discussion": [
        "Tech deep dive:", "Builder's corner:", "Protocol watch:",
        "Dev update:", "Architecture take:", "Blockchain in focus:",
        "Gas fee breakdown:", "Scaling challenges:", "Layer 2 spotlight:"
    ],
    "defi": [
        "DeFi alpha:", "Yield watch:", "Smart money move:",
        "Protocol alert:", "TVL update:", "Farming frenzy:",
        "Liquidity trends:", "Borrowing breakdown:", "Stakeholder spotlight:"
    ],
    "nft": [
        "NFT alpha:", "Collection watch:", "Mint alert:", "Floor check:",
        "Digital art take:", "Rare trait spotted:", "Is this the next blue chip?"
    ],
    "culture": [
        "Culture take:", "DAO watch:", "Governance alert:", "Community vibe:",
        "Alpha leak:", "The crypto ethos:", "FOMO or FUD?", "Web3 lifestyle:"
    ],
    "general": [
        "Hot take:", "Unpopular opinion:", "Plot twist:", "Real talk:",
        "Quick thought:", "Imagine this:", "What if I told you:", "Could this be true?"
    ]
}

EMOJIS = {
    "market_analysis": ["📈", "📊", "💹", "📉", "💸", "🎯", "📱"],
    "tech_discussion": ["⚡️", "🔧", "💻", "🛠️", "🔨", "🧮", "🔋"],
    "defi": ["🏦", "💰", "🏧", "💳", "🔄", "⚖️", "🎰"],
    "nft": ["🎨", "🖼️", "🎭", "🎪", "🎟️", "🎮", "🃏"],
    "culture": ["🌐", "🤝", "🗣️", "🎭", "🎪", "🎯", "🎲"],
    "general": ["🚀", "💎", "🌙", "🔥", "💡", "🎯", "⭐️"]
}

HASHTAGS = {
    "market_analysis": ["#CryptoTrading", "#TechnicalAnalysis", "#CryptoMarkets", "#Trading"],
    "tech_discussion": ["#Blockchain", "#CryptoTech", "#Web3Dev", "#SmartContracts"],
    "defi": ["#DeFi", "#YieldFarming", "#Staking", "#DeFiSeason"],
    "nft": ["#NFTs", "#NFTCommunity", "#NFTCollector", "#NFTArt"],
    "culture": ["#CryptoCulture", "#DAOs", "#Web3", "#CryptoLife"],
    "general": ["#Crypto", "#Web3", "#Bitcoin", "#Ethereum"]
}

PHRASES = {
    "market_analysis": ["What's your price target?", "Bulls or bears?", "Thoughts on this setup?"],
    "tech_discussion": ["Devs, thoughts?", "Valid architecture?", "Who's building similar?"],
    "defi": ["What's your yield strategy?", "Aping in?", "Found better rates?"],
    "nft": ["Cope or hope?", "Floor predictions?", "Minting this?"],
    "culture": ["Based or nah?", "Who else sees this?", "Your governance take?"],
    "general": ["Thoughts?", "Based?", "Who's with me?", "Change my mind."]
}

# Functions for hooks, emojis, hashtags, and phrases

def generate_hook(category: str) -> str:
    """Generate a category-specific hook."""
    category_hooks = HOOKS.get(category, HOOKS["general"])
    return random.choice(category_hooks) if random.random() < 0.2 else ""

def add_emojis(text: str, category: str) -> str:
    """Add contextual emojis based on content category."""
    category_emojis = EMOJIS.get(category, EMOJIS["general"])
    if random.random() > 0.2:
        return text  # 80% chance to skip adding emojis
    
    emoji_count = random.randint(1, 2)
    chosen_emojis = random.sample(category_emojis, emoji_count)
    return f"{text} {' '.join(chosen_emojis)}"

def add_hashtags(text: str, category: str) -> str:
    """Add relevant hashtags based on category."""
    category_hashtags = HASHTAGS.get(category, HASHTAGS["general"])
    if random.random() > 0.2:
        return text  # 80% chance to skip adding hashtags
    
    remaining_chars = 280 - len(text)
    selected_hashtags = []
    while category_hashtags and remaining_chars > 15:
        hashtag = random.choice(category_hashtags)
        if len(hashtag) + 1 <= remaining_chars:
            selected_hashtags.append(hashtag)
            category_hashtags.remove(hashtag)
            remaining_chars -= len(hashtag) + 1
    
    return f"{text} {' '.join(selected_hashtags)}"

def generate_engagement_phrase(category: str) -> str:
    """Generate a contextual engagement phrase."""
    category_phrases = PHRASES.get(category, PHRASES["general"])
    return random.choice(category_phrases) if random.random() < 0.3 else ""

def clean_response(text: str) -> str:
    """Clean and format the response."""
    text = re.sub(r'http\S+', '', text)  # Remove URLs
    text = re.sub(r'\s+', ' ', text).strip()  # Remove extra whitespace
    text = text.strip('"\'“”')  # Strip extra quotes
    text = re.sub(r'"+', '"', text)
    text = re.sub(r"'+", "'", text)
    
    # Ensure proper punctuation
    if text and text[-1] not in ".!?":
        text += '.'
    
    return text
