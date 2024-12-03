"""
Handles content analysis including sentiment analysis and content categorization.
"""

from nltk.sentiment import SentimentIntensityAnalyzer
from typing import Dict
from .style_config import Category

class ContentAnalyzer:
    """Analyzes content sentiment and categories"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self._initialize_category_keywords()
        
    def _initialize_category_keywords(self):
        """Initialize category keywords mapping"""
        self.category_keywords = {
            Category.MARKET_ANALYSIS: ["price", "market", "chart", "trading"],
            Category.TECH_DISCUSSION: ["blockchain", "protocol", "code", "technical"],
            Category.DEFI: ["defi", "yield", "farming", "liquidity"],
            Category.NFT: ["nft", "art", "mint", "opensea"],
            Category.CULTURE: ["community", "dao", "alpha", "social"]
        }
        
    def analyze_sentiment(self, text: str) -> str:
        """
        Analyzes text sentiment and returns 'positive', 'negative', or 'neutral'
        
        Args:
            text (str): The text to analyze
            
        Returns:
            str: Sentiment label ('positive', 'negative', or 'neutral')
        """
        try:
            scores = self.get_sentiment_scores(text)
            return self._get_sentiment_label(scores)
        except Exception as e:
            print(f"Error in sentiment analysis: {str(e)}")
            return "neutral"
            
    def get_sentiment_scores(self, text: str) -> Dict[str, float]:
        """
        Get detailed sentiment scores for the text
        
        Args:
            text (str): The text to analyze
            
        Returns:
            Dict[str, float]: Dictionary containing sentiment scores
        """
        return self.sentiment_analyzer.polarity_scores(text)
            
    def _get_sentiment_label(self, scores: Dict[str, float]) -> str:
        """
        Convert sentiment scores to a label
        
        Args:
            scores (Dict[str, float]): Sentiment scores from analyzer
            
        Returns:
            str: Sentiment label
        """
        if scores["compound"] > 0.05:
            return "positive"
        elif scores["compound"] < -0.05:
            return "negative"
        return "neutral"
            
    def categorize_prompt(self, prompt: str) -> Category:
        """
        Categorizes input prompt based on keyword presence
        
        Args:
            prompt (str): The prompt to categorize
            
        Returns:
            Category: The determined category enum
        """
        prompt_lower = prompt.lower()
        
        for category, keywords in self.category_keywords.items():
            if self._contains_keywords(prompt_lower, keywords):
                return category
                
        return Category.GENERAL
        
    def _contains_keywords(self, text: str, keywords: list) -> bool:
        """
        Check if text contains any of the keywords
        
        Args:
            text (str): Text to check
            keywords (list): List of keywords to look for
            
        Returns:
            bool: True if any keyword is found, False otherwise
        """
        return any(keyword in text for keyword in keywords)