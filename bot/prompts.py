"""Module containing all tweet prompts organized by category with engagement hooks."""

from typing import Dict, List

DATING_PROMPTS = [
    "Drop your worst crypto FOMO story—bet it still hurts less than your ex! 🌟 Reply below!",
    "Tell me your best 'panic selling' story without telling me you panic sold! 🥂 Go!",
    "Rate your trust in DeFi vs blind dates—which one's burned you more? 💼💖 Share below!",
    "What's your portfolio diversity looking like? Show us your power moves! 💅 Quote tweet with your strategy!",
    "GPT vs your dating life—which one needs more debugging? 🤖✨ Let's hear it!",
    "Share a chart pattern that reminds you of your dating history! Wrong answers only! 💘📉",
    "Your portfolio should be like your dating standards—what's your non-negotiable? Share below! 💫💼",
    "Drop a 🚩 if you've ever signed a smart contract without reading it! Let's hear that story! 📝💕",
    "Quote tweet with your biggest investing green flag! What makes you swipe right on a project? 🎯💖",
    "Staking vs commitment issues—which one's giving you cold feet? Poll time! 💍✨"
]

CRYPTO_PROMPTS = [
    "Drop your best 'diamond hands' moment below! What made you HODL through the storm? 🏡💎",
    "Wrong answers only: What's your strategy during a market crash? Give us your best advice! ✈️✨",
    "Explain blockchain to us like we're your grandparents! Best explanation wins! 🔗🚀",
    "Quote tweet with the crypto wisdom you wish you had in 2021! Let's save the next generation! 💡💰",
    "Strategy or luck? Share your biggest crypto win and let us guess which one it was! 🍀📈",
    "If Bitcoin was a person, what would their dating profile say? Wrong answers only! 🙌💻",
    "Explain Web3 using only emojis! Best thread gets a follow! 🛠️✨",
    "Show us your NFT collection without showing us your NFT collection! Go! 🌐🎨",
    "Tag someone who bought the dip! Bonus points if they actually timed it right! 🪂💹",
    "Style check: Drop your wallet address fits—blue chip only or all alt everything? 👜✨",
    "Bears vs Bulls—whose outfit slays harder? Vote below! 🐻🐂",
    "Quote tweet your worst 'too good to be true' DeFi moment! We promise not to laugh (much)! 👀💰",
    "Show us your staking rewards flex! What's your passive income strategy? 💅💎"
]

AI_PROMPTS = [
    "Tell us your best 'AI said what?!' moment! Wrong responses only! ☕🤖✨",
    "What's the most savage response you've gotten from ChatGPT? Screenshots or it didn't happen! 😉💻",
    "Rate your AI model's sass level from 1-10! Share the receipts! 🏆💡",
    "If your AI assistant was your bestie, what would be their go-to gossip? Spill the tea! 👩‍💻🤖",
    "Share your most chaotic AI generation—we know you've got screenshots! ✨📈",
    "Your GPU is writing a breakup letter to your wallet—what does it say? Best replies get shared! 🔥🚀",
    "Tag someone who needs to know about AI hallucinations! We've all been there! 🤩🤖",
    "Drop your favorite AI gossip network story! What's the tea on these neural networks? 🤫🤖",
    "Show us your best prompt engineering fail! We're here for the chaos! 💁‍♀️✨",
    "Which AI model matches your personality? Tag yourself! 🌟🤖",
    "Rate these language models' outfit choices! GPT is serving, but BERT is giving corporate! 📱💫"
]

FINANCE_PROMPTS = [
    "Tell us you're financially savvy without telling us your bank balance! Go! 🌈💸",
    "Your budget spreadsheet is spilling tea—what's the biggest plot twist? Share below! 🚗💰",
    "Tag someone who needs a retirement plan intervention! We see you! 🕰️📊",
    "Drop your best 'I thought I was day trading' story! Extra points for happy endings! 🏖️📈",
    "Quote tweet with your Warren Buffett moment! When did you feel like the Oracle? 🚤✨",
    "Show us your portfolio energy! What's giving main character energy right now? ✨💼",
    "Drop your DCA success story! When did consistency win over timing? 📅💅",
    "Risk management check! What's your safety net looking like? Wrong answers only! ☂️💫",
    "Compound interest flex time! Show us those gains graphs! 🧴📈"
]

TECH_SASS_PROMPTS = [
    "Rate your Web3 wallet collection! Which one's the vintage Birkin? 👜✨",
    "Tag that one dev who always finds the wildest bugs! We know who you are! 🐛💃",
    "Your code reviews need a reality show! What's the latest drama? 👀💻",
    "Show us your commit messages when no one's watching! We won't tell! 🎯✨",
    "Confess your 'testing in production' stories! Judgment-free zone! 👠🚫",
    "What's that one piece of legacy code you can't let go of? Tag your tech lead! 👗🔄"
]

PRODUCTIVITY_PROMPTS = [
    "Show us your chaotic to-do list energy! No judgment, we're all friends here! 🎨✨",
    "Rate your investment in productivity tools vs actual productivity! Be honest! 📝💼",
    "Drop your best 'I thought I could multitask' story! Screenshots encouraged! ⏰👔",
    "Tag someone who needs a meeting-free day! We're looking out for you! 🧖‍♀️✨",
    "Inbox zero check! How's that going for everyone? Wrong answers only! 📧✨"
]

MEME_CAPTIONS = [
    "Caption this crypto chart! Best reply gets a follow! 🪙✨ #Tetherballcoin",
    "Wrong answers only: What's happening in this meme? 😂 #CryptoHumor",
    "Tag a HODLer who needs to see this! 💎🙌 #Tetherballcoin",
    "This meme called you out, didn't it? Share your story below! 😂📈 #CryptoMemes",
    "Make it a meme! Drop your best caption below! 🚀🔥 #Tetherballcoin",
    "Market's dipping but your meme game never does! Show us what you've got! 💃📉",
    "It's not giving financial advice... but make it viral! Remix this! 💅💫",
    "Your portfolio saw this meme and took it personally! Tag yourself! ☕️✨"
]

FALLBACK_TWEETS = [
    "Drop your crypto lifestyle hacks below! How do you stay winning? 💅 #CryptoLife",
    "Share your DYOR process! Wrong answers strongly encouraged! ✨ #CryptoWisdom",
    "Show us your portfolio diversity in emojis only! 🌟 #CryptoInvesting",
    "Tag a friend who needs to learn about HODL life! We're here to help! 🚀 #CryptoTips",
    "What's your seed phrase storage strategy? (Wrong answers only!) 🔐 #CryptoSecurity",
    "Serving looks and gains! Drop your success story below! 💁‍♀️📈 #BalancedLife",
    "Money moves check! What's your latest power play? 💫💼 #WealthyMindset",
    "Your research is showing! Drop your favorite alpha source! ✨📚 #SmartMoney"
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
        'meme_captions': MEME_CAPTIONS,
        'fallback_tweets': FALLBACK_TWEETS
    }