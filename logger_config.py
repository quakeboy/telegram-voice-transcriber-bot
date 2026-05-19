import logging
import logging.handlers
import os
from pathlib import Path


def setup_logger(log_folder: str, log_level: str = "INFO", log_name: str = "bot") -> logging.Logger:
    """Setup logger with file and console handlers.

    Args:
        log_folder: Directory for log files
        log_level: Logging level (INFO, DEBUG, etc.)
        log_name: Logger and log file name (e.g. "bot" for bot.log, "transcriber_worker" for transcriber_worker.log)
    """
    Path(log_folder).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(log_name)
    logger.setLevel(getattr(logging, log_level))
    logger.propagate = False

    # Clear any existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    log_file = os.path.join(log_folder, f"{log_name}.log")
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger
