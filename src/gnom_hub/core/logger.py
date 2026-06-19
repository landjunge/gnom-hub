import logging
import sys

def setup_logging(level: str = "INFO") -> logging.Logger:
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
    return logging.getLogger(f"gnom_hub.{name}")
