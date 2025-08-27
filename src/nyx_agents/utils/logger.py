"""
Logging configuration for the bot.
"""

import os
import logging
from datetime import datetime

# Global dict to track logger instances
LOGGERS = {}

def setup_logger(name: str, log_dir: str = "logs") -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    Args:
        name (str): Name for the logger
        log_dir (str): Directory to store log files
    Returns:
        logging.Logger: Configured logger instance
    """
    # If logger already exists, return it
    if name in LOGGERS:
        return LOGGERS[name]

    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevent propagation to root logger
    logger.propagate = False

    # Only add handlers if they haven't been added yet
    if not logger.handlers:
        # Create formatters and handlers
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # File handler - create new log file daily
        log_file = os.path.join(
            log_dir, 
            f'athena_{datetime.now().strftime("%Y%m%d")}.log'
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    # Store logger in global dict
    LOGGERS[name] = logger

    return logger

# Optional: function to get existing logger
def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger by name.
    Args:
        name (str): Name of the logger
    Returns:
        logging.Logger: Existing logger instance or None
    """
    return LOGGERS.get(name, setup_logger(name))