import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

log = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

LOGFORMAT = "%(asctime)s [%(levelname)-4s] %(filename)s:%(lineno)s > %(message)s"
LOGLEVEL = os.getenv("LOG_LEVEL", "DEBUG")
log.setLevel(LOGLEVEL)
formatter = logging.Formatter(LOGFORMAT)

consoleHandler = logging.StreamHandler(stream=sys.stdout)
consoleHandler.setFormatter(formatter)
log.addHandler(consoleHandler)

# Create a file handler in the "log" directory
if not os.path.exists("log"):
    os.mkdir("log")
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
file_handler = logging.FileHandler(f"log/{current_time}.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Add the file handler to the logger
log.addHandler(file_handler)

def close_log():
    log.removeHandler(file_handler)
    file_handler.close()
