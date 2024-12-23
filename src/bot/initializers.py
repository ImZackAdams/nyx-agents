# bot/initializers.py
import os
import logging
import torch
import tweepy
import bitsandbytes as bnb
from diffusers import StableDiffusionPipeline

def validate_env_variables(logger: logging.Logger):
    required_vars = ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET", "BOT_USER_ID"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

def setup_twitter_api() -> tweepy.API:
    auth = tweepy.OAuth1UserHandler(
        consumer_key=os.getenv('API_KEY'),
        consumer_secret=os.getenv('API_SECRET'),
        access_token=os.getenv('ACCESS_TOKEN'),
        access_token_secret=os.getenv('ACCESS_TOKEN_SECRET')
    )
    return tweepy.API(auth)

def initialize_diffusion_pipeline(logger: logging.Logger):
    logger.info("Initializing Stable Diffusion pipeline...")

    # Point to the *absolute* path where your model is actually stored
    model_path = "/home/athena/Desktop/athena/new_src/ml/image/sd2_model"

    # Optional check to ensure the directory exists
    if not os.path.isdir(model_path):
        raise FileNotFoundError(f"Local model folder not found at: {model_path}")

    # Force local loading so HF doesn't try to interpret the path as a repo ID
    pipe = StableDiffusionPipeline.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        local_files_only=True
    ).to("cuda")

    # Convert text encoder weights to 8-bit using bitsandbytes
    for name, module in pipe.text_encoder.named_modules():
        if hasattr(module, 'weight') and module.weight is not None and module.weight.dtype == torch.float16:
            module.weight = bnb.nn.Int8Params(module.weight.data, requires_grad=False)

    return pipe
