"""
Patterns used for text cleaning and formatting, ensuring ALL hashtags are removed.
"""

import re
from dataclasses import dataclass

@dataclass
class CleaningPatterns:
    """Container for all text cleaning patterns"""
    
    # =====================================
    # 1. Basic TBALL variants
    # =====================================
    BASIC_TBALL = [
        (r'TetherBallCoin(?:\'s)?', '$TBALL'),
        (r'Tetherball[Cc]oin(?:\'s)?', '$TBALL'),
        (r'TETHERBALLCOIN(?:\'S)?', '$TBALL'),
        (r'tetherballcoin(?:\'s)?', '$TBALL'),
    ]
    
    # =====================================
    # 2. TBall name variants
    # =====================================
    TBALL_VARIANTS = [
        (r'[Tt][Bb]all(?:\'s)?', '$TBALL'),
        (r'[Tt][Bb]alls', '$TBALL'),
        (r'TBALL(?:\'S)?', '$TBALL'),
        (r'TBall', '$TBALL'),
        (r'T-Ball', '$TBALL'),
    ]
    
    # =====================================
    # 3. Symbol variants
    # =====================================
    SYMBOL_VARIANTS = [
        (r'\${2,}TBALL', '$TBALL'),
        (r'\${2,}[Tt]ball', '$TBALL'),
        (r'\${1,}tblll\${1,}', '$TBALL'),
    ]
    
    # =====================================
    # 4. Social media variants
    #    (Previous patterns replaced some hashtags with $TBALL,
    #     but we want to remove *all* hashtags. So we comment them out
    #     or remove them entirely.)
    # =====================================
    SOCIAL_VARIANTS = [
        # (r'#[Tt]ball', '$TBALL'),
        # (r'#TBALL', '$TBALL'),
        # (r'#\$+[Tt]ball', '$TBALL'),
        # (r'#[Bb]alls?\b', '$TBALL'),
        (r'@[Tt]etherballcoin', '$TBALL'),
        (r'@[Tt]ball', '$TBALL'),
    ]
    
    # =====================================
    # 5. Remove ALL hashtags (no matter what)
    # =====================================
    REMOVE_ALL_HASHTAGS = [
        (r'#\S+', ''),  # Any '#' plus non-whitespace chars -> remove
    ]
    
    # =====================================
    # 6. Special cases
    # =====================================
    SPECIAL_CASES = [
        (r'TBall\s*\(\s*TBALL\s*\)', '$TBALL'),
        (r'TetherBallCoin\s*\(\s*TBALL\s*\)', '$TBALL'),
        (r'TetherBallCoin\s*\(\s*\$TBALL\s*\)', '$TBALL'),
        (r'[Tt]ethy(?:\'s)?', '$TBALL'),
        (r'[Tt]ball-?[Cc]oin', '$TBALL'),
        (r'TBCC', '$TBALL'),
        (r'T-Balls', '$TBALL'),
        (r'\$Tball', '$TBALL'),
        (r'\$TBALL[sS]', '$TBALL'),
    ]
    
    # =====================================
    # 7. Formatting patterns
    # =====================================
    FORMATTING = [
        (r'[☽♄✦⁂]', ''),    # Remove astrological symbols
        (r'\d️?[\u20e3⃣]?\s*[).]\s*', ''),  # Remove list markers
        (r'\s+', ' '),      # Normalize whitespace
    ]
    
    # =====================================
    # 8. Contraction fixes
    # =====================================
    CONTRACTIONS = [
        (r"(?<!\w)(dont|wont|im|ive|its|lets|youre|whats|cant|ill|id)(?!\w)",
         lambda m: m.group(1).capitalize())
    ]
    
    # =====================================
    # 9. Punctuation patterns
    # =====================================
    PUNCTUATION = [
        (r'([!?.]){2,}', r'\1'),   # Remove repeated punctuation
        (r'\s+([.,!?])', r'\1'),   # Fix spacing before punctuation
        (r'([.,!?])\s+', r'\1 '),  # Fix spacing after punctuation
        (r'\s+', ' '),             # Normalize spaces
    ]
    
    # =====================================
    # 10. Final cleanup patterns
    # =====================================
    FINAL_CLEANUP = [
        (r'\$TBALL[sS]\b', '$TBALL'),
        (r'\$Tball\b', '$TBALL'),
        (r'(\$TBALL)\s+', r'\1 '),
        (r'^\s*"|"\s*$', ''),  # Remove quotes at start/end
        (r'^\s*\'|\'\s*$', '') # Remove single quotes at start/end
    ]

    # =====================================
    # 11. Text standardization patterns
    # =====================================
    TEXT_STANDARDIZATION = [
        (r'\s+', ' '),        # Normalize spaces
        (r'\s+([.,!?])', r'\1')  # Fix spacing before punctuation
    ]
    
    # =====================================
    # 12. Cleanup patterns
    # =====================================
    CLEANUP = [
        (r'\[.*?\]', ''),  # Remove square bracket content
        (r'@\w+\s?', ''),  # Remove @ mentions
    ]
    
    # =====================================
    # 13. Content cutoff markers
    # =====================================
    CUTOFF_PHRASES = [
        "Note:",
        "Stay informed",
        "Here's MY",
        "Your response",
        "This response"
    ]
