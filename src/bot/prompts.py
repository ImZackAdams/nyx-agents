from typing import Dict, List

# --------------------------------
# 1) General Web3 & Crypto Educational
# --------------------------------
GENERAL_CRYPTO_EDUCATIONAL: List[str] = [
    "Web3 pro tip: 'decentralization' is like a group project with zero teachers—everyone’s in charge, and no one to blame. #ChainGang",
    "Blockchain 101: a giant public notebook nobody can secretly erase. Because some drama’s best kept permanent. #DigitalReceipts",
    "Ever wonder why ‘consensus’ matters? It’s code for ‘we all agree, so you can’t cheat.’ Sit down, scammers. #NoCheatersAllowed",
    "Crypto security rule: never share your private key. It’s basically a diary password, but losing it costs way more than middle-school gossip. #LockItDown",
    "Eyeing Web3? Start with a block explorer. It’s like peeking behind the curtain of the next financial revolution—except wizards are real. #Peekaboo",
]

# --------------------------------
# 2) NFTs & Tokenized Assets
# --------------------------------
NFT_PROMPTS: List[str] = [
    "NFTs: digital collectibles or pricey JPEGs? Depends on whether you’re flipping them or cluelessly hoarding them. #Perspective",
    "Just minted an NFT? Enjoy that intangible trophy—like adopting a Tamagotchi, but with fewer responsibilities. #90sThrowback",
    "Gas fees? Think of them as the cover charge to an exclusive blockchain club. Pixel art flexes included. #PriceOfFame",
    "NFT utility is the future—concert tickets, real estate deeds, proof of authenticity. Digital bragging rights, served hot. #SmartAssets",
    "If ‘metadata’ sounds dull, imagine it’s your NFT’s birth certificate. Lose it and watch your precious collectible disappear. #BlockchainBasics",
]

# --------------------------------
# 3) DeFi & Tokens
# --------------------------------
DEFI_TOKENS_PROMPTS: List[str] = [
    "DeFi = more freedom, fewer suits. But ‘fewer suits’ ≠ ‘less risk.’ Bet carefully, frens. #EyesOpen",
    "Yield farming: a fancy term for chasing juicy returns in digital fields. Harvest or watch your crops vanish. #CropCircles",
    "Stablecoins keep crypto from going full stampede. Peg ‘em right or watch the meltdown. #SteadyAsSheGoes",
    "Liquidity pools: toss in tokens, earn fees—like renting out your car. If the market swerves, hello unicycle. #ImpermanentLoss",
    "Tokenomics: science that stops your coin from becoming Monopoly money. Print too many, and the market laughs. #BalanceIsKey",
]

# --------------------------------
# 4) Memecoins & Sassy Remarks
# --------------------------------
MEME_CAPTIONS = [
    "When $TBALL says 'Built Different,' it really means taking memes to the moon. 🚀 #NoApologies",
    "Swing with us or stay dusty—$TBALL doesn’t wait for permission. #BuiltDifferent",
    "Some coins brag about utility; $TBALL just brags about fun. We’re built different, baby! 💅 #MemeLife",
    "Ready to swing with us? $TBALL has the last laugh when it comes to ‘worthless memes.’ #BuiltDifferent",
    "Board the $TBALL rocket and swing with us—profits are no joke when your coin’s built different. 😏",
    "Swing with us on $TBALL’s wild ride. Because if it ain’t built different, it ain’t memeworthy. 💥 #CryptoFun",
    "Built different? That’s $TBALL’s battle cry. Wave goodbye to boring coins and say hello to meme magic. ✨",
    "Swinging with us means betting on $TBALL chaos—and boy, do we love chaos! #BuiltDifferent",
    "If your memecoin can’t handle the spotlight, swing with us at $TBALL. We’re built different for a reason. 😎",
    "Built different and proud of it—$TBALL is where meme mania meets raw ambition. Swing with us if you dare! 💅",
    "Watching $TBALL blast off? Either hop on board or enjoy the view from the sidelines. #MoonBound",
    "They called it ‘just a meme.’ We call it $TBALL because laughter pairs well with gains. #NoApologies",
    "If FOMO had a poster child, it’d be $TBALL. Grab your ticket or regret it later. 💥",
    "We tried ‘serious’ coins. Then $TBALL happened, and the rest is rocket-fueled history. #MemeticMomentum",
    "Everyone’s so serious, meanwhile $TBALL is printing memes—and profits. Coincidence? I think not. 😎",
    "Need some spice in your portfolio? $TBALL might just be the sauce you didn’t know you craved. #PicanteCrypto",
    "Who says a meme can’t rule the market? $TBALL thrives on chaos—join in or miss out. 🤷‍♂️",
    "Tired of the same old charts? Let $TBALL inject some excitement. Up, down, who cares—we’re laughing. 😂",
    "Call it a fluke, call it fate, $TBALL just keeps bopping critics on the head. #SassyCrypto",
    "No one regrets jumping into $TBALL except those who didn’t do it sooner. Meme mania, unstoppable. 💅"
]


# --------------------------------
# 5) Fallback: Comedic Disclaimers & Misc
# --------------------------------
FALLBACK_PROMPTS: List[str] = [
    "AI meltdown or market crash? Grab popcorn either way—chaos is free entertainment. #EntertainmentValue",
    "Triggered by roasts? Remember, block confirmations don’t care about your feelings. #RealityCheck",
    "Not into harsh truths? This isn’t the droid you’re looking for. #SassyAndIKnowIt",
    "Crypto or code drama—both can wreck your day. $TBALL might 10x, so that’s a silver lining. #LifeLine",
    "High gas fees + savage tweets = normal here. If it’s too hot, go collect vintage stamps. #LowVolatility",
]

def get_all_prompts() -> Dict[str, List[str]]:
    """
    Returns all prompt categories for generating
    short, sassy, standalone tweets (no direct user references).
    """
    return {
        'general_crypto_educational': GENERAL_CRYPTO_EDUCATIONAL,
        'nft_prompts': NFT_PROMPTS,
        'defi_tokens_prompts': DEFI_TOKENS_PROMPTS,
        'memecoin_prompts': MEME_CAPTIONS,
        'fallback_prompts': FALLBACK_PROMPTS,
    }
