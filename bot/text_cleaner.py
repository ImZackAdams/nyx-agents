import re
from typing import Optional

class TextCleaner:
    """Handles tweet text cleaning and formatting."""
    
    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        """
        Cleans and formats the text for consistent spacing and readability.
        
        Args:
            text: Input text to clean
            
        Returns:
            str: Cleaned and formatted text
        """
        if not text:
            return ""
            
        # Extract actual tweet content if it contains the "Tweet:" prefix
        if "Tweet:" in text:
            text = text.split("Tweet:")[-1].strip()
            text = text.split('\n')[0].strip()
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Remove all types of quotation marks
        text = re.sub(r'["“”‘’]', '', text)
        
        # Fix punctuation spacing
        text = re.sub(r'\s+([.,!?])', r'\1', text)  # Fix spacing before punctuation
        text = re.sub(r'([.,!?])\s+', r'\1 ', text)  # Space after punctuation
        
        # Fix common contractions
        text = re.sub(
            r"(?<!\w)(dont|wont|im|ive|its|lets|youre|whats|cant|ill|id)(?!\w)", 
            lambda m: m.group(1).capitalize(), 
            text, 
            flags=re.IGNORECASE
        )
        
        # Clean punctuation and emojis
        text = re.sub(r'([!?.]){2,}', r'\1', text)  # Reduce repeated punctuation
        text = re.sub(r'(\w)([💅✨👏🌟🚀💎🔓🎨⚡️🔧])', r'\1 \2', text)  # Space before emojis
        text = re.sub(r'(?<!\s)([#@])', r' \1', text)  # Space before hashtags/mentions
        
        # Limit hashtags to 2
        if text.count('#') > 2:
            hashtags = re.findall(r'#\w+', text)
            main_text = re.sub(r'#\w+', '', text).strip()
            text = f"{main_text} {' '.join(hashtags[:2])}"
            
        # Remove any remaining generated metadata or instructions
        text = re.sub(r'\[.*?\]', '', text)  # Remove square bracket content
        text = re.sub(r'@\w+\s?', '', text)  # Remove generated usernames
        
        # Remove leading/trailing quotes
        text = text.strip(' "\'')
        
        # Ensure proper ending
        if not text.endswith(('.', '!', '?')):
            text += '!'
            
        return text.strip()

# Test cases
def run_tests():
    examples = [
        ' "Tweet: Hello, world!" ',  # Leading/trailing quotes and "Tweet:" prefix
        "dont you think its amazing?",  # Common contractions
        '"Just a tweet with stray quotes"',  # Stray quotes
        "Bitcoin is amazing🚀",  # Emoji handling
        "Crypto is great! #BTC #ETH #DOGE",  # Hashtag limiting
        "This is a test [REMOVE_ME] @user123",  # Metadata removal
        "This needs punctuation",  # Adding punctuation
        "This     has   extra spaces.  ",  # Extra spaces
        None,  # Empty input
    ]

    for i, example in enumerate(examples, start=1):
        cleaned_text = TextCleaner.clean_text(example)
        print(f"Test Case {i}:")
        print(f"Original: {example}")
        print(f"Cleaned: {cleaned_text}")
        print("---")

if __name__ == "__main__":
    run_tests()
