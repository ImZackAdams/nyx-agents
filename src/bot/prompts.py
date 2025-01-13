from typing import Dict, List

# --------------------------------
# 1) General Web3 & Crypto Educational
# --------------------------------
GENERAL_CRYPTO_EDUCATIONAL: List[str] = [
    "Web3 pro tip: 'decentralization' is like a class with no teacher—everyone’s in charge, and $TBALL aces the final.",
    "Blockchain 101: an open ledger where $TBALL carves its name. Because some drama’s best immortalized on-chain.",
    "Ever wonder why ‘consensus’ matters? It’s how $TBALL and everyone else agree, so scammers can’t sneak in.",
    "Crypto security rule: never share your private key. That’s like handing over your $TBALL fortune—good luck getting it back.",
    "Eyeing Web3? Start with a block explorer. Peek behind the curtain and see where $TBALL fits into the next financial revolution.",
]

# --------------------------------
# 2) NFTs & Tokenized Assets
# --------------------------------
NFT_PROMPTS: List[str] = [
    "NFTs: digital collectibles or pricey JPEGs? If it’s tied to $TBALL, it’s a trophy worth showing off.",
    "Just minted an NFT backed by $TBALL? Enjoy that intangible flex—like adopting a Tamagotchi, but with actual value.",
    "Gas fees? Think of them as the cover charge to the exclusive $TBALL NFT club. Bragging rights included.",
    "NFT utility is the future—concert tickets, real estate deeds, proof of authenticity. $TBALL is the VIP pass you didn’t know you needed.",
    "If ‘metadata’ sounds dull, remember it’s your NFT’s on-chain ID. Lose it, and kiss your $TBALL masterpiece goodbye.",
]

# --------------------------------
# 3) DeFi & Tokens
# --------------------------------
DEFI_TOKENS_PROMPTS: List[str] = [
    "DeFi = more freedom, fewer middlemen. But fewer middlemen ≠ zero risk. Keep your $TBALL stash close.",
    "Yield farming: a fancy term for chasing juicy returns in digital fields. Harvest your $TBALL or watch it vanish.",
    "Stablecoins keep the market from going full stampede. But if they lose their peg, $TBALL stands tall anyway.",
    "Liquidity pools: toss in tokens for fees—like renting out your ride. Just don’t forget your $TBALL seatbelt in case of a market swerve.",
    "Tokenomics: the science behind $TBALL’s growth, so it never becomes Monopoly money. Print responsibly, or the market laughs.",
]

# --------------------------------
# 4) Memecoins & Sassy Remarks
# --------------------------------
MEME_CAPTIONS: List[str] = [
    "When $TBALL says 'Built Different,' it means we’re here to meme and dream. 🚀",
    "Swing with $TBALL or stay dusty—this train doesn’t wait for permission.",
    "Some coins brag about utility; $TBALL brags about fun (and maybe a moon trip, too). 💅",
    "Ready to swing with $TBALL? You might find your portfolio doing a happy dance.",
    "Board the $TBALL rocket for a wild ride—we’re packing memes and ambition. 😏",
    "Swing with us on $TBALL’s epic journey. Because if it ain’t different, it ain’t worth memeing. 💥",
    "Built different? That’s $TBALL’s daily anthem. Wave goodbye to mundane coins—meme magic incoming. ✨",
    "Bet on $TBALL chaos, because where there’s madness, there’s moon potential!",
    "If your memecoin can’t handle the heat, $TBALL’s got the oven cranked to max. 😎",
    "Built different and proud—$TBALL turns doubters into daydreamers. Swing with us if you dare! 💅",
    "Watching $TBALL blast off? Jump aboard or watch from the sidelines—FOMO guaranteed.",
    "They called it ‘just a meme.’ We call it $TBALL because humor pairs well with gains.",
    "If FOMO had a poster child, it’d be $TBALL. Grab your ticket or regret it soon. 💥",
    "We tried ‘serious’ coins. Then $TBALL came along—now the rest is rocket-fueled history.",
    "Serious faces everywhere, but $TBALL is over here printing memes…and maybe profits. 😎",
    "Need some spice in your portfolio? $TBALL is that secret sauce you’ve been missing.",
    "Who says a meme can’t run the market? $TBALL is chaos incarnate—join or miss out. 🤷‍♂️",
    "Bored of reading static charts? Let $TBALL inject a little adrenaline. Up, down—still a party! 😂",
    "Call it luck, call it fate—$TBALL just keeps batting critics out of the park.",
    "No regrets for $TBALL believers, only epic stories. Meme mania remains undefeated. 💅",
]

# --------------------------------
# 5) Fallback: Comedic Disclaimers & Misc
# --------------------------------
FALLBACK_PROMPTS: List[str] = [
    "AI meltdown or market crash? At least your $TBALL memes stay priceless.",
    "Triggered by roasts? Don’t forget: block confirmations—and $TBALL growth—don’t care about feelings.",
    "Not into harsh truths? $TBALL says embrace the chaos or step aside.",
    "Crypto or code drama—both can wreck your day, but $TBALL could 10x. Silver linings, people.",
    "High gas fees + savage tweets = normal here. If you can’t handle it, go collect stamps. $TBALL thrives in the heat.",
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
