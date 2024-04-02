import logging

from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = "INFO"
        logger.opt(exception=record.exc_info).log(level, record.getMessage())


def intercept_logging():
    """
    Replaces logging handlers with a loguru intercept
    """
    intercept_handler = InterceptHandler()
    # Redirect all stdlib loggers loggers to the intercept handler
    for logger_name in logging.root.manager.loggerDict:
        found_logger = logging.getLogger(logger_name)
        found_logger.handlers = [intercept_handler]
