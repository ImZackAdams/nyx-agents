# src/bot/initializers.py
import os
import logging
import torch
import tweepy
import bitsandbytes as bnb
from diffusers import StableDiffusionPipeline


def validate_env_variables(logger: logging.Logger):
    """Validate that all required environment variables are present."""
    required_vars = ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET", "BOT_USER_ID"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")


def setup_twitter_api() -> tweepy.API:
    """Set up and return a Twitter API client."""
    auth = tweepy.OAuth1UserHandler(
        consumer_key=os.getenv('API_KEY'),
        consumer_secret=os.getenv('API_SECRET'),
        access_token=os.getenv('ACCESS_TOKEN'),
        access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
    )
    return tweepy.API(auth)


def initialize_diffusion_pipeline(logger: logging.Logger):
    """Initialize the Stable Diffusion pipeline with 8-bit optimization."""
    logger.info("Initializing Stable Diffusion pipeline...")
    pipe = StableDiffusionPipeline.from_pretrained(
        "./sd2_model", torch_dtype=torch.float16
    ).to("cuda")

    for name, module in pipe.text_encoder.named_modules():
        if hasattr(module, 'weight') and module.weight is not None and module.weight.dtype == torch.float16:
            module.weight = bnb.nn.Int8Params(module.weight.data, requires_grad=False)

    return pipe