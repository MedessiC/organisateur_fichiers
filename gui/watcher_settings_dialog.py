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



class WatcherSettingsDialog(QDialog):
    """Dialogue de configuration de la surveillance des dossiers."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration de la surveillance")
        self.setMinimumWidth(400)
        
        # Mise en page principale
        layout = QVBoxLayout(self)
        
        # Groupe d'options de surveillance
        group_box = QGroupBox("Options de surveillance")
        group_layout = QVBoxLayout(group_box)
        
        # Option de délai entre les organisations automatiques
        delay_layout = QHBoxLayout()
        delay_label = QLabel("Délai entre les organisations (secondes):")
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(10, 3600)
        self.delay_spin.setValue(30)
        self.delay_spin.setSingleStep(10)
        delay_layout.addWidget(delay_label)
        delay_layout.addWidget(self.delay_spin)
        group_layout.addLayout(delay_layout)
        
        # Options d'organisation automatique
        self.auto_organize_by_type = QCheckBox("Organiser par type automatiquement")
        self.auto_organize_by_type.setChecked(True)
        group_layout.addWidget(self.auto_organize_by_type)
        
        self.auto_remove_duplicates = QCheckBox("Supprimer les doublons automatiquement")
        self.auto_remove_duplicates.setChecked(False)
        group_layout.addWidget(self.auto_remove_duplicates)
        
        # Option pour la récursivité
        self.recursive_watch = QCheckBox("Surveiller les sous-dossiers")
        self.recursive_watch.setChecked(True)
        group_layout.addWidget(self.recursive_watch)
        
        layout.addWidget(group_box)
        
        # Boutons de dialogue
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
