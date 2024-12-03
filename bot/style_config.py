"""
Style configuration and categories for text processing.
"""

from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum, auto

class Category(Enum):
    """Enumeration of content categories"""
    MARKET_ANALYSIS = auto()
    TECH_DISCUSSION = auto()
    DEFI = auto()
    NFT = auto()
    CULTURE = auto()
    GENERAL = auto()

def get_default_emojis() -> Dict[str, List[str]]:
    return {
        'market_analysis': ["📈", "💰", "💎", "🚀", "💅"],
        'tech_discussion': ["💻", "⚡️", "🔧", "💅", "✨"],
        'defi': ["🏦", "💰", "💎", "✨", "💅"],
        'nft': ["🎨", "🖼️", "✨", "💅", "🌟"],
        'culture': ["🌐", "✨", "💅", "🌟", "🎭"],
        'general': ["✨", "💅", "🌟", "🚀", "💎"]
    }

def get_default_hashtags() -> Dict[str, List[str]]:
    return {
        'market_analysis': [
            "#AthenaTellsItLikeItIs", "#AthenaOnMarkets", "#MarketMoxie",
            "#ChartingWithAthena", "#TradingTruths", "#FinanceWithAthena",
            "#AthenaBreaksItDown", "#AthenaKnowsMarkets"
        ],
        'tech_discussion': [
            "#AthenaTellsItLikeItIs", "#TechTalkWithAthena", "#BlockchainWithAthena",
            "#CryptoClarity", "#AthenaCodes", "#Web3WithAthena", "#AthenaExplainsIt"
        ],
        'defi': [
            "#AthenaTellsItLikeItIs", "#DeFiDecoded", "#AthenaOnDeFi",
            "#ProtocolPerfection", "#LiquidityWithAthena", "#AthenaDeFiTea",
            "#DeFiByAthena", "#AthenaUnchains"
        ],
        'nft': [
            "#AthenaTellsItLikeItIs", "#NFTWithAthena", "#ArtWithAthena",
            "#MintTalkWithAthena", "#AthenaOnNFTs", "#BlockchainArtistry",
            "#NFTDecodedByAthena", "#AthenaArtAlpha"
        ],
        'culture': [
            "#AthenaTellsItLikeItIs", "#AthenaUnfiltered", "#CryptoCultureWithAthena",
            "#Web3Chronicles", "#AthenaDAO", "#AthenaOnCommunity",
            "#BlockchainStories", "#AthenaSharesTea"
        ],
        'general': [
            "#AthenaTellsItLikeItIs", "#AthenaSpeaks", "#BlockchainBanter",
            "#CryptoChatsWithAthena", "#AthenaSays", "#AthenaSpillsTheTea",
            "#AthenaOnWeb3", "#AthenaWisdom"
        ]
    }

def get_default_openers() -> List[str]:
    return [
        "👀 Tea alert!", "💅 Listen up!", "✨ Plot twist!",
        "💫 Spicy take incoming!", "🔥 Hot gossip!",
        "Hot take!", "Fun fact:", "Did you know?",
        "Newsflash!", "Heads up!", "Quick thought:",
        "🌶️ Controversial opinion:", "💎 Gem alert!"
    ]

def get_default_hooks() -> Dict[str, List[str]]:
    return {
        'market_analysis': ["Market tea:", "Chart check:", "Price watch:"],
        'tech_discussion': ["Tech tea:", "Protocol tea:", "Blockchain tea:"],
        'defi': ["DeFi tea:", "Yield tea:", "Protocol tea:"],
        'nft': ["NFT tea:", "Mint tea:", "Floor tea:"],
        'culture': ["Culture tea:", "DAO tea:", "Community tea:"],
        'general': ["Hot take:", "Tea time:", "Spill alert:"]
    }

def get_default_personality_markers() -> Dict[str, List[str]]:
    return {
        'sass': ["💅", "✨", "👀", "💫", "🌟"],
        'drama': ["🎭", "🎪", "🎯", "🎨", "🎮"],
        'tech': ["💻", "⚡️", "🔧", "🛠️", "💡"],
        'finance': ["💰", "💎", "🚀", "📈", "💹"]
    }

@dataclass
class StyleConfig:
    """Configuration for text styling elements"""
    emojis: Dict[str, List[str]] = field(default_factory=get_default_emojis)
    hashtags: Dict[str, List[str]] = field(default_factory=get_default_hashtags)
    openers: List[str] = field(default_factory=get_default_openers)
    hooks: Dict[str, List[str]] = field(default_factory=get_default_hooks)
    fallback_responses: List[str] = field(default_factory=lambda: [
        "✨ Crypto never sleeps, and neither do the opportunities! 💅",
        "💅 Another day in crypto – where the memes are hot and the takes are hotter! ✨",
        "🌟 Plot twist: crypto is just spicy math with memes! 💅 #CryptoTea"
    ])
    personality_markers: Dict[str, List[str]] = field(default_factory=get_default_personality_markers)
    incomplete_phrases: List[str] = field(default_factory=lambda: [
        "here's why", "here's the lowdown", "so what do we",
        "but wait", "what's your take", "share your",
        "meanwhile", "but first", "lets talk about"
    ])

    @classmethod
    def default(cls) -> 'StyleConfig':
        """Creates default style configuration"""
        return cls()