"""Centralized logging configuration for Gnom-Hub."""
import logging
import sys

def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the root gnom-hub logger."""
    logger = logging.getLogger("gnom_hub")
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    ))
    logger.addHandler(handler)
    return logger

def get_logger(name: str) -> logging.Logger:
    """Get a child logger for a specific module."""
    return logging.getLogger(f"gnom_hub.{name}")
