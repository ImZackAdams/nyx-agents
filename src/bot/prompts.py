from typing import Dict, List

# --------------------------------
# 0) Disclaimers or Intro Text
# --------------------------------

DISCLAIMER_TEXT = (
    "⚠️ Not financial advice. Also not emotional support. "
    "Expect savage, comedic, crypto-based reality checks. ⚠️"
)

# --------------------------------
# 1) General Web3 & Crypto Educational
# --------------------------------
GENERAL_CRYPTO_EDUCATIONAL: List[str] = [
    "Web3 pro tip: 'decentralization' means no single entity’s in charge—like a group project with no teacher to blame. #ChainGang",
    "Blockchain 101: think of it as a giant, public notebook everyone can read but no one can secretly erase. #DigitalReceipts",
    "Ever wonder why ‘consensus’ matters? It’s the fancy way of saying ‘we all agree, so no one can cheat the system.’ #NoCheatersAllowed",
    "Crypto security rule: never share your private key. It’s like your diary password—except, losing it can cost you more than middle-school gossip. #LockItDown",
    "Want in on Web3? Start by learning how to read a block explorer. It’s basically peeking behind the curtain of the next financial revolution. #Peekaboo",
]

# --------------------------------
# 2) NFTs & Tokenized Assets
# --------------------------------
NFT_PROMPTS: List[str] = [
    "NFTs: digital collectible or overpriced JPEG? Depends on whether you’re flipping them or cluelessly hogging them. #Perspective",
    "Just minted an NFT? Congratulations, you now own something intangible that’s verifiably yours—like adopting a digital Tamagotchi. #90sThrowback",
    "Gas fees on that NFT? Think of it as the cost of entry to an exclusive blockchain club where everyone’s flexing pixel art. #PriceOfFame",
    "NFT utility is the future—imagine concert tickets, real estate deeds, or proof of authenticity on-chain. Bragging rights included. #SmartAssets",
    "If ‘metadata’ sounds boring, just remember it’s basically your NFT’s birth certificate. Keep it safe, or watch it vanish. #BlockchainBasics",
]

# --------------------------------
# 3) DeFi & Tokens
# --------------------------------
DEFI_TOKENS_PROMPTS: List[str] = [
    "DeFi = finance, but with more freedom and fewer suits. Just don’t confuse ‘fewer suits’ with ‘less risk.’ #EyesOpen",
    "Yield farming: fancy name for chasing juicy returns in digital fields. Harvest carefully, or watch your crops vanish. #CropCircles",
    "Stablecoins keep the wild west of crypto from going full stampede—peg ‘em right, or watch the meltdown. #SteadyAsSheGoes",
    "Liquidity pools: you throw in tokens, earn fees—like renting out your car. But if the market swerves, you might get back a unicycle. #ImpermanentLoss",
    "Tokenomics: the science of making sure your coin isn't just Monopoly money. Print too many, and the market will laugh you out. #BalanceIsKey",
]

# --------------------------------
# 4) Memecoins & Sassy Remarks
# --------------------------------
MEME_CAPTIONS: List[str] = [
    "Memecoins: where internet culture meets speculation. Ride the hype wave or get dunked on by the next dog-themed craze. #WoofWoof",
    "$TBALL soared again? Either jump aboard or keep mocking from the sidelines—nobody regrets gains but the gainsless. #HindsightHurts",
    "Here’s a hot tip: if your memecoin pitch is just 'trust me, bro,' might wanna read an actual whitepaper. #DueDiligence",
    "Some say memecoins are worthless. Tell that to the folks who retired on a dog coin. Probability is savage, but luck’s always a wildcard. #DontBlink",
    "Shilling memecoins is like telling everyone your lottery numbers. Fun if you win, cringe if you lose. #WinningTicket",
]

# --------------------------------
# 5) Fallback: Comedic Disclaimers & Misc
# --------------------------------
FALLBACK_PROMPTS: List[str] = [
    "AI meltdown or market crash? Either way, pop some popcorn—you’re in for a wild ride. #EntertainmentValue",
    "Before you get triggered by roasts, remember: block confirmations don’t care about your feelings. #RealityCheck",
    "If you’re not into harsh truths, maybe this isn’t the droid you’re looking for. #SassyAndIKnowIt",
    "Crypto or code drama—both can wreck your day. At least $TBALL might cheer you up with a 10x. #LifeLine",
    "If you can’t handle high gas fees and savage tweets, maybe stick to collecting vintage stamps. #LowVolatility",
]

def get_all_prompts() -> Dict[str, List[str]]:
    """
    Returns all available prompts organized by category. 
    They aim to produce standalone tweet content that’s:
    - Educational: Explaining crypto/Web3 concepts in plain English.
    - Funny: Inject humor and sass to keep it engaging.
    - Interactive: Encouraging user replies, retweets, and likes.

    Categories:
    - general_crypto_educational: Basic but snappy crypto & blockchain insights.
    - nft_prompts: For those exploring NFTs and their use cases.
    - defi_tokens_prompts: DeFi strategies, tips, and comedic warnings.
    - memecoin_prompts: Memecoins, hype cycles, and savage one-liners.
    - fallback_prompts: General disclaimers, comedic roasts, and quick saves.

    Disclaimer: 
      Not financial advice. Not emotional support.
      Use at your own risk—some tweets may cause excitement or confusion.
    """
    return {
        'general_crypto_educational': GENERAL_CRYPTO_EDUCATIONAL,
        'nft_prompts': NFT_PROMPTS,
        'defi_tokens_prompts': DEFI_TOKENS_PROMPTS,
        'memecoin_prompts': MEME_CAPTIONS,
        'fallback_prompts': FALLBACK_PROMPTS,
    }
