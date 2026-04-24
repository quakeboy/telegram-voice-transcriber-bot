import logging
import logging.handlers
import os
from pathlib import Path


def setup_logger(log_folder: str, log_level: str = "INFO") -> logging.Logger:
    """Setup logger with file and console handlers."""
    Path(log_folder).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("transcriber")
    logger.setLevel(getattr(logging, log_level))

    if logger.handlers:
        return logger

    log_file = os.path.join(log_folder, "bot.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    console_handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
