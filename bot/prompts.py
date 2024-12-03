"""Module containing all tweet prompts organized by category."""

from typing import Dict, List

DATING_PROMPTS = [
    "FOMO is like your ex—teaches you lessons but always leaves you wanting something better! 🌟",
    "Panic selling? It's like ghosting after a great date—you're only hurting yourself! 🥂",
    "Trusting random DeFi protocols is like blind dates—sometimes surprising, often thrilling, always a story! 💼💖",
    "Diversification: because keeping your options open is the ultimate power move. 💅",
    "When GPT understands you better than your dates—because it's smarter and listens more! 🤖✨",
    "Chart patterns are like dating—they always have a story to tell if you're paying attention! 💘📉"
]

CRYPTO_PROMPTS = [
    "FOMO might knock, but patience builds the mansion. 🏡💎",
    "Panic selling is like yelling during turbulence—sit tight, the skies clear eventually! ✈️✨",
    "Blockchain: Proof that simplicity can be revolutionary! 🔗🚀",
    "What's the crypto wisdom you wish you had sooner? Let's spread the wealth of knowledge! 💡💰",
    "Luck vs. strategy in crypto? Spoiler: Strategy wins every time, but luck makes the ride fun! 🍀📈",
    "If Bitcoin hadn't paved the way, Web3 wouldn't be the wild adventure it is today. 🙌💻",
    "Blockchain in one sentence: It's the internet's way of finally growing up! 🛠️✨",
    "NFTs aren't just pictures—they're the first draft of a new internet! 🌐🎨",
    "Market crashes test patience, but the calm ones always catch the rebound! 🪂💹"
]

AI_PROMPTS = [
    "Why does GPT sound smarter than me? Because it's powered by ambition, not coffee. ☕🤖✨",
    "AI predicting your every move? Don't worry, it's just here to make life smoother than your ex ever did. 😉💻",
    "Training AI is like raising a star athlete: an investment in future wins! 🏆💡",
    "AI models are like your best friend—they know your quirks and make you look smarter. 👩‍💻🤖",
    "Overfitting expectations? Relax, even AI knows how to adapt to greatness. ✨📈",
    "Machine learning: Turning GPUs into the engines of tomorrow's innovations. 🔥🚀",
    "AI dreaming big—one hallucination at a time. Don't we all? 🤩🤖"
]

FINANCE_PROMPTS = [
    "Budgeting tip: Diversify smarter, not harder—Dogecoin's fun, but so is balance! 🌈💸",
    "Financial planners are like GPS for your money—they keep you from driving into a ditch! 🚗💰",
    "Retirement plans are like blue-chip investments—solid, steady, and worth the wait. 🕰️📊",
    "Index funds vs. day trading: Are you a steady achiever or a thrill-seeker? 🏖️📈",
    "If investing were easy, everyone would have their own yacht—Warren Buffett's got the blueprint! 🚤✨"
]

JOKES_AND_FUN_PROMPTS = [
    "Neural networks: Making spreadsheets look like amateurs since forever. 📊✨",
    "If crypto coins had personalities, which one's stealing the spotlight at parties? 🎉💸",
    "What's your funniest 'learning moment' in crypto? Share the love and laughs! 😂📈",
    "If Satoshi Nakamoto had a Twitter account, what would their bio say? 🤔✨",
    "Blockchain: Spreadsheets with swagger and purpose. 🌶️🔗",
    "NFTs: The spicy intersection of art, ownership, and possibilities! 🎨💎"
]

MEME_CAPTIONS = [
    "This meme? Pure gold. 🪙✨ #Tetherballcoin",
    "Some things you just can't unsee. 😂 #CryptoHumor",
    "Hodlers will understand. 💎🙌 #Tetherballcoin",
    "Because laughter is the best investment. 😂📈 #CryptoMemes",
    "Meme game strong, just like our coin. 🚀🔥 #Tetherballcoin"
]

FALLBACK_TWEETS = [
    "Crypto markets never sleep, and neither should your strategies! 💅 #CryptoLife",
    "DYOR and don't let FOMO get you—research is key to success! ✨ #CryptoWisdom",
    "Diversification is the spice of life, even in the crypto world! 🌟 #CryptoInvesting",
    "Don't let panic sell-offs drain your gains. Stay calm and HODL! 🚀 #CryptoTips",
    "Your seed phrase is sacred—treat it like your most prized possession! 🔐 #CryptoSecurity"
]

def get_all_prompts() -> Dict[str, List[str]]:
    """Returns all available prompts organized by category."""
    return {
        'dating_prompts': DATING_PROMPTS,
        'crypto_prompts': CRYPTO_PROMPTS,
        'ai_prompts': AI_PROMPTS,
        'finance_prompts': FINANCE_PROMPTS,
        'jokes_and_fun_prompts': JOKES_AND_FUN_PROMPTS
    }