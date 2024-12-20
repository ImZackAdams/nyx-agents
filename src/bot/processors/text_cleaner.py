"""
Handles tweet text cleaning and formatting.
"""
import re
from typing import Optional, List, Tuple
from bot.processors.cleaning_patterns import CleaningPatterns

class TextCleaner:
    """Handles tweet text cleaning and formatting."""
    
    def __init__(self):
        """Initialize the TextCleaner with patterns."""
        self.patterns = CleaningPatterns()
    
    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        """
        Cleans and formats the text for consistent spacing and readability.
        Ensures all TetherBall coin references are converted to $TBALL.
        
        Args:
            text: Input text to clean
            
        Returns:
            Cleaned and formatted text
        """
        if not text:
            return ""
            
        cleaner = TextCleaner()
        return cleaner._clean_text_impl(text)
    
    def _clean_text_impl(self, text: str) -> str:
        """Implementation of the text cleaning process."""
        # Extract core content
        text = self._extract_core_content(text)
        
        # Apply all TBALL-related patterns
        text = self._apply_tball_patterns(text)
        
        # Apply formatting patterns
        text = self._apply_formatting(text)
        
        # Final cleanup
        text = self._apply_patterns(text, self.patterns.CLEANUP)
        text = self._final_cleanup(text)
        
        return text.strip()
    
    def _extract_core_content(self, text: str) -> str:
        """Extract the main content from text."""
        quote_match = re.search(r'"([^"]+)"', text)
        if quote_match:
            text = quote_match.group(1).strip()
        elif "Tweet:" in text:
            text = text.split("Tweet:")[-1].strip()
            
        text = text.split("\n")[0].strip()
        for cutoff in self.patterns.CUTOFF_PHRASES:
            text = text.split(cutoff)[0].strip()
            
        return text
    
    def _apply_tball_patterns(self, text: str) -> str:
        """Apply all TBALL-related patterns."""
        for pattern_group in [
            self.patterns.BASIC_TBALL,
            self.patterns.TBALL_VARIANTS,
            self.patterns.SYMBOL_VARIANTS,
            self.patterns.SOCIAL_VARIANTS,
            self.patterns.SPECIAL_CASES
        ]:
            text = self._apply_patterns(text, pattern_group)
        return text
    
    def _apply_formatting(self, text: str) -> str:
        """Apply all formatting-related patterns."""
        text = self._apply_patterns(text, self.patterns.FORMATTING)
        text = self._apply_patterns(text, self.patterns.CONTRACTIONS, flags=re.IGNORECASE)
        text = self._apply_patterns(text, self.patterns.PUNCTUATION)
        return text
    
    def _final_cleanup(self, text: str) -> str:
        """Perform final cleanup operations."""
        # Apply final cleanup patterns
        text = self._apply_patterns(text, self.patterns.FINAL_CLEANUP)
        text = self._apply_patterns(text, self.patterns.TEXT_STANDARDIZATION)
        
        if not text.endswith(('.', '!', '?')):
            text += '!'
            
        return text.strip()
    
    @staticmethod
    def _apply_patterns(text: str, patterns: List[Tuple[str, str]], flags: int = 0) -> str:
        """Apply a list of patterns to the text."""
        result = text
        for pattern, replacement in patterns:
            if callable(replacement):
                result = re.sub(pattern, replacement, result, flags=flags)
            else:
                result = re.sub(pattern, replacement, result, flags=flags)
        return result