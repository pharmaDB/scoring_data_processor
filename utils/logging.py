import logging

_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def getLogger(name, level=logging.INFO):

    # Set up console log handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter(_FORMAT))

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(ch)
    return logger
