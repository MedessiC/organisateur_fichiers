import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
from organizer import classer_fichier_par_type,creer_dossier_si_absent

class FolderHandler(FileSystemEventHandler):
    def on_modified(self, event):
        # Vérifier si le dossier a été modifié
        print(f"Changement détecté : {event.src_path}")
        # Appeler le script organizer.py
        classer_fichier_par_type(path)

if __name__ == "__main__":
    path = "c:\\Users\\Medessi Cvi\\Desktop\\TT" # Remplacez avec le chemin de votre dossier
    event_handler = FolderHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)

    print(f"Surveillance du dossier : {path}")
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
