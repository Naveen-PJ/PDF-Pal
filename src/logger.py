from loguru import logger
import sys


def configure_logger():
    # Remove default handlers to avoid duplicate logs
    logger.remove()

    # Define custom colors for specific levels
    logger.level("TRACE", color="<blue>")
    logger.level("INFO", color="<green>")
    logger.level("SUCCESS", color="<green>")
    logger.level("WARNING", color="<red>")
    logger.level("ERROR", color="<red>")
    logger.level("CRITICAL", color="<red>")
    
    # Console handler (Uncomment to enable terminal output)
    logger.add(
        sys.stdout, 
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", 
        level="INFO"
    )
    
    # # File handler
    # logger.add("app.log", rotation="1 MB", retention="7 days", compression="zip", level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}")

# Run configuration once on import
configure_logger()