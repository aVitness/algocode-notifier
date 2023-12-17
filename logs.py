import logging
import sys

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("[%(levelname)s %(asctime)s] %(message)s", datefmt='%m.%d %H:%M:%S')
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(formatter)

file_handler = logging.FileHandler('logs/logs.log', mode='a', encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stdout_handler)
