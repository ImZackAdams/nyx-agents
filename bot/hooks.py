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


def generate_hook(category: str) -> str:
    return random.choice(HOOKS.get(category, HOOKS["general"]))


def add_emojis(text: str, category: str) -> str:
    if random.random() > 0.8:
        return text
    emojis = random.sample(EMOJIS.get(category, EMOJIS["general"]), random.randint(1, 2))
    return f"{text} {' '.join(emojis)}"


def add_hashtags(text: str, category: str) -> str:
    if random.random() > 0.8:
        return text
    hashtags = random.sample(HASHTAGS.get(category, HASHTAGS["general"]), random.randint(1, 3))
    return f"{text} {' '.join(hashtags)}"


def clean_response(text: str) -> str:
    text = re.sub(r'http\S+', '', text)  # Remove URLs
    text = re.sub(r'\s+', ' ', text).strip()  # Remove extra whitespace
    return text.rstrip('"\'.,!?') + '.'
