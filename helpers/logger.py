import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

LOG_DIR = PROJECT_ROOT / "Backend" / "Logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"

# Create a logger
logger = logging.getLogger("my_app")
logger.setLevel(logging.INFO)

# Avoid adding multiple handlers if imported multiple times
if not logger.handlers:
    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
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

