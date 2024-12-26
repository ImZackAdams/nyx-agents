# Bot configuration constants

# Content type chances
NEWS_POSTING_CHANCE = 0.40   # 20% chance to check and post news
MEME_POSTING_CHANCE = 0.20   # 20% chance to post memes

# Meme settings
SUPPORTED_MEME_FORMATS = ('.jpg', '.jpeg', '.png', '.gif', 'JPG')
MEMES_FOLDER_NAME = 'memes'  # relative to cwd

# Reply settings
REPLY_DELAY_SECONDS = 60      # Delay between individual replies
REPLIES_PER_CYCLE = 5       # Number of replies to process per check
REPLY_CYCLES = 3          # Number of 15-minute cycles

# Tweet generation settings
MAX_TWEET_LENGTH = 240
MIN_TWEET_LENGTH = 80
SUMMARY_MIN_LENGTH = 100  # Add this
SUMMARY_MAX_LENGTH = 500  # Add this
MAX_GENERATION_ATTEMPTS = 10
MAX_PROMPT_ATTEMPTS = 3      # Number of different prompts to try before fallback


# Timing settings (all in seconds)
POST_COOLDOWN = 60 * 30      # 1 hour between posts
RETRY_DELAY = 60 * 2        # 15 minutes retry delay
INITIAL_REPLY_DELAY = 60 * 8  # Wait 10 minutes after posting
REPLY_CYCLE_DELAY = 60 * 8    # 15 minutes between reply cycles
FINAL_CHECK_DELAY = 60 * 40    # 1 hour wait before final check