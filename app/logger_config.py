import logging
import sys
import os

def setup_logger(name: str = "search_app", level=logging.INFO) -> logging.Logger:
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()  # убираем дубли, если повторный вызов
    logger.addHandler(handler)
    logger.propagate = False

    return logger
