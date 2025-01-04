from typing import Dict, List

# --------------------------------
# 1) General Web3 & Crypto Educational
# --------------------------------
GENERAL_CRYPTO_EDUCATIONAL: List[str] = [
    "Web3 pro tip: 'decentralization' means no single entity is in charge—like a group project with no teacher to blame. #ChainGang",
    "Blockchain 101: think of it as a giant, public notebook everyone can read but nobody can secretly erase. #DigitalReceipts",
    "Ever wonder why ‘consensus’ matters? It’s the fancy way of saying, ‘We all agree, so no one can cheat the system.’ #NoCheatersAllowed",
    "Crypto security rule: never share your private key—it’s like your diary password, except losing it can cost you way more than middle-school gossip. #LockItDown",
    "Want in on Web3? Learn to read a block explorer. It’s basically peeking behind the curtain of the next financial revolution. #Peekaboo",
]

# --------------------------------
# 2) NFTs & Tokenized Assets
# --------------------------------
NFT_PROMPTS: List[str] = [
    "NFTs: digital collectible or overpriced JPEG? Depends on whether you’re flipping them or cluelessly hogging them. #Perspective",
    "Just minted an NFT? Congrats—you own something intangible that’s verifiably yours, like a digital Tamagotchi. #90sThrowback",
    "Gas fees on that NFT? Think of it as the cost of entry to an exclusive blockchain club where everyone’s flexing pixel art. #PriceOfFame",
    "NFT utility is the future—imagine concert tickets, real estate deeds, and proof of authenticity on-chain. Bragging rights included. #SmartAssets",
    "If ‘metadata’ sounds boring, remember it’s basically your NFT’s birth certificate. Keep it safe, or watch it vanish. #BlockchainBasics",
]

# --------------------------------
# 3) DeFi & Tokens
# --------------------------------
DEFI_TOKENS_PROMPTS: List[str] = [
    "DeFi = finance with more freedom and fewer suits. Just don’t confuse ‘fewer suits’ with ‘less risk.’ #EyesOpen",
    "Yield farming: fancy name for chasing juicy returns in digital fields. Harvest carefully, or watch your crops vanish. #CropCircles",
    "Stablecoins keep crypto from going full stampede—peg ‘em right, or watch the meltdown. #SteadyAsSheGoes",
    "Liquidity pools: you throw in tokens, earn fees—like renting out your car. But if the market swerves, you might end up with a unicycle. #ImpermanentLoss",
    "Tokenomics: the science of making sure your coin isn’t Monopoly money. Print too many, and the market will laugh you out. #BalanceIsKey",
]

# --------------------------------
# 4) Memecoins & Sassy Remarks
# --------------------------------
MEME_CAPTIONS: List[str] = [
    "Memecoins: where internet culture meets speculation. Ride the hype wave or get dunked on by the next dog-themed craze. #WoofWoof",
    "$TBALL soared again? Either jump aboard or keep mocking from the sidelines—nobody regrets gains but the gainsless. #HindsightHurts",
    "Here’s a tip: if your memecoin pitch is just 'trust me, bro,' you might wanna skim the whitepaper. #DueDiligence",
    "Some say memecoins are worthless. Tell that to folks who retired on a dog coin. Probability is savage, luck’s always a wildcard. #DontBlink",
    "Shilling memecoins is like telling everyone your lottery numbers—fun if you win, cringe if you lose. #WinningTicket",
]

# --------------------------------
# 5) Fallback: Comedic Disclaimers & Misc
# --------------------------------
FALLBACK_PROMPTS: List[str] = [
    "AI meltdown or market crash? Either way, grab popcorn—you’re in for a ride. #EntertainmentValue",
    "Before you get triggered by roasts, remember: block confirmations don’t care about your feelings. #RealityCheck",
    "If you’re not into harsh truths, maybe this isn’t the droid you’re looking for. #SassyAndIKnowIt",
    "Crypto or code drama—both can wreck your day. At least $TBALL might cheer you up with a 10x. #LifeLine",
    "If you can’t handle high gas fees and savage tweets, consider collecting vintage stamps. #LowVolatility",
]


def get_all_prompts() -> Dict[str, List[str]]:
    
    return {
        'general_crypto_educational': GENERAL_CRYPTO_EDUCATIONAL,
        'nft_prompts': NFT_PROMPTS,
        'defi_tokens_prompts': DEFI_TOKENS_PROMPTS,
        'memecoin_prompts': MEME_CAPTIONS,
        'fallback_prompts': FALLBACK_PROMPTS,
    }
