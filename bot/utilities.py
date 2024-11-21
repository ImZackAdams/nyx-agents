import logging
import psutil
import torch

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
