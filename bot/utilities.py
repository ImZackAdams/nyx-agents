import logging
import psutil
import torch
import re

def setup_logging():
    """Set up logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def log_resource_usage(logger):
    """Log resource usage (CPU, RAM, GPU)."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    logger.info(f"CPU Usage: {cpu_percent}% | RAM Usage: {memory_percent}%")

    if torch.cuda.is_available():
        gpu_memory = torch.cuda.memory_allocated() / 1024 / 1024
        gpu_utilization = torch.cuda.utilization()
        logger.info(f"GPU Memory Usage: {gpu_memory} MB | GPU Utilization: {gpu_utilization}%")

def clean_text(text):
    """
    Cleans text by removing unnecessary elements such as hashtags, mentions, URLs, 
    excessive whitespace, and unnecessary quotation marks.

    Args:
        text (str): The text to clean.

    Returns:
        str: The cleaned text.
    """
    # Remove mentions (@username)
    text = re.sub(r"@\w+", "", text)
    # Remove hashtags (#hashtag)
    text = re.sub(r"#\w+", "", text)
    # Remove URLs
    text = re.sub(r"http\S+", "", text)
    # Remove special characters except punctuation
    text = re.sub(r"[^a-zA-Z0-9\s.,!?']", "", text)
    # Remove unnecessary quotation marks
    text = re.sub(r"[\"“”]", "", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text
