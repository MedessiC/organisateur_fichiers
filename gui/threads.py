import sys
import os
from datetime import datetime
import shutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QTreeWidget, QTreeWidgetItem, QLabel, QLineEdit, 
                            QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, 
                            QFileDialog, QInputDialog, QMessageBox, QSplitter, QFrame,
                            QCheckBox, QProgressBar, QToolButton, QMenu, QSpinBox, 
                            QGroupBox, QDialog, QDialogButtonBox, QDateEdit, QTextEdit, QFormLayout)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QDate
import csv
from PyQt6.QtGui import QIcon, QColor, QFont

# Importation des modules d'organisation
from core.organizer import (classer_fichier_par_type, classer_par_date, renommer_fichiers, 
                      supprimer_doublons, calculer_hash, generer_nouveau_nom)
from core.history import enregistrer_action, afficher_historique, nettoyer_historique
from core.watcher import demarrer_surveillance, FolderHandler
from logs.logger import logger
import time

import os
import time
from PyQt6.QtCore import QThread, pyqtSignal
import json


class WatcherThread(QThread):
    """Thread pour la surveillance des dossiers"""
    status_update = pyqtSignal(str)
    file_changed = pyqtSignal(str)

    def __init__(self, directory, delay=30):
        super().__init__()
        self.directory = directory
        self.running = True
        self.delay = delay  # Délai en secondes (peut ne pas être directement utilisé ici)
        self.observer = None
        self.event_handler = None

    def run(self):
        from core.watcher import FolderHandler, Observer, logger  # Importez ici pour éviter les problèmes de dépendances cycliques potentiels

        if not os.path.exists(self.directory):
            self.status_update.emit(f"❌ Le dossier {self.directory} n'existe pas.")
            return

        self.event_handler = FolderHandler(self.directory, self.delay) # Utilisez le délai du WatcherThread
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.directory, recursive=False)

        self.status_update.emit(f"👁️ Surveillance activée sur le dossier: {self.directory}")
        self.observer.start()

        try:
            while self.running:
                time.sleep(1)
        except Exception as e:
            logger.error(f"Erreur dans le thread de surveillance: {e}")
            self.status_update.emit(f"⚠️ Erreur de surveillance: {str(e)}")
        finally:
            if self.observer and self.observer.is_alive():
                self.observer.stop()
                self.observer.join()
                self.status_update.emit("🛑 Surveillance arrêtée.")

    def stop(self):
        self.running = False
        self.wait()
class LoadFilesWorker(QThread):
    file_found = pyqtSignal(tuple)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, directory):
        super().__init__()
        self.directory = directory

    def run(self):
        try:
            for file_name in os.listdir(self.directory):
                file_path = os.path.join(self.directory, file_name)
                if os.path.isfile(file_path):
                    try:
                        file_info = os.stat(file_path)
                       # file_hash = calculer_hash(file_path)[:8] if file_path else "N/A"
                        file_hash = "..."  # Valeur par défaut ou vide

                        _, extension = os.path.splitext(file_name)
                        extension = extension.lower()

                        file_type = "Autres"
                        for type_name, extensions in {
                            "Documents": [".pdf", ".doc", ".docx", ".txt", ".odt"],
                            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
                            "Vidéos": [".mp4", ".avi", ".mov", ".mkv"],
                            "Musique": [".mp3", ".wav", ".aac", ".flac"],
                            "Archives": [".zip", ".rar", ".tar", ".gz", ".7z"],
                            "Exécutables": [".exe", ".msi", ".bat", ".sh", ".apk"],
                            "Feuilles de calcul": [".xls", ".xlsx", ".csv", ".ods"],
                            "Présentations": [".ppt", ".pptx", ".odp"],
                            "Code": [".py", ".java", ".c", ".cpp", ".js", ".html", ".css"],
                        }.items():
                            if extension in extensions:
                                file_type = type_name
                                break

                        size_kb = file_info.st_size / 1024
                        if size_kb < 1024:
                            size_str = f"{size_kb:.2f} KB"
                        else:
                            size_mb = size_kb / 1024
                            size_str = f"{size_mb:.2f} MB" if size_mb < 1024 else f"{size_mb / 1024:.2f} GB"

                        mod_date = datetime.fromtimestamp(file_info.st_mtime).strftime("%d/%m/%Y %H:%M")

                        self.file_found.emit((file_name, file_type, size_str, mod_date, file_hash, size_kb))
                    except Exception as e:
                        print(f"Erreur pour {file_name}: {e}")
            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))

class OrganizeWorker(QThread):
    """Classe pour exécuter les opérations d'organisation en arrière-plan."""
    finished = pyqtSignal(str, int)
    progress = pyqtSignal(int)
    
    def __init__(self, dossier, operations, mode_simulation=False, limite=None):
        super().__init__()
        self.dossier = dossier
        self.operations = operations
        self.mode_simulation = mode_simulation
        self.limite = limite
        
    def run(self):
        resultats = []
        fichiers_traites = 0
        
        for operation, active in self.operations.items():
            if not active:
                continue
                
            if operation == "type":
                nombre = classer_fichier_par_type(self.dossier, self.mode_simulation, self.limite)
                resultats.append(f"{nombre} fichiers classés par type")
                fichiers_traites += nombre
                self.progress.emit(25)
                
            elif operation == "date":
                nombre = classer_par_date(self.dossier, self.mode_simulation, self.limite)
                resultats.append(f"{nombre} fichiers classés par date")
                fichiers_traites += nombre
                self.progress.emit(50)
                
            elif operation == "rename":
                nombre = renommer_fichiers(self.dossier, self.mode_simulation, self.limite)
                resultats.append(f"{nombre} fichiers renommés")
                fichiers_traites += nombre
                self.progress.emit(75)
                
            elif operation == "duplicates":
                nombre = supprimer_doublons(self.dossier, self.mode_simulation, self.limite)
                resultats.append(f"{nombre} doublons supprimés")
                fichiers_traites += nombre
                self.progress.emit(100)
        
        message = "\n".join(resultats)
        self.finished.emit(message, fichiers_traites)

