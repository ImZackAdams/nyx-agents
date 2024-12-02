"""
Text processing and enhancement utilities for the Athena bot.
Handles text analysis, categorization, and response formatting with personality traits.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from nltk.sentiment import SentimentIntensityAnalyzer
import random
import re
from collections import deque
from enum import Enum, auto

class Category(Enum):
    """Enumeration of content categories"""
    MARKET_ANALYSIS = auto()
    TECH_DISCUSSION = auto()
    DEFI = auto()
    NFT = auto()
    CULTURE = auto()
    GENERAL = auto()

@dataclass
class StyleConfig:
    """Configuration for text styling elements"""
    emojis: Dict[str, List[str]]
    hashtags: Dict[str, List[str]]
    openers: List[str]
    hooks: Dict[str, List[str]]
    fallback_responses: List[str]
    personality_markers: Dict[str, List[str]]
    incomplete_phrases: List[str]

    @classmethod
    def default(cls) -> 'StyleConfig':
        """Creates default style configuration"""
        return cls(
            emojis={
                'market_analysis': ["📈", "💰", "💎", "🚀", "💅"],
                'tech_discussion': ["💻", "⚡️", "🔧", "💅", "✨"],
                'defi': ["🏦", "💰", "💎", "✨", "💅"],
                'nft': ["🎨", "🖼️", "✨", "💅", "🌟"],
                'culture': ["🌐", "✨", "💅", "🌟", "🎭"],
                'general': ["✨", "💅", "🌟", "🚀", "💎"]
            },
            hashtags={
                'market_analysis': ["#CryptoTea", "#TradingGossip", "#MarketDrama"],
                'tech_discussion': ["#TechTea", "#BlockchainGossip", "#CryptoTech"],
                'defi': ["#DeFiTea", "#YieldGossip", "#DeFiDrama"],
                'nft': ["#NFTea", "#NFTGossip", "#CollectionDrama"],
                'culture': ["#CryptoTea", "#Web3Drama", "#CultureGossip"],
                'general': ["#CryptoTea", "#Web3Gossip", "#BlockchainLife"]
            },
            openers=[
                "👀 Tea alert!", "💅 Listen up!", "✨ Plot twist!",
                "💫 Spicy take incoming!", "🔥 Hot gossip!",
                "Hot take!", "Fun fact:", "Did you know?",
                "Newsflash!", "Heads up!", "Quick thought:",
                "🌶️ Controversial opinion:", "💎 Gem alert!"
            ],
            hooks={
                'market_analysis': ["Market tea:", "Chart check:", "Price watch:"],
                'tech_discussion': ["Tech tea:", "Protocol tea:", "Blockchain tea:"],
                'defi': ["DeFi tea:", "Yield tea:", "Protocol tea:"],
                'nft': ["NFT tea:", "Mint tea:", "Floor tea:"],
                'culture': ["Culture tea:", "DAO tea:", "Community tea:"],
                'general': ["Hot take:", "Tea time:", "Spill alert:"]
            },
            fallback_responses=[
                "✨ Crypto never sleeps, and neither do the opportunities! 💅",
                "💅 Another day in crypto – where the memes are hot and the takes are hotter! ✨",
                "🌟 Plot twist: crypto is just spicy math with memes! 💅 #CryptoTea"
            ],
            personality_markers={
                'sass': ["💅", "✨", "👀", "💫", "🌟"],
                'drama': ["🎭", "🎪", "🎯", "🎨", "🎮"],
                'tech': ["💻", "⚡️", "🔧", "🛠️", "💡"],
                'finance': ["💰", "💎", "🚀", "📈", "💹"]
            },
            incomplete_phrases=[
                "here's why", "here's the lowdown", "so what do we",
                "but wait", "what's your take", "share your",
                "meanwhile", "but first", "lets talk about"
            ]
        )

class TextCleaner:
    """Handles text cleaning and formatting"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Cleans and formats text for consistency"""
        if not text:
            return ""
            
        # Initial cleanup
        text = text.strip('"\'').strip()
        
        # Remove placeholder content
        text = re.sub(r'\?\s*([.,!?]|$)', r'\1', text)  # remove ? placeholders
        text = re.sub(r'\[\s*[^]]*\]', '', text)  # remove [explanations]
        text = re.sub(r'\s{2,}', ' ', text)  # normalize multiple spaces
        
        # Fix basic formatting
        text = re.sub(r'\.{3,}', '...', text)  # fix ellipsis
        text = re.sub(r'\s*-\s*', '-', text)  # normalize dashes
        
        # Handle crypto terms
        text = re.sub(r'HODL(?:ING|ERS?)?', 'hodl', text, flags=re.IGNORECASE)
        text = re.sub(r'(?:DYOR?|DO YOUR OWN RESEARCH)', 'DYOR', text, flags=re.IGNORECASE)
        text = re.sub(r'Po[Ww]\s*/?[Ss]?', 'PoW', text)
        
        # Fix punctuation
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        text = re.sub(r'([.,!?;:])\s+', r'\1 ', text)
        text = re.sub(r'([!?.]){2,}', r'\1', text)
        text = re.sub(r'&', 'and', text)
        
        # Remove unwanted content
        text = re.sub(r'@\w+', '', text)  # @ mentions
        text = re.sub(r'\$[A-Z]+', '', text)  # ticker symbols
        text = re.sub(r'["""\']', '', text)  # quotes
        text = re.sub(r'http\S+', '', text)  # URLs
        
        # Final cleanup and proper ending
        text = text.strip()
        if not text.endswith(('!', '?', '.')):
            text += '!'
            
        return text.strip()

class ContentAnalyzer:
    """Analyzes content sentiment and categories"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
    def analyze_sentiment(self, text: str) -> str:
        """Analyzes text sentiment"""
        try:
            scores = self.sentiment_analyzer.polarity_scores(text)
            if scores["compound"] > 0.05:
                return "positive"
            elif scores["compound"] < -0.05:
                return "negative"
            return "neutral"
        except Exception:
            return "neutral"
            
    def categorize_prompt(self, prompt: str) -> Category:
        """Categorizes input prompt"""
        keywords = {
            Category.MARKET_ANALYSIS: ["price", "market", "chart", "trading"],
            Category.TECH_DISCUSSION: ["blockchain", "protocol", "code", "technical"],
            Category.DEFI: ["defi", "yield", "farming", "liquidity"],
            Category.NFT: ["nft", "art", "mint", "opensea"],
            Category.CULTURE: ["community", "dao", "alpha", "social"]
        }
        
        prompt_lower = prompt.lower()
        for category, category_keywords in keywords.items():
            if any(keyword in prompt_lower for keyword in category_keywords):
                return category
        return Category.GENERAL

class TextProcessor:
    """Main text processing class with style management"""
    
    def __init__(self, style_config: StyleConfig = None, max_history: int = 10):
        self.config = style_config or StyleConfig.default()
        self.cleaner = TextCleaner()
        self.analyzer = ContentAnalyzer()
        self.recent_emojis = deque(maxlen=max_history)
        self.recent_hashtags = deque(maxlen=max_history)
        self.recent_openers = deque(maxlen=max_history)
        
    def process_tweet(self, prompt: str, text: str) -> str:
        """Process and style tweet content"""
        try:
            # Extract and clean tweet
            tweet = text.split("Tweet:")[-1].strip().split('\n')[0].strip()
            tweet = self.cleaner.clean_text(tweet)
            
            if len(tweet) < 20:
                return random.choice(self.config.fallback_responses)
                
            # Handle length constraints
            if len(tweet) > 240:
                tweet = self._truncate_tweet(tweet)
                
            # Add styling
            category = self.analyzer.categorize_prompt(prompt)
            tweet = self._add_style(tweet, category.name.lower())
            
            return tweet
            
        except Exception:
            return random.choice(self.config.fallback_responses)
            
    def _truncate_tweet(self, tweet: str) -> str:
        """Smartly truncates tweet to fit length limit with more natural flow"""
        sentences = re.split(r'(?<=[.!?])\s+', tweet)
        result = []
        current_length = 0
        
        for sentence in sentences:
            if current_length + len(sentence) <= 237:
                result.append(sentence)
                current_length += len(sentence) + 1
            else:
                # Break when adding another sentence exceeds the limit
                break
        
        # Add ellipsis if truncation occurs
        truncated_tweet = ' '.join(result).strip()
        if len(truncated_tweet) < len(tweet):
            truncated_tweet += '...'
        
        return truncated_tweet

        
    def _add_style(self, text: str, category: str) -> str:
        """Adds styling elements with reduced aggressiveness"""
        if len(text) >= 220:
            return text  # No styling for very long tweets
        
        # Optional: only clean redundant hashtags
        hashtags_to_clean = re.findall(r'#\w+', text)
        if len(hashtags_to_clean) > 1:
            text = re.sub(r'#\w+', '', text, count=len(hashtags_to_clean) - 1)
        
        text = text.strip()
        
        # Add emoji if missing a personality marker
        if not any(char in text for char in ''.join(self.config.personality_markers['sass'])):
            emoji = self._select_emoji(category)
            text = self._place_emoji(text, emoji)
        
        # Add a hashtag if space allows
        if len(text) <= 200:
            hashtag = self._select_hashtag(category)
            if hashtag:
                text = f"{text} {hashtag}"
        
        # Final cleanup
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s+([.,!?])', r'\1', text)
        
        return text.strip()

        
    def _select_emoji(self, category: str) -> str:
        """Selects appropriate emoji based on category and history"""
        available = [e for e in self.config.emojis[category] 
                    if e not in self.recent_emojis]
        if not available:
            available = self.config.emojis[category]
            
        emoji = random.choice(available)
        self.recent_emojis.append(emoji)
        return emoji
        
    def _select_hashtag(self, category: str) -> Optional[str]:
        """Selects appropriate hashtag based on category and history"""
        available = [t for t in self.config.hashtags[category] 
                    if t not in self.recent_hashtags]
        if not available:
            return None
            
        hashtag = random.choice(available)
        self.recent_hashtags.append(hashtag)
        return hashtag
        
    def _place_emoji(self, text: str, emoji: str) -> str:
        """Determines emoji placement in text"""
        placement = random.random()
        if placement < 0.3:
            return f"{emoji} {text}"
        elif placement < 0.7:
            return f"{text} {emoji}"
        return text