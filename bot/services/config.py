# Bot configuration constants

# Meme settings
MEME_POSTING_CHANCE = 0.20  # 20% chance to post memes
SUPPORTED_MEME_FORMATS = ('.jpg', '.jpeg', '.png', '.gif', 'JPG')
MEMES_FOLDER_NAME = 'memes'  # relative to cwd

# Reply settings
REPLY_DELAY_SECONDS = 2      # Delay between individual replies
REPLIES_PER_CYCLE = 3        # Number of replies to process per check
REPLY_CYCLES = 3             # Number of 15-minute cycles

# Tweet generation settings
MAX_TWEET_LENGTH = 180
MIN_TWEET_LENGTH = 80
MAX_GENERATION_ATTEMPTS = 5
MAX_PROMPT_ATTEMPTS = 3      # Number of different prompts to try before fallback

# Timing settings (all in seconds)
POST_COOLDOWN = 60 * 60      # 1 hour between posts
RETRY_DELAY = 60 * 15        # 15 minutes retry delay
INITIAL_REPLY_DELAY = 60 * 10  # Wait 10 minutes after posting
REPLY_CYCLE_DELAY = 60 * 15    # 15 minutes between reply cycles
FINAL_CHECK_DELAY = 60 * 60    # 1 hour wait before final check