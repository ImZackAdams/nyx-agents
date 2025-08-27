import re
import logging

def extract_prompt(text: str) -> str:
    # Remove bot mentions
    text = re.sub(r"@\w+", "", text).strip()
    text_lower = text.lower()

    # Define explicit phrases that indicate an image request.
    # Be very explicit and simple. If you want to expand later, you can.
    explicit_phrases = [
        "generate an image of",
        "generate an image",
        "make an image of",
        "make an image",
        "create an image of",
        "create an image"
    ]

    for phrase in explicit_phrases:
        if phrase in text_lower:
            # Extract the prompt after the phrase
            start_index = text_lower.find(phrase) + len(phrase)
            prompt_part = text[start_index:].strip()
            # If no prompt after phrase, return original text to avoid empty prompt triggers
            if not prompt_part:
                return text
            return prompt_part
    
    # If none of the explicit phrases are matched, return the original text
    return text
