"""
Style configuration and categories for text processing.
"""

from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class Category(Enum):
    """Enumeration of content categories"""
    MARKET_ANALYSIS = "market_analysis"
    TECH_DISCUSSION = "tech_discussion"
    DEFI = "defi"
    NFT = "nft"
    CULTURE = "culture"
    GENERAL = "general"
    
    def get_key(self) -> str:
        """Get the string key for dictionary lookups"""
        return self.value

@dataclass
class StyleConfig:
    """Configuration for text styling elements"""
    emojis: Dict[str, List[str]] = field(default_factory=lambda: {
        Category.MARKET_ANALYSIS.get_key(): ["📈", "💰", "💎", "🚀", "💅"],
        Category.TECH_DISCUSSION.get_key(): ["💻", "⚡️", "🔧", "💅", "✨"],
        Category.DEFI.get_key(): ["🏦", "💰", "💎", "✨", "💅"],
        Category.NFT.get_key(): ["🎨", "🖼️", "✨", "💅", "🌟"],
        Category.CULTURE.get_key(): ["🌐", "✨", "💅", "🌟", "🎭"],
        Category.GENERAL.get_key(): ["✨", "💅", "🌟", "🚀", "💎"]
    })
    
    hashtags: Dict[str, List[str]] = field(default_factory=lambda: {
        Category.MARKET_ANALYSIS.get_key(): [
            "#AthenaTellsItLikeItIs", "#AthenaOnMarkets", "#MarketMoxie",
            "#ChartingWithAthena", "#TradingTruths", "#FinanceWithAthena",
            "#AthenaBreaksItDown", "#AthenaKnowsMarkets"
        ],
        Category.TECH_DISCUSSION.get_key(): [
            "#AthenaTellsItLikeItIs", "#TechTalkWithAthena", "#BlockchainWithAthena",
            "#CryptoClarity", "#AthenaCodes", "#Web3WithAthena", "#AthenaExplainsIt"
        ],
        Category.DEFI.get_key(): [
            "#AthenaTellsItLikeItIs", "#DeFiDecoded", "#AthenaOnDeFi",
            "#ProtocolPerfection", "#LiquidityWithAthena", "#AthenaDeFiTea",
            "#DeFiByAthena", "#AthenaUnchains"
        ],
        Category.NFT.get_key(): [
            "#AthenaTellsItLikeItIs", "#NFTWithAthena", "#ArtWithAthena",
            "#MintTalkWithAthena", "#AthenaOnNFTs", "#BlockchainArtistry",
            "#NFTDecodedByAthena", "#AthenaArtAlpha"
        ],
        Category.CULTURE.get_key(): [
            "#AthenaTellsItLikeItIs", "#AthenaUnfiltered", "#CryptoCultureWithAthena",
            "#Web3Chronicles", "#AthenaDAO", "#AthenaOnCommunity",
            "#BlockchainStories", "#AthenaSharesTea"
        ],
        Category.GENERAL.get_key(): [
            "#AthenaTellsItLikeItIs", "#AthenaSpeaks", "#BlockchainBanter",
            "#CryptoChatsWithAthena", "#AthenaSays", "#AthenaSpillsTheTea",
            "#AthenaOnWeb3", "#AthenaWisdom"
        ]
    })
    
    openers: List[str] = field(default_factory=lambda: [
        "👀 Tea alert!", "💅 Listen up!", "✨ Plot twist!",
        "💫 Spicy take incoming!", "🔥 Hot gossip!",
        "Hot take!", "Fun fact:", "Did you know?",
        "Newsflash!", "Heads up!", "Quick thought:",
        "🌶️ Controversial opinion:", "💎 Gem alert!"
    ])
    
    hooks: Dict[str, List[str]] = field(default_factory=lambda: {
        Category.MARKET_ANALYSIS.get_key(): ["Market tea:", "Chart check:", "Price watch:"],
        Category.TECH_DISCUSSION.get_key(): ["Tech tea:", "Protocol tea:", "Blockchain tea:"],
        Category.DEFI.get_key(): ["DeFi tea:", "Yield tea:", "Protocol tea:"],
        Category.NFT.get_key(): ["NFT tea:", "Mint tea:", "Floor tea:"],
        Category.CULTURE.get_key(): ["Culture tea:", "DAO tea:", "Community tea:"],
        Category.GENERAL.get_key(): ["Hot take:", "Tea time:", "Spill alert:"]
    })
    
    personality_markers: Dict[str, List[str]] = field(default_factory=lambda: {
        'sass': ["💅", "✨", "👀", "💫", "🌟"],
        'drama': ["🎭", "🎪", "🎯", "🎨", "🎮"],
        'tech': ["💻", "⚡️", "🔧", "🛠️", "💡"],
        'finance': ["💰", "💎", "🚀", "📈", "💹"]
    })
    
    fallback_responses: List[str] = field(default_factory=lambda: [
        "✨ Crypto never sleeps, and neither do the opportunities! 💅",
        "💅 Another day in crypto – where the memes are hot and the takes are hotter! ✨",
        "🌟 Plot twist: crypto is just spicy math with memes! 💅 #CryptoTea"
    ])
    
    incomplete_phrases: List[str] = field(default_factory=lambda: [
        "here's why", "here's the lowdown", "so what do we",
        "but wait", "what's your take", "share your",
        "meanwhile", "but first", "lets talk about"
    ])

    @classmethod
    def default(cls) -> 'StyleConfig':
        """Creates default style configuration"""
        return cls()