# bot/initializers.py
import os
import logging
import torch
import tweepy
import bitsandbytes as bnb
from diffusers import StableDiffusionPipeline

def _env_bool(name: str, default: str = "0") -> bool:
    value = os.getenv(name, default).strip().lower()
    return value in ("1", "true", "yes", "on")


def validate_env_variables(logger: logging.Logger):
    """Validate that all required environment variables are present."""
    if _env_bool("SKIP_TWITTER_VALIDATION", "0"):
        logger.info("Skipping Twitter credential validation (SKIP_TWITTER_VALIDATION=1).")
        return
    required_pairs = [
        ("API_KEY", "TWITTER_API_KEY"),
        ("API_SECRET", "TWITTER_API_SECRET"),
        ("ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN"),
        ("ACCESS_TOKEN_SECRET", "TWITTER_ACCESS_SECRET"),
    ]
    missing = [a for a, b in required_pairs if not (os.getenv(a) or os.getenv(b))]
    if missing or not os.getenv("BOT_USER_ID"):
        missing_vars = missing + ([] if os.getenv("BOT_USER_ID") else ["BOT_USER_ID"])
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

def setup_twitter_api() -> tweepy.API:
    """Set up and return a Twitter API client."""
    auth = tweepy.OAuth1UserHandler(
        consumer_key=os.getenv('API_KEY') or os.getenv("TWITTER_API_KEY"),
        consumer_secret=os.getenv('API_SECRET') or os.getenv("TWITTER_API_SECRET"),
        access_token=os.getenv('ACCESS_TOKEN') or os.getenv("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.getenv('ACCESS_TOKEN_SECRET') or os.getenv("TWITTER_ACCESS_SECRET")
    )
    return tweepy.API(auth)

def initialize_diffusion_pipeline(logger: logging.Logger):
    """Initialize the Stable Diffusion pipeline with 8-bit optimization."""
    logger.info("Initializing Stable Diffusion pipeline...")

    # 1. Absolute path to your local Stable Diffusion model folder
    # Allow override via environment variable for different machines.
    model_path = os.getenv("SD_MODEL_PATH")
    if not model_path:
        # Default to repo-relative path if not provided.
        src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(src_dir, "ml", "image", "sd2_model")

    # 2. Check if the directory actually exists
    if not os.path.isdir(model_path):
        raise FileNotFoundError(f"Local model folder not found at: {model_path}")

    # 3. Force local loading so HF does NOT treat model_path as a remote repo
    pipe = StableDiffusionPipeline.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        local_files_only=True
    ).to("cuda")

    # 4. Convert text encoder weights to 8-bit using bitsandbytes
    for name, module in pipe.text_encoder.named_modules():
        if hasattr(module, 'weight') and module.weight is not None and module.weight.dtype == torch.float16:
            module.weight = bnb.nn.Int8Params(module.weight.data, requires_grad=False)

    return pipe
