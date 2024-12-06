import re
from typing import Optional

class TextCleaner:
    """Handles tweet text cleaning and formatting."""
    
    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        """
        Cleans and formats the text for consistent spacing and readability.
        Ensures all TetherBall coin references are converted to $TBALL.
        """
        if not text:
            return ""
            
        # First extract the core tweet content
        quote_match = re.search(r'"([^"]+)"', text)
        if quote_match:
            text = quote_match.group(1).strip()
        elif "Tweet:" in text:
            text = text.split("Tweet:")[-1].strip()
            
        # Take only the meaningful content before any meta text
        text = text.split("\n")[0].strip()
        for cutoff in ["Note:", "Stay informed", "Here's MY", "Your response", "This response"]:
            text = text.split(cutoff)[0].strip()
        
        # Phase 1: Handle all ticker variations
        ticker_patterns = [
            # Basic variants
            (r'TetherBallCoin(?:\'s)?', '$TBALL'),
            (r'Tetherball[Cc]oin(?:\'s)?', '$TBALL'),
            (r'TETHERBALLCOIN(?:\'S)?', '$TBALL'),
            (r'tetherballcoin(?:\'s)?', '$TBALL'),
            
            # TBall variants
            (r'[Tt][Bb]all(?:\'s)?', '$TBALL'),
            (r'[Tt][Bb]alls', '$TBALL'),
            (r'TBALL(?:\'S)?', '$TBALL'),
            (r'TBall', '$TBALL'),
            (r'T-Ball', '$TBALL'),
            
            # Multiple dollar signs
            (r'\${2,}TBALL', '$TBALL'),
            (r'\${2,}[Tt]ball', '$TBALL'),
            (r'\${1,}tblll\${1,}', '$TBALL'),
            
            # Hash variants
            (r'#[Tt]ball', '$TBALL'),
            (r'#TBALL', '$TBALL'),
            (r'#\$+[Tt]ball', '$TBALL'),
            (r'#[Bb]alls?\b', '$TBALL'),
            
            # At mentions
            (r'@[Tt]etherballcoin', '$TBALL'),
            (r'@[Tt]ball', '$TBALL'),
            
            # Parenthetical forms
            (r'TBall\s*\(\s*TBALL\s*\)', '$TBALL'),
            (r'TetherBallCoin\s*\(\s*TBALL\s*\)', '$TBALL'),
            (r'TetherBallCoin\s*\(\s*\$TBALL\s*\)', '$TBALL'),
            
            # Nickname variants
            (r'[Tt]ethy(?:\'s)?', '$TBALL'),
            (r'[Tt]ball-?[Cc]oin', '$TBALL'),
            
            # Special cases
            (r'TBCC', '$TBALL'),
            (r'T-Balls', '$TBALL'),
            (r'\$Tball', '$TBALL'),  # Fix case
            (r'\$TBALL[sS]', '$TBALL'),  # Remove plurals
        ]
        
        # Apply all ticker replacements
        for pattern, replacement in ticker_patterns:
            text = re.sub(pattern, replacement, text)
        
        # Phase 2: Clean up formatting
        # Remove special characters and normalize spacing
        text = re.sub(r'[☽♄✦⁂]', '', text)  # Remove astrological symbols
        text = re.sub(r'\d️?[\u20e3⃣]?\s*[).]\s*', '', text)  # Remove list markers
        text = ' '.join(text.split())  # Normalize whitespace
        
        # Fix contractions and capitalization
        text = re.sub(
            r"(?<!\w)(dont|wont|im|ive|its|lets|youre|whats|cant|ill|id)(?!\w)", 
            lambda m: m.group(1).capitalize(), 
            text, 
            flags=re.IGNORECASE
        )
        
        # Clean up punctuation and spacing
        text = re.sub(r'([!?.]){2,}', r'\1', text)  # Remove repeated punctuation
        text = re.sub(r'\s+([.,!?])', r'\1', text)  # Fix spacing before punctuation
        text = re.sub(r'([.,!?])\s+', r'\1 ', text)  # Fix spacing after punctuation
        text = re.sub(r'\s+', ' ', text)  # Normalize spaces
        
        # Phase 3: Final cleanup
        # Remove any remaining metadata or unwanted elements
        text = re.sub(r'\[.*?\]', '', text)  # Remove square bracket content
        text = re.sub(r'@\w+\s?', '', text)  # Remove @ mentions
        
        # Ensure proper ticker formatting one last time
        text = re.sub(r'\$TBALL[sS]\b', '$TBALL', text)
        text = re.sub(r'\$Tball\b', '$TBALL', text, flags=re.IGNORECASE)
        text = re.sub(r'(\$TBALL)\s+', r'\1 ', text)
        
        # Remove quotes and extra spaces
        text = text.strip(' "\'')
        
        # Ensure proper ending
        if not text.endswith(('.', '!', '?')):
            text += '!'
            
        return text.strip()

# Comprehensive test cases
def run_tests():
    test_cases = [
        # Basic forms
        "TetherBallCoin is amazing!",
        "Just bought some $$$TBALL!",
        "Love my TBalls investment!",
        
        # Complex forms
        "TetherBallCoin (TBALL) to the moon!",
        "#$$$TBALL ($ #Balls) is pumping!",
        "$$tblll$$ making moves!",
        
        # Mixed cases with special characters
        "🚀 TBalls on fire 🔥 & TetherBallCoin (TBALL) mooning!",
        "1️⃣ Invest in TBalls ⏰ 2️⃣ HODL ☽",
        "@tetherballcoin & #TBALL working together!",
        
        # Nicknames and variants
        "Tethy's making progress!",
        "T-Balls Coding Club (TBCC) update",
        "TBallCoin's ecosystem growing!"
    ]

    for i, test in enumerate(test_cases, 1):
        cleaned = TextCleaner.clean_text(test)
        print(f"\nTest {i}:")
        print(f"Input:  {test}")
        print(f"Output: {cleaned}")
        print(f"$TBALL present: {'$TBALL' in cleaned}")
        print("-" * 50)

if __name__ == "__main__":
    run_tests()