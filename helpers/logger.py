import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

LOG_DIR = PROJECT_ROOT / "Backend" / "Logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

class LoggingSystem():

    app = logging.getLogger("app")
    app.setLevel(logging.INFO)
    cleanup = logging.getLogger("cleanUp")
    cleanup.setLevel(logging.INFO)

    @classmethod
    def configureLogger(cls, logger: logging.Logger, filename: str):
        if not logger.handlers:
            # File handler
            file_handler = logging.FileHandler(LOG_DIR / f"{filename}.log")
            file_handler.setLevel(logging.INFO)

            # Formatter
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)

            # File handler
            logger.addHandler(file_handler)

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

    def __init__(self):
        self.app = LoggingSystem.app
        self.cleanup = LoggingSystem.cleanup

LoggingSystem.configureLogger(LoggingSystem.app, "app")
LoggingSystem.configureLogger(LoggingSystem.cleanup, "cleanUp")