# src/bot/initializers.py
import os
import logging
import torch
import bitsandbytes as bnb
from diffusers import StableDiffusionPipeline

def validate_env_variables(logger: logging.Logger):
    required_vars = ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_TOKEN_SECRET", "BOT_USER_ID"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

def initialize_diffusion_pipeline(logger: logging.Logger):
    logger.info("Initializing Stable Diffusion pipeline...")
    pipe = StableDiffusionPipeline.from_pretrained(
        "./sd2_model", torch_dtype=torch.float16
    ).to("cuda")

    for name, module in pipe.text_encoder.named_modules():
        if hasattr(module, 'weight') and module.weight is not None and module.weight.dtype == torch.float16:
            module.weight = bnb.nn.Int8Params(module.weight.data, requires_grad=False)

    return pipe
