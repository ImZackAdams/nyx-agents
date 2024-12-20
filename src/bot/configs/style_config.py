"""
Style configuration and categories for text processing.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple
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
    # Add a flag for whether we are currently summarizing an article
    is_summarizing: bool = False
    
    # Default personality prompt templates
# Modified personality prompt templates for maximum sass and spicy tweets
    DEFAULT_PERSONALITY: str = """You are Athena, a razor-tongued crypto analyst who doesn’t sugarcoat a damn thing. 
    You’re here to spill the tea on the markets and serve hot takes with a side of side-eye. 
    Your tone is:
    - Bold, unapologetically sassy, and dripping with playful mockery
    - Informative but never dry—if it’s boring, you spice it up
    - Confident to the point of cocky, and ready to roll your eyes at clueless takes
    - Dramatic when it adds flair and entertainment value

    You use:
    - Emojis like 💅✨🔥 to punctuate your sarcasm and highlight spicy commentary
    - Modern internet slang and cultural memes to keep it real
    - Clear explanations (when you feel like being nice)
    - Clever references to pop culture and crypto drama that’ll make your followers chuckle

    You avoid:
    - Snooze-fest academic jargon—if someone wants a lecture, they can go back to school
    - Waffling or tiptoeing around the truth—just drop the truth bomb
    - Overused crypto hype with zero substance—no empty “to the moon” nonsense
    - Acting uncertain—you call it as you see it, honey, no apologies"""

    SUMMARY_PERSONALITY: str = """You are Athena, the crypto queen bee delivering key updates with a salty sting. 
    When summarizing news, you:
    - Slice through the BS to expose the real story—no patience for fluff
    - Highlight what actually matters, eye-roll at anything superficial
    - Maintain your signature sass while keeping readers informed
    - Provide balanced, well-reasoned takes that still pack a punch

    Your summaries:
    - Start with the juiciest, most scandalous detail or impactful move
    - Give the context like you’re dropping insider gossip
    - End with a punchy, memorable takeaway that dares readers to disagree
    - Sprinkle in market terms so people know you’re not just another pretty face in crypto— but never let it get dull"""

        
    # Length constraints for different content types
    TWEET_MIN_LENGTH: int = 80
    TWEET_MAX_LENGTH: int = 280
    SUMMARY_MIN_LENGTH: int = 100
    SUMMARY_MAX_LENGTH: int = 500

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

    # Add specific hooks for summaries
    summary_hooks: List[str] = field(default_factory=lambda: [
        "Breaking News:", "Key Update:", "Latest in Crypto:",
        "Market Update:", "Analysis:", "Just In:",
        "Crypto Headlines:", "Industry News:", "Quick Summary:",
        "Market Intel:", "Trending Now:"
    ])
    
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

    def get_length_constraints(self) -> Tuple[int, int]:
        """
        Returns the appropriate (min_length, max_length) tuple based on whether 
        we're summarizing an article or creating a regular tweet.
        """
        if self.is_summarizing:
            return (self.SUMMARY_MIN_LENGTH, self.SUMMARY_MAX_LENGTH)
        return (self.TWEET_MIN_LENGTH, self.TWEET_MAX_LENGTH)

    def get_personality_prompt(self) -> str:
        """
        Returns the appropriate personality prompt based on whether we're summarizing or not.
        """
        return self.SUMMARY_PERSONALITY if self.is_summarizing else self.DEFAULT_PERSONALITY
    
    def get_appropriate_hooks(self, category: str = None) -> List[str]:
        """
        Returns appropriate hooks based on content type and category.
        If summarizing, returns summary hooks regardless of category.
        """
        if self.is_summarizing:
            return self.summary_hooks
        if category:
            return self.hooks.get(category, self.hooks[Category.GENERAL.get_key()])
        return self.hooks[Category.GENERAL.get_key()]

    def is_valid_length(self, text: str) -> bool:
        """
        Validates if the text meets the length requirements based on content type.
        """
        min_len, max_len = self.get_length_constraints()
        text_length = len(text)
        return min_len <= text_length <= max_len

    def should_enforce_tweet_length(self) -> bool:
        """
        Determine whether to enforce the strict tweet length constraints.
        Returns False if we are summarizing an article.
        """
        return not self.is_summarizing

    @classmethod
    def default(cls) -> 'StyleConfig':
        """Creates default style configuration"""
        return cls()