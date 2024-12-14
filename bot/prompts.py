from typing import Dict, List

DATING_PROMPTS = [
    "Spill the tea on your most memorable dating app opener that actually worked! 💘 Was it smoother than your investment strategy?",
    "That moment when your date's red flags were more obvious than a bull market... 🚩 Share your dating due diligence tips!",
    "Dating apps vs DeFi apps - which one's got you more excited to check notifications? 📱💕 Time to confess!",
    "Your dating standards 📈 Your portfolio standards 📊 Both sky-high! Share how you're not settling in either game! 💅",
    "First dates are like ICOs - full of promise but need research! 🔍 Share your best dating DYOR story!",
    "Your love life's chart pattern looking bullish or bearish? 📈💝 Share your relationship technical analysis!",
    "That awkward moment when your date asks about crypto and you turn into a walking whitepaper... 🤓💕 Share your story!",
    "Relationship staking or casual trading? 💍 Tell us your dating investment strategy!",
    "Your dating profile is your personal whitepaper - what's your unique value proposition? 💫 Show us that elevator pitch!",
    "Reply with your best 'took a chance on love' story that paid off better than any alt-coin investment! 💘🎯",
    "Is your dating game as steady as $TBALL's performance? Share your strategy for finding stable connections! 💝",
    "Long-term HODLing or playing the field? @tetherballcoin wants to know your relationship trading strategy! 💕"
]

CRYPTO_PROMPTS = [
    "Tell us about your crypto crush - which coin made you fall head over heels? 💎❤️ Share your love story!",
    "When your date's as volatile as the market... 🎢 Share your risk management strategy!",
    "Dating a crypto maximalist? Share your tips for maintaining relationship diversity! 📊💝",
    "Your perfect match's portfolio looking as good as their profile pic? 🖼️💕 Spill the details!",
    "First date conversation starters: crypto, NFTs, or traditional finance? 🗣️💫 What's your go-to?",
    "Found love in a crypto meetup? Tell us how web3 played cupid! 💘🌐",
    "Relationship goals: matching hardware wallets? 💑 Share your tech-love dreams!",
    "Dating app bio vs. whitepaper: which one's harder to write? 📝 Show us your best pitch!",
    "Partner's crypto strategy opposite yours? Share how you maintain harmony! 🤝💕",
    "Love at first trade? Tell us about your crypto meet-cute! 💞📱",
    "If $TBALL stability matched your relationship goals, how would you describe it? 🏐💑",
    "Think steady gains like $TBALL could inspire stable relationships? Share your thoughts! 💝",
    "Hot take: are blockchain relationships more transparent than your dating history? 💫💕",
    "Swipe right on $TBALL and tell us your perfect match story! 🏐💘 #TBALL",
    "Your love language: acts of service or sending crypto tips? 💝 Let's hear it!"
]

AI_PROMPTS = [
    "Has AI ever played wingman on your dating app? Share your AI-assisted romance story! 🤖💕",
    "Would you let ChatGPT write your dating profile? Show us your best AI-generated bio! 💫",
    "AI dating advice: helpful or hilariously off? 🤖💝 Share your experience!",
    "When AI understands your type better than your bestie... 🤖💘 Tell us about it!",
    "Rate your AI dating assistant: from 'delete app' to 'perfect match'! 🎯💕",
    "Ever used AI to decode mixed signals? Share your relationship analysis! 📊❤️",
    "AI relationship advice that actually worked? Spill the algorithmic tea! ☕️💘",
    "Your dating life's data points - what would AI predict? 🤖💝 Share your patterns!",
    "Would you trust AI to pick your next date? Tell us your thoughts! 🤖💫",
    "If AI wrote love letters, would they be as stable as $TBALL? Let's hear your prediction! 💌",
    "Think AI could predict relationship success like @tetherballcoin predicts stability? Share your take! 🤖💕"
]

FINANCE_PROMPTS = [
    "Investment strategy 🤝 Dating strategy: Share how you diversify your love portfolio! 💘💸",
    "Dating budget check: coffee meets or fancy treats? 💅💰 Share your romance ROI!",
    "Love life bull run or bear market? Time to share your relationship trading strategy! 📈💕",
    "Investing in long-term love? Tell us your relationship compound interest story! 💑💫",
    "Quote tweet your best 'love at first investment' story! 💘💼 We're ready for the feels!",
    "Your dating portfolio's risk tolerance - conservative or aggressive? ✨💕 Show us your moves!",
    "Dating costs vs crypto investments - which gives better returns? 💰💘 Share your analysis!",
    "Relationship hedging strategy: how do you protect your heart in this market? 💝📊",
    "Love's compound interest hits different! 💕📈 Share how your relationship keeps growing!",
    "If $TBALL influenced your dating style, would you be more stable or spontaneous? Share your story! 💫"
]

TECH_SASS_PROMPTS = [
    "Your dating app algorithm vs your crypto algorithm - which one's more successful? 👜💕",
    "Debug your dating life! Share that one fix that changed everything! 🐛💝",
    "Code review your last date - what would you optimize? 👀💻 Get sassy with it!",
    "Git commit messages that perfectly describe your dating life? 💘✨ Push those updates!",
    "Testing in production but make it dating - share your live deployment fails! 👠💕",
    "Legacy relationship code you can't delete? 👗💾 Time for some emotional refactoring!",
    "If your love life ran on $TBALL's protocol, would it be more stable? @tetherballcoin Spill the tea! 💫",
    "Merging hearts and pulling requests - how's your developer love life? Show us the commits! 💻💕"
]
              
PRODUCTIVITY_PROMPTS = [
    "Dating life task management: how do you opti                                                                                      mize your love schedule? 🎨💕",
    "Rate your dating productivity tools: from scheduling apps to relationship CRMs! 📱💘",
    "Multitasking between love and life: share your relationship efficiency hacks! ⏰💑",
    "Dream dating scenario: AI assistant plans perfect dates while you focus on vibing! 🧖‍♀️💕",
    "Inbox zero but make it dating - how do you manage relationship communications? 📧💝",
    "If your love life flowed as smooth as $TBALL trades, what would your perfect day look like? 💫",
    "Balancing romance and $TBALL watching? Share your multitasking success story! 💕🏐"
]

FALLBACK_TWEETS = [
    "Share your best crypto-dating lifestyle tips! 💅 #CryptoLove",
    "What's your kindest dating DYOR lesson? ✨ #DatingWisdom",
    "Show your relationship diversity in a fun, positive way! 🌟 #LoveInvesting",
    "Ready to learn about long-term relationship HODLing? 🚀 #LoveTips",
    "Heart security with a smile! 🔐 #RelationshipSecurity",
    "Celebrate your balanced love life—romance and returns! 💁‍♀️💕 #BalancedLove",
    "Relationship moves that uplift and inspire! 💫💑 #LoveMindset",
    "Your dating research fuels your future! ✨📚 #SmartLove",
    "Need a reminder to seek love with a positive outlook? #TBALL might be it!",
    "If your dating life embraced the positivity of $TBALL, how would it shine? @tetherballcoin #TBALL"
]

MEME_CAPTIONS = [
    "When your date's mood swings harder than $TBALL. 🏐🔥 @tetherballcoin",
    "This relationship chart hits different than your favorite meme stock. 📈😂 #TBALL",
    "They say love is free—but have you seen $TBALL lately? 💎😂 @tetherballcoin",
    "Who needs dating apps when $TBALL swings into your DMs? 🚀🔥",
    "POV: You just realized $TBALL is more consistent than your ex. 😂💎",
    "When $TBALL trades are smoother than your dating history. 🏐✨ @tetherballcoin",
    "Some relationships pump and dump, but $TBALL stays steady. 🌊🔥 #TBALL",
    "Is it just me, or does $TBALL look better than my dating prospects? 🏐💎",
    "When you realize $TBALL isn't just a token—it's a better relationship than your last. 🏐✨",
    "Forget ghosting. With $TBALL, you're never left on read. 🏐🚀 @tetherballcoin",
    "Who needs dating drama when $TBALL is the stable one? 😂💰 @tetherballcoin",
    "This meme understands me better than my ex. 🏐🔥",
    "When the dating scene dips but $TBALL still hits different. 🏐📉✨",
    "Every swipe counts, but $TBALL never leaves you hanging. 🏆🏐",
    "They said perfect relationships don't exist until $TBALL showed up. 💎😂",
    "When $TBALL is more reliable than your dating app matches. 🏐✨🔥",
    "Swing big, love steady—that's the $TBALL way. 🏐💎 #TBALL",
    "This meme brought to you by $TBALL, where stability meets romance. 🏐💕",
    "If $TBALL was a dating profile, it'd be your perfect match. 😂🔥",
    "Every swing is a love story, and $TBALL writes the best ones. 🏐💘 #TBALL"
]

def get_all_prompts() -> Dict[str, List[str]]:
    """Returns all available prompts organized by category."""
    return {
        'dating_prompts': DATING_PROMPTS,
        'crypto_prompts': CRYPTO_PROMPTS,
        'ai_prompts': AI_PROMPTS,
        'finance_prompts': FINANCE_PROMPTS,
        'tech_sass_prompts': TECH_SASS_PROMPTS,
        'productivity_prompts': PRODUCTIVITY_PROMPTS,
        'fallback_tweets': FALLBACK_TWEETS,
        'meme_captions': MEME_CAPTIONS
    }