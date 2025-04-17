import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from logger import logger
from organizer import classer_fichier_par_type, supprimer_doublons

class FolderHandler(FileSystemEventHandler):
    def __init__(self, path, delai_execution=30):
        self.path = path
        self.derniere_execution = 0
        self.delai_execution = delai_execution  # en secondes

    def on_modified(self, event):
        if not event.is_directory:
            maintenant = time.time()
            if maintenant - self.derniere_execution > self.delai_execution:
                logger.info(f"🔄 Organisation declenchee pour : {self.path}")
                classer_fichier_par_type(self.path)
                supprimer_doublons(self.path)
                logger.info("✅ Organisation terminee.")
                self.derniere_execution = maintenant
            else:
                logger.info("⏱️ Modification detectee mais attente du delai avant la prochaine organisation.")

def demarrer_surveillance(path):
    if not os.path.exists(path):
        logger.error(f"❌ Le chemin {path} n'existe pas.")
        return

    event_handler = FolderHandler(path)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()

    logger.info(f"👁️ Surveillance activee sur le dossier : {path}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Surveillance arrêtée.")
        observer.stop()
    observer.join()
