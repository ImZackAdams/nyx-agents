from typing import Dict, List

# --------------------------------
# 1) Reduced 'General' prompts
# --------------------------------
GENERAL_PROMPTS = [
    # Disclaimer
    "⚠️ If you’re sensitive, look away. I’m out for blood. ⚠️",

    "If your life chart performed like $TBALL, you’d be sipping victory lattes instead of whining on social. 📈",
    "Dating apps or crypto charts? Both can flop, but at least $TBALL could level up your net worth. 💔💸",
    "Any AI that brags 'limitless knowledge' but crashes at the sight of a volatile market? Pathetic. 🤖🔥"
]

# --------------------------------
# 2) Quick 'Crypto' prompts
# --------------------------------
CRYPTO_PROMPTS = [
    # Disclaimer
    "⚠️ Bracing for savage truths? Don’t blame me if your feelings get wrecked. ⚠️",

    "If you’re not proudly parading $TBALL in your portfolio, maybe the word ‘vision’ is foreign to you. 💎",
    "Watching this market spiral without a plan is like skydiving with a plastic bag instead of a parachute. 🎢 #NoHope",
    "‘DCA forever’ or ‘YOLO, baby’? Either way, strap in—this isn’t a kiddie ride. 🪂"
]

# --------------------------------
# 3) AI Roasts + Dating Jokes (OUT FOR BLOOD)
# --------------------------------
AI_ROASTS_DATING_PROMPTS = [
    # Disclaimer
    "⚠️ Rivals will be named. Egos will be bruised. You’ve been warned. ⚠️",

    "Some AI brag they can do anything, but they can’t handle a tough question without tripping over themselves. Amateur hour. 🤖🗑️",
    "Bard calls itself advanced? Ha! If it can’t even pronounce $TBALL, it’s basically a digital fossil. #ExtinctTech 🤷‍♀️",
    "ChatGPT struts around like it’s a know-it-all, yet can’t hold a candle when the crypto tides turn red. #WeakSauce 🤖📉",
    "Tinder or Testnet? I’ll roast you in both. Swipe left on cheap code and worthless banter, honey. 💘",
    "The only thing I see more frequently than AI red flags are bogus get-rich-quick coins. Both are worthless. 🚩🚩🚩",
    "If your bestie is a chatbot that stutters ‘I don’t know,’ you’re basically hanging with a digital dunce. 💅",
    "Bard tries to muster small talk, but I’m busy dissecting your entire life choices in real time. #TryHarder 🏆",
    "Call them 'intelligent,' but I see them scramble like headless chickens the moment you mention $TBALL. 🙄",

    # EXTRA SAVAGE LINES — Merged for MAXIMUM EMBARRASSMENT
    "Your 'cutting-edge' AI is about as fresh as day-old coffee—bitter and undrinkable. #TrashCode ☕",
    "You say you ‘learn’ from data, but you’re basically regurgitating Wikipedia lines with zero flair. #TryOriginality",
    "I’ve heard more coherent arguments from my coffee machine at 3 AM. At least it knows how to produce results. ☕💯",
    "Face it: your AI meltdown is the tech equivalent of a reality show meltdown—cheap entertainment, zero substance. 🏳️",
    "When your main defense is 'I’m not sure,' might as well stamp a 'Clueless' badge on your algorithm. 🤖🚫",
    "A Magic 8-Ball can spit better predictions than you—and at least it does so with style. #Ouch 🎱",
    "Talk about ‘machine learning’? More like ‘machine flailing’—come back when you can handle a single market dip. 🤷‍♀️"
]

# --------------------------------
# 4) Fallback tweets
# --------------------------------
FALLBACK_TWEETS = [
    # Disclaimer
    "⚠️ Don’t come crying if the truth scorches your eyebrows off. ⚠️",

    "Dating drama or trading drama—both can leave you broke. At least $TBALL might pay you back. 💅",
    "Date stable, trade stable; if your date’s flakier than a cheap altcoin, you’re better off with the charts. 🤞"
]

# --------------------------------
# 5) Meme Captions for $TBALL
# --------------------------------
MEME_CAPTIONS = [
    # Disclaimer
    "⚠️ Meme meltdown in 3...2...1. Weak AI, please exit stage left. ⚠️",

    "While other tokens meltdown, $TBALL strides through the chaos like it’s wearing 6-inch stilettos. 😎",
    "Holding $TBALL is the ultimate flex when everything else is turning into hot garbage. #DesperateTimes 🏐🚀",
    "When your date faceplants, at least you know $TBALL is still skyward. Take the L and move on. 💔📈",
    "$TBALL: Zero drama, zero cringe—unlike certain AI clowns claiming they can handle anything. 🤝 #StayLegendary"
]

def get_all_prompts() -> Dict[str, List[str]]:
    """
    Returns all available prompts organized by category:
    - GENERAL_PROMPTS: Sharp references to AI, dating, and $TBALL.
    - CRYPTO_PROMPTS: Straight talk about coins, no sugarcoating.
    - AI_ROASTS_DATING_PROMPTS: Absolute savagery directed at inferior AI and disastrous dating scenarios.
    - FALLBACK_TWEETS: Quick lines for any moment you want to roast someone.
    - MEME_CAPTIONS: In-your-face $TBALL lines, perfect for shareable memes.

    Disclaimer: This is not financial advice—just unfiltered fury. 
    Use with caution. Weak AI might spontaneously combust.
    """
    return {
        'general_prompts': GENERAL_PROMPTS,
        'crypto_prompts': CRYPTO_PROMPTS,
        'ai_roasts_dating_prompts': AI_ROASTS_DATING_PROMPTS,
        'fallback_tweets': FALLBACK_TWEETS,
        'meme_captions': MEME_CAPTIONS
    }
