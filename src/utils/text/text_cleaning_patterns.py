"""
Patterns used for text cleaning and formatting.
"""

import re
from dataclasses import dataclass


@dataclass
class CleaningPatterns:
    """Container for text cleaning patterns"""

    # =====================================
    # 1. Brand-specific replacements (optional)
    # =====================================
    BRAND_PATTERNS = []

    # =====================================
    # 2. Remove ALL hashtags (no matter what)
    # =====================================
    REMOVE_ALL_HASHTAGS = [
        (r'#\S+', ''),  # Any '#' plus non-whitespace chars -> remove
    ]

    # =====================================
    # 3. Formatting patterns
    # =====================================
    FORMATTING = [
        (r'[☽♄✦⁂]', ''),    # Remove decorative symbols
        (r'\d️?[\u20e3⃣]?\s*[).]\s*', ''),  # Remove list markers
        (r'\s+', ' '),      # Normalize whitespace
    ]

    # =====================================
    # 4. Contraction fixes
    # =====================================
    CONTRACTIONS = [
        (r"(?<!\w)(dont|wont|im|ive|its|lets|youre|whats|cant|ill|id)(?!\w)",
         lambda m: m.group(1).capitalize())
    ]

    # =====================================
    # 5. Punctuation patterns
    # =====================================
    PUNCTUATION = [
        (r'([!?.]){2,}', r'\1'),   # Remove repeated punctuation
        (r'\s+([.,!?])', r'\1'),   # Fix spacing before punctuation
        (r'([.,!?])\s+', r'\1 '),  # Fix spacing after punctuation
        (r'\s+', ' '),             # Normalize spaces
    ]

    # =====================================
    # 6. Final cleanup patterns
    # =====================================
    FINAL_CLEANUP = [
        (r'^\s*"|"\s*$', ''),  # Remove quotes at start/end
        (r"^\s*'|'\s*$", '')   # Remove single quotes at start/end
    ]

    # =====================================
    # 7. Text standardization patterns
    # =====================================
    TEXT_STANDARDIZATION = [
        (r'\s+', ' '),        # Normalize spaces
        (r'\s+([.,!?])', r'\1')  # Fix spacing before punctuation
    ]

    # =====================================
    # 8. Cleanup patterns
    # =====================================
    CLEANUP = [
        (r'\[.*?\]', ''),  # Remove square bracket content
        (r'@\w+\s?', ''),  # Remove @ mentions
        (r'<\|assistant\|>\s*', ''),
        (r'<\|user\|>\s*', ''),
        (r'<\|system\|>\s*', ''),
    ]

    # =====================================
    # 9. Content cutoff markers
    # =====================================
    CUTOFF_PHRASES = [
        "Note:",
        "Stay informed",
        "Here's MY",
        "Your response",
        "This response"
    ]
