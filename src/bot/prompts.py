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
MEME_CAPTIONS: List[str] = [
    "Memecoins: where internet culture meets speculation. Ride the wave or get dunked on by the next dog coin. #WoofWoof",
    "$TBALL soared again? Board the rocket or stay gainsless. No one regrets profits except those who missed ‘em. #HindsightHurts",
    "Pro tip: if your memecoin pitch is ‘trust me, bro,’ consider actually reading a whitepaper. #DueDiligence",
    "Some say memecoins are worthless. Tell that to the retirees who bet on a dog coin. Probability is savage, luck is wild. #DontBlink",
    "Shilling memecoins is like announcing your lottery numbers—fun if you win, cringe if you lose. #WinningTicket",
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
