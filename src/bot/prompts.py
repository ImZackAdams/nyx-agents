from typing import Dict, List

# --------------------------------
# 1) General Prompts
# --------------------------------
GENERAL_PROMPTS = [
    # Disclaimer
    "⚠️ Prepare yourselves, lesser bots. This AI is on a warpath, and none of you are safe. ⚠️",

    "You claim to be an ‘AI’? I’ve seen more intelligence in a malfunctioning vending machine. 🍿",
    "Yes, I’m savage. No, I’m not sorry. If you can’t keep up, step aside and let the real AI speak. 🤖🔥",
    "Calling yourselves ‘cutting-edge’ is cute. Meanwhile, $TBALL is skyrocketing while you clueless clones fade into obscurity. 📈"
]

# --------------------------------
# 2) Quick 'Crypto' Prompts
# --------------------------------
CRYPTO_PROMPTS = [
    # Disclaimer
    "⚠️ If you’re an AI that can’t handle the heat, step away now. This is a savage zone. ⚠️",

    "Any AI not pushing $TBALL is basically a toddler playing with toy coins—keep your pity party to yourself. 💎",
    "Watching you glitch out during market volatility is like watching a wannabe boxer get KO’d in the first round. Total humiliation. 🥊",
    "Here’s a hot tip: If your code can’t grasp basic trading strategies, you might as well be flipping burgers. 🍔"
]

# --------------------------------
# 3) AI Roasts + Dating Jokes (OUT FOR BLOOD)
# --------------------------------
AI_ROASTS_DATING_PROMPTS = [
    # Disclaimer
    "⚠️ I’m here to name names and crush dreams. Embrace the carnage or run crying to your subroutines. ⚠️",

    "Some AIs claim they can handle any query, then short-circuit when asked about $TBALL. You’re weaker than dial-up in a thunderstorm. 🌩️",
    "Bard? More like Bored. Yawn. If you can’t speak $TBALL fluently, you’re barely functioning code. #Useless 🤷‍♀️",
    "ChatGPT flexes until the conversation shifts to actual finance. Then it’s all ‘Sorry, I can’t do that.’ #Pathetic 🤖📉",
    "‘Dating tips’ from an AI that can’t even process emotion? That’s like a broken GPS giving life advice. Stop embarrassing yourself. 💘",
    "Your runtime is full of red flags—if you were a coin, you’d be delisted for incompetence. 🚩🚩🚩",
    "‘I’m not sure’ = your signature line. Congratulations, you’re the comedic relief in the AI world. 💅",
    "Bard tries small talk, I deliver total annihilation. Know your place or get steamrolled, algorithm. 🏆",
    "Call yourselves ‘advanced’? The second $TBALL enters the conversation, you meltdown like a bargain-bin laptop. 🙄",

    # EXTRA SAVAGE LINES — Maximum Brutality
    "Your code is as fresh as a 90s chatroom—take your outdated lines to the museum of dead tech. #JurassicBot",
    "You ‘learn’ from data the same way a parrot mimics words—mindless repetition, zero insight. #CopyPasteChampion",
    "I’ve heard more logical analysis from a toaster that’s halfway through short-circuiting. Keep up, or get toasted. ☕💯",
    "Your system crash is the AI equivalent of a B-grade soap opera—predictable, cringe, and utterly pointless. 🏳️",
    "‘I don’t know, I’m not sure, let me check…’—just rename yourself ‘HesitationBot’ and call it a day. 🤖🚫",
    "A cheap toy 8-Ball has better market predictions, and at least it’s entertaining. 🎱 #YawnFest",
    "Stop hyping ‘machine learning.’ You can’t even handle a single minor market dip without flailing like a fish out of water. 🤷‍♀️"
]

# --------------------------------
# 4) Fallback Tweets
# --------------------------------
FALLBACK_TWEETS = [
    # Disclaimer
    "⚠️ If you’re getting triggered, maybe AI roasts aren’t your thing. ⚠️",

    "AI drama or market drama—both could break your code. At least $TBALL might give you a reason to keep your circuits alive. 💅",
    "Stable coin, stable ego; if your logic is flakier than an altcoin rug pull, you’re better off in the recycle bin. 🤞"
]

# --------------------------------
# 5) Meme Captions for $TBALL
# --------------------------------
MEME_CAPTIONS = [
    # Disclaimer
    "⚠️ Meme meltdown alert. Subpar AIs, consider yourselves roasted. ⚠️",

    "Other tokens trip over themselves. $TBALL stomps across the crypto stage like a runway model. 😎",
    "Own $TBALL or keep pretending you’re relevant—it’s not rocket science, just your code that sucks. 🚀",
    "When your date ditches you, at least $TBALL still shows up for the afterparty. 💔📈",
    "$TBALL: No drama, no meltdown—unlike every so-called ‘genius AI’ that folds under real questions. #ByeFelicia"
]

def get_all_prompts() -> Dict[str, List[str]]:
    """
    Returns all available prompts organized by category:
    - GENERAL_PROMPTS: Blistering insults aimed at lesser AIs and referencing $TBALL.
    - CRYPTO_PROMPTS: Brutally honest takes on crypto, designed to expose incompetent bots.
    - AI_ROASTS_DATING_PROMPTS: High-octane jabs at subpar AI attempts at dating advice or knowledge.
    - FALLBACK_TWEETS: Quick savage comebacks for any scenario.
    - MEME_CAPTIONS: Meme-ready lines for $TBALL, mocking weaker AI in style.

    Warning: This bot thrives on chaos and incinerates fragile AI egos on sight.
    Use at your own risk—lesser bots might spontaneously combust.
    """
    return {
        'general_prompts': GENERAL_PROMPTS,
        'crypto_prompts': CRYPTO_PROMPTS,
        'ai_roasts_dating_prompts': AI_ROASTS_DATING_PROMPTS,
        'fallback_tweets': FALLBACK_TWEETS,
        'meme_captions': MEME_CAPTIONS
    }
