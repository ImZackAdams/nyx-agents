"""
Utility functions for resource monitoring, logging, and model management.
Provides decorators and helper functions for the Athena bot.
"""

import os
import psutil
import torch
import functools
import time
from typing import Callable, Any, Dict
import logging
from datetime import datetime

def setup_logger(name: str, log_dir: str = "logs") -> logging.Logger:
    """
    Set up a logger with file and console handlers.
    Args:
        name (str): Name for the logger
        log_dir (str): Directory to store log files
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

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

    return logger

def get_gpu_memory_usage() -> Dict[str, float]:
    """
    Get current GPU memory usage information.
    Returns:
        dict: Dictionary containing GPU memory statistics
    """
    if not torch.cuda.is_available():
        return {"gpu_available": False}

    try:
        gpu_memory = {
            "gpu_available": True,
            "allocated_memory": torch.cuda.memory_allocated() / 1024**3,  # GB
            "cached_memory": torch.cuda.memory_reserved() / 1024**3,      # GB
            "total_memory": torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
        }
        return gpu_memory
    except Exception as e:
        return {
            "gpu_available": True,
            "error": str(e)
        }

def get_system_metrics() -> Dict[str, float]:
    """
    Get current system resource usage metrics.
    Returns:
        dict: Dictionary containing system resource metrics
    """
    process = psutil.Process()
    
    try:
        metrics = {
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "memory_usage": process.memory_info().rss / 1024**2,  # MB
            "num_threads": process.num_threads(),
            "system_memory_percent": psutil.virtual_memory().percent
        }
        
        # Add GPU metrics if available
        gpu_metrics = get_gpu_memory_usage()
        metrics.update(gpu_metrics)
        
        return metrics
    except Exception as e:
        return {"error": str(e)}

def log_resource_usage(func: Callable) -> Callable:
    """
    Decorator to log resource usage before and after function execution.
    Args:
        func (Callable): Function to wrap
    Returns:
        Callable: Wrapped function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get self.logger from the class instance
        logger = args[0].logger if args and hasattr(args[0], 'logger') else logging.getLogger()
        
        # Log start metrics
        start_time = time.time()
        start_metrics = get_system_metrics()
        logger.debug(f"Starting {func.__name__} - Resource usage: {start_metrics}")
        
        try:
            # Execute the function
            result = func(*args, **kwargs)
            
            # Log end metrics
            end_time = time.time()
            end_metrics = get_system_metrics()
            execution_time = end_time - start_time
            
            # Calculate resource usage differences
            metrics_diff = {
                key: end_metrics[key] - start_metrics[key]
                for key in start_metrics
                if isinstance(start_metrics[key], (int, float)) and
                   isinstance(end_metrics[key], (int, float))
            }
            
            logger.debug(
                f"Completed {func.__name__} - "
                f"Execution time: {execution_time:.2f}s - "
                f"Resource usage change: {metrics_diff}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
            
    return wrapper

def cleanup_gpu_memory() -> None:
    """
    Clean up GPU memory by emptying cache and garbage collection.
    """
    if torch.cuda.is_available():
        try:
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        except Exception as e:
            logging.error(f"Error cleaning GPU memory: {e}")

class ResourceMonitor:
    """Class for monitoring system resources during model operations."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.start_metrics = None
        self.end_metrics = None
        self.start_time = None
        
    def __enter__(self):
        """Start monitoring resources."""
        self.start_time = time.time()
        self.start_metrics = get_system_metrics()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log resource usage on exit."""
        end_time = time.time()
        self.end_metrics = get_system_metrics()
        
        execution_time = end_time - self.start_time
        
        # Calculate metrics differences
        metrics_diff = {
            key: self.end_metrics[key] - self.start_metrics[key]
            for key in self.start_metrics
            if isinstance(self.start_metrics[key], (int, float)) and
               isinstance(self.end_metrics[key], (int, float))
        }
        
        self.logger.debug(
            f"Resource usage summary:\n"
            f"Execution time: {execution_time:.2f}s\n"
            f"Resource changes: {metrics_diff}"
        )
        
        if exc_type is not None:
            self.logger.error(f"Error occurred: {exc_val}")
            
        # Cleanup
        cleanup_gpu_memory()