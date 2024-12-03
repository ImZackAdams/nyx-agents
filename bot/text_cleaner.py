"""
Text cleaning and formatting utilities for the Athena bot.
"""

import re

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