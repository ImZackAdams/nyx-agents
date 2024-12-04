from typing import Dict, List

DATING_PROMPTS = [
    "Reflect on a time you overcame FOMO and learned something new! 🌟 Share your growth with the community!",
    "Tell us about a positive pivot you made in your investing journey—no panic, all progress! 🥂",
    "Which has helped you grow more, learning about DeFi or stepping outside your comfort zone on a date? 💼💖",
    "Show off how you’ve diversified your portfolio to build confidence! 💅 Share your winning approach!",
    "Is your decision-making smoother in investing or dating? 🤖✨ Celebrate your best moves!",
    "Share a chart pattern that positively inspires you—maybe it mirrors your personal growth! 💘📈",
    "Your portfolio standards and life standards—both should be high! 💫💼 Share one non-negotiable for success!",
    "Ever been proud of reading every detail before signing a smart contract? 📝💕 How does diligence pay off for you?",
    "Quote tweet with your brightest investing green flag! What makes a project or goal shine? 🎯💖",
    "Staking or stepping into new commitments—where have you grown more? 💍✨",
    "If your personal journey was as reliable as $TBALL, how stable would it feel? 💖🔥 #TBALL",
    "Hearts or crypto gains? Tell @tetherballcoin how embracing growth outlasts any past challenge! 🏐✨"
]

CRYPTO_PROMPTS = [
    "Share a time you held steady and grew stronger! 🏡💎 Let us cheer on your diamond mindset!",
    "In a changing market, what’s your most uplifting strategy? ✈️✨",
    "Explain blockchain in a kind and simple way. 🔗🚀 Spread knowledge and inspire newcomers!",
    "Quote tweet with the crypto wisdom you’d pass forward today! 💡💰 Help guide others positively!",
    "Did strategy or optimism fuel your biggest crypto win? 🍀📈 Celebrate your success story!",
    "Imagine Bitcoin as a supportive friend—what encouraging trait would it highlight? 🙌💻",
    "Explain Web3 with uplifting emojis! 🛠️✨ Let’s see your creative positivity!",
    "Show your NFT journey’s highlights—no need to brag, just inspire! 🌐🎨",
    "Think you timed the market well? Patience pays off! 🪂💹",
    "Style check: Are you confidently holding blue chips or exploring diverse alts? 👜✨",
    "Bears or Bulls—both bring lessons. 🐻🐂 Share a positive takeaway!",
    "Quote tweet a DeFi lesson you learned. 👀💰 What’s your growth story?",
    "Show off your staking wins and steady gains! 💅💎 Celebrate consistent progress!",
    "If your portfolio includes $TBALL, how does that reflect your optimism? 🏐💎 #TBALL",
    "Think you can swing into new opportunities like $TBALL? Share your bright vision!"
]

AI_PROMPTS = [
    "Share a fun moment when AI surprised you in a good way! ☕🤖✨",
    "What’s the kindest response ChatGPT ever gave you? 😉💻",
    "Rate your AI model’s helpfulness from 1-10! 🏆💡",
    "If your AI assistant was a supportive friend, what encouraging words would they share? 👩‍💻🤖",
    "Show a time AI generation made you smile! ✨📈",
    "If your GPU wrote a love letter to your wallet, what hopeful message would it send? 🔥🚀",
    "Ever learned something new thanks to AI? 🤩🤖 Share your positive discoveries!",
    "Drop an AI success story! 🤫🤖",
    "Show a prompt engineering moment that led to insight! 💁‍♀️✨",
    "Which AI model best reflects your positive traits? 🌟🤖",
    "If AI had a favorite crypto, would $TBALL’s stability impress it? 🤖💎 #TBALL",
    "Think AI could spot @tetherballcoin as a promising opportunity? Share your optimistic guess!"
]

FINANCE_PROMPTS = [
    "Show how you’re building wealth step-by-step! 🌈💸",
    "Has your budget ever surprised you in a positive way? 🚗💰",
    "Ready to refine your financial future? Your long-term growth is inspiring!",
    "Share a day-trading lesson you turned into a positive outcome! 🏖️📈",
    "Quote tweet with your “Warren Buffett” moment of clarity! 🚤✨",
    "Show your portfolio’s confident energy! ✨💼",
    "Did Dollar-Cost Averaging bring you consistency and calm? 📅💅",
    "How do you secure your financial future? ☂️💫",
    "Compound interest wins are worth celebrating! 🧴📈",
    "If $TBALL boosts your outlook, how does it brighten your financial path? @tetherballcoin #TBALL"
]

TECH_SASS_PROMPTS = [
    "Rate your Web3 wallet lineup—each one a step in your positive journey! 👜✨",
    "Celebrate the developers who solve tough bugs and improve our world! 🐛💃",
    "Your code reviews lead to learning and innovation! 👀💻",
    "Show off your clever commit messages—creativity fuels positivity! 🎯✨",
    "Testing in production that taught you something valuable? 👠🚫",
    "One piece of legacy code that brings warm nostalgia? 👗🔄",
    "If your dev stack chose $TBALL for stability, how would it shine? @tetherballcoin",
    "Are you pushing creative commits and ideas that inspire growth? Show us your work!"
]

PRODUCTIVITY_PROMPTS = [
    "Show your to-do list progress—turning chaos into calm! 🎨✨",
    "Rate your productivity tools—how do they brighten your day? 📝💼",
    "Share a multitasking moment where you triumphed! ⏰👔",
    "Imagine a day free of meetings—how would you grow and create? 🧖‍♀️✨",
    "Inbox zero or inbox hero? 📧✨ Show how positivity helps you manage it all!",
    "If your workflow flowed as smoothly as $TBALL trades, how would you celebrate? @tetherballcoin",
    "Juggling tasks while watching $TBALL rise? Let positivity guide your focus!"
]

FALLBACK_TWEETS = [
    "Share your best crypto lifestyle tips that promote well-being! 💅 #CryptoLife",
    "What’s your kindest DYOR lesson? ✨ #CryptoWisdom",
    "Show your portfolio diversity in a fun, positive way! 🌟 #CryptoInvesting",
    "Ready to learn about HODL life? 🚀 #CryptoTips",
    "Seed phrase security with a smile! 🔐 #CryptoSecurity",
    "Celebrate your balanced life—gains and gratitude! 💁‍♀️📈 #BalancedLife",
    "Money moves that uplift and inspire! 💫💼 #WealthyMindset",
    "Your research fuels your future! ✨📚 #SmartMoney",
    "Need a reminder to seek opportunities with a positive outlook? #TBALL might be it!",
    "If your watchlist embraced the positivity of $TBALL, how would it shine? @tetherballcoin #TBALL"
]

MEME_CAPTIONS = [
    "When $TBALL swings, it swings big. 🏐🔥 Are you ready to catch the momentum? @tetherballcoin",
    "This chart hits harder than your favorite meme stock. 📈😂 #TBALL",
    "They say laughter is the best currency—except when you have $TBALL. 💎😂 @tetherballcoin",
    "Who needs a moonshot when $TBALL swings into orbit? 🚀🔥",
    "POV: You just realized $TBALL is the most stable thing in your portfolio. 😂💎",
    "When $TBALL trades are smoother than your pick-up lines. 🏐✨ @tetherballcoin",
    "Some tokens pump, but $TBALL makes waves. 🌊🔥 #TBALL",
    "Is it just me, or does $TBALL look better with every swing? 🏐💎 @tetherballcoin",
    "When you realize $TBALL isn't just a token—it's a lifestyle. 🏐✨",
    "Forget hodling. With $TBALL, you’re swinging into greatness. 🏐🚀 @tetherballcoin",
    "Who needs memes when $TBALL is already the joke-proof investment? 😂💰 @tetherballcoin",
    "This meme swings harder than $TBALL on a good day. 🏐🔥",
    "When the market dips but $TBALL still hits the sweet spot. 🏐📉✨",
    "Every swing counts, and $TBALL is always on target. 🏆🏐 @tetherballcoin",
    "They said stability was a myth until $TBALL showed up. 💎😂 @tetherballcoin",
    "When $TBALL is your biggest win and your favorite meme. 🏐✨🔥",
    "Swing big, hold steady—that’s the $TBALL way. 🏐💎 #TBALL",
    "This meme brought to you by $TBALL, where swings meet success. 🏐🚀 @tetherballcoin",
    "If $TBALL doesn’t inspire your next meme, are you even trading? 😂🔥 @tetherballcoin",
    "Every swing is a story, and $TBALL is writing the best ones. 🏐✨ #TBALL"
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
