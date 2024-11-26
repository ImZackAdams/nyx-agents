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

import re

def clean_text(text):
    """
    Cleans text by removing unnecessary elements such as hashtags, mentions, URLs, 
    excessive whitespace, and unnecessary quotation marks. Also improves readability 
    by fixing punctuation spacing, capitalization, and formatting.

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
    # Remove special characters except basic punctuation
    text = re.sub(r"[^a-zA-Z0-9\s.,!?']", "", text)
    # Remove unnecessary quotation marks (leading and trailing)
    text = text.strip('"').strip("'")
    # Fix spacing around punctuation
    text = re.sub(r"([.,!?])([A-Za-z])", r"\1 \2", text)  # Ensure space after punctuation
    # Add spacing for camel-cased words (e.g., "BlockChain" → "Block Chain")
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Capitalize first letter of each sentence
    sentences = re.split(r'([.!?])', text)  # Split into sentences with punctuation
    cleaned_sentences = [s.capitalize() if i % 2 == 0 else s for i, s in enumerate(sentences)]
    text = ''.join(cleaned_sentences)

    return text

