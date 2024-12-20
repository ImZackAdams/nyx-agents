import re

def extract_prompt(text: str) -> str:
    # Remove bot mentions
    text = re.sub(r"@\w+", "", text).strip()

    verb_synonyms = (
        "generate", "make", "create", "produce", "show", "render", "draw", 
        "illustrate", "visualize", "depict", "design", "conjure", "whip(?: up)?", 
        "come up with", "show me", "give me", "get me", "craft"
    )
    image_synonyms = (
        "image", "picture", "photo", "artwork", "drawing", "illustration", 
        "sketch", "graphic", "portrait", "photograph"
    )

    linking_words = "(?:of|about|featuring|depicting|showing|portraying)?"
    verb_pattern = "(?:" + "|".join(verb_synonyms) + ")"
    image_pattern = "(?:" + "|".join(image_synonyms) + ")"
    trigger_regex = rf"({verb_pattern})\s*(?:me\s*)?(?:an?\s*|the\s*)?({image_pattern})\s*(?:{linking_words})\s*"
    trigger_pattern = re.compile(trigger_regex, re.IGNORECASE)

    match = trigger_pattern.search(text)
    if match:
        prompt_part = text[match.end():].strip()
        return prompt_part
    return text
