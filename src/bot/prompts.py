from typing import Dict, List

GENERAL_PROMPTS = [
    "When those market red flags were more obvious than a bull run... 🚩 Share your due diligence tips!",
    "DeFi apps vs dating apps - which one's got you more excited to check notifications? 📱✨",
    "New projects are like ICOs - full of promise but need research! 🔍 Share your best DYOR story!",
    "Your personal growth chart looking bullish or bearish? 📈 Share your life technical analysis!",
    "Your professional profile is your personal whitepaper - what's your unique value proposition? 💫",
    "Is your trading strategy as steady as $TBALL? Share your approach! 📈"
]

CRYPTO_PROMPTS = [
    "Tell us about your crypto crush - which coin made you believe in the future? 💎",
    "When your portfolio's as volatile as life itself... 🎢 Share your risk management strategy!",
    "Best conversation starters: crypto, NFTs, or traditional finance? 🗣️💫 What's your go-to?",
    "Investment goals: matching hardware wallets? 💎 Share your tech dreams!",
    "Your dating red flags 🚩 Your trading red flags 📊 Which ones have saved you more? Share!",
    "Think $TBALL's stability could redefine DeFi? Share your thoughts! 📈",
    "Your investment language: DCA or lump sum investing? 💫 Let's hear it!"
]

AI_PROMPTS = [
    "Has AI ever helped optimize your investment strategy? Share your story! 🤖📈",
    "AI financial advice: helpful or hilariously off? 🤖 Share your experience!",
    "Ever used AI to decode market signals? Share your analysis! 📊",
    "Would you trust AI with your dating life or your trading life? 🤖 Choose wisely!",
    "Could AI write better investment strategies than humans? Share your take! 📈"
]

FINANCE_PROMPTS = [
    "Investment strategy 🤝 Life strategy: Share how you diversify your portfolio! 💎",
    "Portfolio bull run or bear market? Time to share your trading strategy! 📈",
    "Your portfolio's risk tolerance - conservative or aggressive? ✨ Show us your moves!",
    "Risk hedging strategy: how do you protect your assets in this market? 📊",
    "Steady gains like $TBALL or high volatility? Share your preference! 📈"
]

TECH_SASS_PROMPTS = [
    "Debug your investment strategy! Share that one fix that changed everything! 🐛",
    "Code review your last date - what would you optimize? 👀💻 Get sassy with it!",
    "Testing in production but make it trading - share your live deployment fails! 💻",
    "Merging strategies and pulling profits - how's your developer portfolio? Show us the commits! 💻"
]
              
PRODUCTIVITY_PROMPTS = [
    "Rate your financial productivity tools: from tracking apps to portfolio CRMs! 📱",
    "Dream scenario: AI assistant manages perfect trades while you focus on strategy! 🧖‍♀️",
    "What would your perfect trading day look like? Share your vision! 💫"
]

FALLBACK_TWEETS = [
    "Share your best crypto-lifestyle tips! 💅 #CryptoLife",
    "What's your kindest investment DYOR lesson? ✨ #InvestingWisdom",
    "Asset security with a smile! 🔐 #InvestmentSecurity",
    "Investment moves that uplift and inspire! 💫 #GrowthMindset",
    "When $TBALL leads the way in stability 🏐 #InvestingMindset"
]

MEME_CAPTIONS = [
    "When the market swings harder than expected. 📈🔥",
    "This growth chart hits different than your favorite meme stock. 📈😂",
    "When your trades are smoother than your morning coffee. ✨",
    "Some assets pump and dump, but stability is key. 🌊🔥",
    "When your date asks about your crypto portfolio... 😅💼",
    "When the market dips but your strategy stays strong. 📉✨",
    "Every trade counts, but patience pays off. 🏆",
    "Trade smart, grow steady—that's the way. 💎",
    "If your portfolio was a person, would it be your financial advisor? 😂",
    "Every swing is a lesson, and we're here to learn. 📚"
]

def get_all_prompts() -> Dict[str, List[str]]:
    """Returns all available prompts organized by category."""
    return {
        'general_prompts': GENERAL_PROMPTS,
        'crypto_prompts': CRYPTO_PROMPTS,
        'ai_prompts': AI_PROMPTS,
        'finance_prompts': FINANCE_PROMPTS,
        'tech_sass_prompts': TECH_SASS_PROMPTS,
        'productivity_prompts': PRODUCTIVITY_PROMPTS,
        'fallback_tweets': FALLBACK_TWEETS,
        'meme_captions': MEME_CAPTIONS
    }