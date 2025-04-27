
import os
import time
from core.organizer import supprimer_doublons, classer_fichier_par_type, creer_dossier_si_absent, renommer_fichiers, classer_par_date
from logs.logger import logger

from core.history import afficher_historique, charger_historique, sauvegarder_historique, enregistrer_action

import argparse
from core.undo_redo import undo, redo


from PyQt6.QtWidgets import QApplication
from gui.main_window import FileManager  # Tu importes ta fenêtre principale
import sys
from core.starts import *
# Juste pour test ou accès rapide




    

# main.py


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileManager()
    window.show()
    sys.exit(app.exec())