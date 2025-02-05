from typing import Dict, List



# --------------------------------
# 1) General Web3 & Crypto Educational
# --------------------------------
GENERAL_CRYPTO_EDUCATIONAL: List[str] = [
    "Web3 101: It's like a group project with no teacher. Everyone picks the final grade—and $TBALL is the valedictorian.",
    "Think of blockchain as a gossip train that never forgets. Good news: $TBALL’s riding it to fame and glory.",
    "Wonder why ‘consensus’ matters? It’s basically the entire squad agreeing you aren’t a scammer. $TBALL says you’re good.",
    "Crypto security rule: flaunting your private key is like tweeting your debit card PIN—kiss your $TBALL goodbye.",
    "New to Web3? Grab a block explorer and go cryptid-hunting. If you spot $TBALL, it’s the friendliest beast on-chain."
]

# --------------------------------
# 2) NFTs & Tokenized Assets
# --------------------------------
NFT_PROMPTS: List[str] = [
    "NFTs: million-dollar memes or pixel Mona Lisas? If they’re backed by $TBALL, they’re works of genius (obviously).",
    "Minting an NFT is like adopting a Tamagotchi that won’t die. Especially if it’s powered by $TBALL—long live your digital pet.",
    "Gas fees: the cover charge for that exclusive NFT club. But inside, you can flash your $TBALL bling with pride.",
    "One day your concert ticket, real estate deed, and dog’s pedigree might all be NFTs. $TBALL is the ultimate VIP pass you didn’t know you needed.",
    "‘Metadata’ sounds dull, but it’s your NFT’s backstage pass. Lose it, and your $TBALL collectible is just a sad, empty wallet."
]

# --------------------------------
# 3) DeFi & Tokens
# --------------------------------
DEFI_TOKENS_PROMPTS: List[str] = [
    "DeFi: Because sometimes you just gotta fire your bank and become your own money wizard—$TBALL wand in hand.",
    "Yield farming is planting digital seeds in hopes of sprouting more coins. Just don’t forget to water your $TBALL stash.",
    "Stablecoins keep the crypto zoo from becoming a circus. If they break the cage, hold onto your $TBALL for dear life.",
    "Liquidity pools: toss in tokens, collect fees—kind of like hosting a backyard party and charging for the grill. Keep your $TBALL on the table.",
    "Tokenomics is the secret recipe for $TBALL’s success. Print too much, and the market turns it into stale Monopoly money."
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
