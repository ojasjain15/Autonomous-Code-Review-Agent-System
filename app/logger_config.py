import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict

class LoggerManager:
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.loggers: Dict[str, logging.Logger] = {}

    def _create_handler(self, log_file: str) -> RotatingFileHandler:
        log_path = self.log_dir / log_file
        handler = RotatingFileHandler(
            log_path,
            maxBytes=10_000_000,
            backupCount=5
        )
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        return handler

    def get_logger(
        self,
        name: str,
        log_file: str,
        level: int = logging.INFO
    ) -> logging.Logger:
        logger_key = f"{name}_{log_file}"
        if logger_key in self.loggers:
            return self.loggers[logger_key]
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.handlers = []
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(console_handler)
        logger.addHandler(self._create_handler(log_file))
        self.loggers[logger_key] = logger
        return logger

    def cleanup(self):
        for logger in self.loggers.values():
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        self.loggers.clear()

_manager = LoggerManager()

def get_logger(
    name: str,
    log_file: str,
    level: int = logging.INFO
) -> logging.Logger:
    return _manager.get_logger(name, log_file, level)

def cleanup_logging():
    _manager.cleanup()
