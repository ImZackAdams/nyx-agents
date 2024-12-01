import random
import re

HOOKS = {
    "market_analysis": ["Market alert:", "Chart check:", "Price watch:", "Trading insight:", "Trend spotting:"],
    "tech_discussion": ["Tech deep dive:", "Protocol watch:", "Blockchain in focus:", "Scaling challenges:"],
    "defi": ["DeFi alpha:", "Yield watch:", "Protocol alert:", "TVL update:"],
    "nft": ["NFT alpha:", "Mint alert:", "Floor check:", "Rare trait spotted:"],
    "culture": ["Culture take:", "DAO watch:", "Community vibe:", "The crypto ethos:"],
    "general": ["Hot take:", "Unpopular opinion:", "Plot twist:", "Real talk:"]
}

EMOJIS = {
    "market_analysis": ["📈", "📊", "💹", "📉"],
    "tech_discussion": ["⚡️", "🔧", "💻", "🛠️"],
    "defi": ["🏦", "💰", "🏧"],
    "nft": ["🎨", "🖼️", "🎭"],
    "culture": ["🌐", "🤝", "🗣️"],
    "general": ["🚀", "💎", "🌙"]
}

HASHTAGS = {
    "market_analysis": ["#CryptoTrading", "#TechnicalAnalysis", "#CryptoMarkets"],
    "tech_discussion": ["#Blockchain", "#CryptoTech", "#Web3Dev"],
    "defi": ["#DeFi", "#YieldFarming", "#Staking"],
    "nft": ["#NFTs", "#NFTCommunity", "#NFTCollector"],
    "culture": ["#CryptoCulture", "#DAOs", "#Web3"],
    "general": ["#Crypto", "#Web3", "#Bitcoin"]
}


def get_category_data(category: str, data_dict: dict) -> list:
    """Fetch data for a category or default to general."""
    return data_dict.get(category, data_dict["general"])


def generate_hook(category: str, prob: float = 0.1) -> str:
    """Generate a hook with a specified probability."""
    if random.random() > prob:
        return ""
    return random.choice(get_category_data(category, HOOKS))


def add_emojis_and_hashtags(text: str, category: str) -> str:
    """Add emojis and/or hashtags with a combined 20% probability."""
    if random.random() <= 0.2:  # 20% chance for either emojis or hashtags
        add_emoji = random.choice([True, False])  # Randomly decide whether to add an emoji
        add_hashtag = not add_emoji or random.choice([True, False])  # Ensure at least one is added

        if add_emoji:
            emojis = random.sample(get_category_data(category, EMOJIS), random.randint(1, 2))
            text = f"{text} {' '.join(emojis)}"

        if add_hashtag:
            hashtags = random.sample(get_category_data(category, HASHTAGS), random.randint(1, 3))
            text = f"{text} {' '.join(hashtags)}"

    return text



def clean_response(text: str) -> str:
    """Clean the generated response."""
    text = re.sub(r'http\S+', '', text)  # Remove URLs
    text = re.sub(r'\s+', ' ', text).strip()  # Remove extra whitespace
    return text.rstrip('"\'.,!?') + '.'
