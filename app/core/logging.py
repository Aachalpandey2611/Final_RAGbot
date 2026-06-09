import logging
import sys
from app.core.config import settings

def setup_logging() -> None:
    # Logger level selection
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Define logging configuration
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # De-clutter external libraries output if not in debug mode
    if not settings.DEBUG:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    else:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

    # Module-level logger for import by other modules
    global logger
    logger = logging.getLogger("app")
    logger.info(f"Logging initialized with level: {logging.getLevelName(log_level)}")

# Export a module-level logger for other modules to import
# (controllers expect `from app.core.logging import logger`)
# `logger` is initialized by `setup_logging()` on app startup but available as a logger object now.
logger = logging.getLogger("app")
