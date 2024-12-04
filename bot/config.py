# Bot configuration constants

# Meme settings
MEME_POSTING_CHANCE = 0.20  # 20% chance to post memes
SUPPORTED_MEME_FORMATS = ('.jpg', '.jpeg', '.png', '.gif', 'JPG')
MEMES_FOLDER_NAME = 'memes'  # relative to cwd

# Reply settings
REPLY_DELAY_SECONDS = 2
REPLIES_PER_CYCLE = 3    # Number of replies to process in each cycle

# Tweet generation settings
MAX_TWEET_LENGTH = 220
MIN_TWEET_LENGTH = 100
MAX_GENERATION_ATTEMPTS = 5

# Timing settings
POST_COOLDOWN = 60 * 90  # 90 minutes
RETRY_DELAY = 60 * 15    # 15 minutes