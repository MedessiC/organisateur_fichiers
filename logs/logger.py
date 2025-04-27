
# Ce fichier est responsable de la configuration du logger pour l'application.
# Il configure le logger pour écrire les logs dans un fichier et sur la console.
# Il crée également un dossier pour les logs s'il n'existe pas déjà.

#
# logger.py

import logging
import os
from datetime import datetime

def setup_logger(name="organizer"):
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    log_filename = datetime.now().strftime("%Y-%m-%d") + ".log"
    log_path = os.path.join(log_dir, log_filename)

    log_format = "[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        console_handler = logging.StreamHandler()

        formatter = logging.Formatter(log_format, date_format)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

logger = setup_logger()

