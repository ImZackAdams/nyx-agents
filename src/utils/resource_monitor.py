import psutil
import torch
import functools
import time
import logging
from typing import Callable, Dict

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
        # Get self.logger from the class instance if available
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
