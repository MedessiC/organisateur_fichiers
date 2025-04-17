<<<<<<< HEAD
# -*- coding: utf-8 -*-
# Interface graphique pour le gestionnaire de fichiers TITO
# Cette version est adaptée aux fonctionnalités d'organizer.py
# Elle permet d'organiser, renommer, et supprimer des fichiers
# Auteur : COOVI Meessi
# Date : 16/04/2025
# Version : 2.0

import sys
import os
from datetime import datetime
import shutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QTreeWidget, QTreeWidgetItem, QLabel, QLineEdit, 
                            QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, 
                            QFileDialog, QInputDialog, QMessageBox, QSplitter, QFrame,
                            QCheckBox, QProgressBar, QToolButton, QMenu, QSpinBox, 
                            QGroupBox, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QFont

# Importation des modules d'organisation
from organizer import (classer_fichier_par_type, classer_par_date, renommer_fichiers, 
                      supprimer_doublons, calculer_hash, generer_nouveau_nom)
from history import enregistrer_action, afficher_historique, nettoyer_historique
from watcher import demarrer_surveillance, FolderHandler
from logger import logger
import time

import os
import time
from PyQt6.QtCore import QThread, pyqtSignal

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
        from watcher import FolderHandler, Observer, logger  # Importez ici pour éviter les problèmes de dépendances cycliques potentiels

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
                            "Images": [".png", ".jpg", ".jpeg", ".gif", ".bmp"],
                            "Vidéos": [".mp4", ".mkv", ".avi", ".mov"],
                            "Documents": [".pdf", ".docx", ".txt", ".xlsx", ".pptx"],
                            "Audios": [".mp3", ".wav", ".aac"],
                            "Archives": [".zip", ".rar", ".7z"],
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

class FileManager(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialisation de la fenêtre principale
        self.setWindowTitle("TITO - Gestionnaire de fichiers intelligent")
        self.setWindowIcon(QIcon("icon.png"))  
        self.setStyleSheet("font-family: Arial; font-size: 12px;")
        self.setMinimumSize(1000, 650)

        # Couleur principale pour la barre supérieure 
        self.main_color = "MidnightBlue"
        self.accent_color = "#4169E1"  # Royal Blue - couleur complémentaire
        
        # Variables pour stocker le chemin courant et les fichiers sélectionnés
        self.current_directory = os.path.expanduser("~")
        self.selected_files = []
        
        # Initialisation du thread de surveillance
        self.watcher_thread = None
        self.is_watching = False
        self.watcher_settings = {
            'delay': 30,
            'auto_organize_by_type': True,
            'auto_remove_duplicates': False,
            'recursive': True
        }
        
        # Configuration de l'interface
        self.setup_ui()
        
        # Charger les fichiers initiaux
        self.directory_label.setText(f"Dossier: {self.current_directory}")
        self.load_files(self.current_directory)
        
    def load_files(self, directory=None):
        self.file_table.setRowCount(0)
        self.status_label.setText("Chargement des fichiers...")
        QApplication.processEvents()

        target_dir = directory or self.current_directory
        if not target_dir or not os.path.isdir(target_dir):
            return

        self.total_size_kb = 0
        self.total_files = 0

        self.loader = LoadFilesWorker(target_dir)
        self.loader.file_found.connect(self.add_file_to_table)
        self.loader.finished.connect(self.finish_loading_files)
        self.loader.error.connect(self.show_loading_error)
        self.loader.start()

    def populate_file_table(self, file_list):
        """Affiche les fichiers dans le tableau après chargement"""
        self.file_table.setRowCount(len(file_list))
        for row, (name, type_, size, date, hash_, _) in enumerate(file_list):
            self.file_table.setItem(row, 0, QTableWidgetItem(name))
            self.file_table.setItem(row, 1, QTableWidgetItem(type_))
            self.file_table.setItem(row, 2, QTableWidgetItem(size))
            self.file_table.setItem(row, 3, QTableWidgetItem(date))
            self.file_table.setItem(row, 4, QTableWidgetItem(hash_))

        total_files = len(file_list)
        total_size_kb = sum(item[5] for item in file_list)

        if total_size_kb < 1024:
            size_text = f"{total_size_kb:.2f} KB"
        else:
            total_size_mb = total_size_kb / 1024
            size_text = f"{total_size_mb:.2f} MB" if total_size_mb < 1024 else f"{total_size_mb / 1024:.2f} GB"

        self.status_label.setText(f"{total_files} éléments - {size_text}")
        
    def add_file_to_table(self, file_data):
        row = self.file_table.rowCount()
        self.file_table.insertRow(row)
        name, type_, size, date, hash_, size_kb = file_data
        self.file_table.setItem(row, 0, QTableWidgetItem(name))
        self.file_table.setItem(row, 1, QTableWidgetItem(type_))
        self.file_table.setItem(row, 2, QTableWidgetItem(size))
        self.file_table.setItem(row, 3, QTableWidgetItem(date))
        self.file_table.setItem(row, 4, QTableWidgetItem(hash_))

        self.total_size_kb += size_kb
        self.total_files += 1
        
    def finish_loading_files(self):
        if self.total_size_kb < 1024:
            size_text = f"{self.total_size_kb:.2f} KB"
        else:
            total_size_mb = self.total_size_kb / 1024
            size_text = f"{total_size_mb:.2f} MB" if total_size_mb < 1024 else f"{total_size_mb / 1024:.2f} GB"

        self.status_label.setText(f"{self.total_files} éléments - {size_text}")

    def show_loading_error(self, error_msg):
        """Affiche un message d'erreur si le chargement échoue"""
        self.status_label.setText("Erreur de chargement")
        QMessageBox.critical(self, "Erreur", f"Impossible de charger les fichiers :\n{error_msg}")

    def setup_ui(self):
        # Widget central
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Barre de titre
        title_bar = QWidget()
        title_bar.setStyleSheet(f"background-color: {self.main_color}; color: white;")
        title_bar.setFixedHeight(50)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(10, 5, 10, 5)
        
        # Logo et titre
        title_label = QLabel("TITO")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        title_bar_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel("Gestionnaire de fichiers intelligent")
        desc_label.setStyleSheet("font-size: 14px; font-style: italic;")
        title_bar_layout.addWidget(desc_label)
        
        # Ajout d'un espace extensible
        title_bar_layout.addStretch()
        
        # Boutons de la barre supérieure
        history_btn = QPushButton("Historique")
        history_btn.setStyleSheet("background-color: white; color: MidnightBlue; padding: 5px 10px; border-radius: 3px;")
        history_btn.clicked.connect(self.afficher_historique)
        title_bar_layout.addWidget(history_btn)
        
        settings_btn = QPushButton("Paramètres")
        settings_btn.setStyleSheet("background-color: white; color: MidnightBlue; padding: 5px 10px; border-radius: 3px;")
        settings_btn.clicked.connect(self.show_settings)
        title_bar_layout.addWidget(settings_btn)
        
        main_layout.addWidget(title_bar)
        
        # Corps principal avec un splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Zone de navigation à gauche
        navigation_widget = QWidget()
        navigation_widget.setMaximumWidth(250)
        navigation_widget.setStyleSheet("background-color: #f0f0f0;")
        nav_layout = QVBoxLayout(navigation_widget)
        nav_layout.setContentsMargins(5, 10, 5, 10)
        
        # Bouton de sélection de dossier
        self.select_button = QPushButton("📂 Choisir un dossier")
        self.select_button.setStyleSheet(f"background-color: {self.main_color}; color: white; padding: 8px 15px; border-radius: 4px;")
        self.select_button.clicked.connect(self.select_directory)
        nav_layout.addWidget(self.select_button)
        
        # Label du dossier actuel
        self.directory_label = QLabel("Dossier: Aucun dossier sélectionné")
        self.directory_label.setWordWrap(True)
        self.directory_label.setStyleSheet("padding: 5px; font-size: 11px;")
        nav_layout.addWidget(self.directory_label)
        
        # Séparateur
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        nav_layout.addWidget(separator)
        
        # Options d'organisation avec des cases à cocher
        organize_group = QWidget()
        organize_layout = QVBoxLayout(organize_group)
        organize_layout.setContentsMargins(0, 5, 0, 5)
        
        organize_title = QLabel("Options d'organisation")
        organize_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        organize_layout.addWidget(organize_title)
        
        # Cases à cocher pour les options d'organisation
        self.organize_by_type = QCheckBox("Organiser par type")
        self.organize_by_type.setChecked(True)
        organize_layout.addWidget(self.organize_by_type)
        
        self.organize_by_date = QCheckBox("Organiser par date")
        organize_layout.addWidget(self.organize_by_date)
        
        self.rename_files = QCheckBox("Renommer les fichiers")
        organize_layout.addWidget(self.rename_files)
        
        self.remove_duplicates = QCheckBox("Supprimer les doublons")
        organize_layout.addWidget(self.remove_duplicates)
        
        self.simulation_mode = QCheckBox("Mode simulation")
        self.simulation_mode.setToolTip("Montre les actions sans les exécuter")
        organize_layout.addWidget(self.simulation_mode)
        
        # Bouton d'organisation
        self.organize_btn = QPushButton("🔄 Organiser le dossier")
        self.organize_btn.setStyleSheet(f"background-color: {self.accent_color}; color: white; padding: 8px 15px; border-radius: 4px; margin-top: 10px;")
        self.organize_btn.clicked.connect(self.organize_files)
        organize_layout.addWidget(self.organize_btn)
        
        nav_layout.addWidget(organize_group)
        
        # Section de surveillance
        watch_group = QWidget()
        watch_layout = QVBoxLayout(watch_group)
        watch_layout.setContentsMargins(0, 5, 0, 5)
        
        watch_title = QLabel("Surveillance automatique")
        watch_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        watch_layout.addWidget(watch_title)
        
        # Bouton de démarrage/arrêt de surveillance
        self.watch_btn = QPushButton("👁️ Démarrer la surveillance")
        self.watch_btn.setStyleSheet(f"background-color: green; color: white; padding: 8px 15px; border-radius: 4px;")
        self.watch_btn.clicked.connect(self.toggle_watcher)
        watch_layout.addWidget(self.watch_btn)
        
        # Bouton de configuration de surveillance
        self.config_watch_btn = QPushButton("⚙️ Configurer la surveillance")
        self.config_watch_btn.clicked.connect(self.configure_watcher)
        watch_layout.addWidget(self.config_watch_btn)
        
        # Ajouter une petite étiquette d'état de surveillance
        self.watch_status_label = QLabel("État: Inactif")
        self.watch_status_label.setStyleSheet("font-style: italic; font-size: 11px;")
        watch_layout.addWidget(self.watch_status_label)
        
        nav_layout.addWidget(watch_group)
        
        # Dossiers rapides
        folders_label = QLabel("Dossiers rapides")
        folders_label.setStyleSheet("font-weight: bold; padding: 5px; font-size: 13px;")
        nav_layout.addWidget(folders_label)
        
        # Arborescence des dossiers
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setIndentation(15)
        self.folder_tree.setStyleSheet("QTreeWidget::item:hover {background-color: #e0e0e0;}")
        
        # Création des catégories principales
        images = self.create_tree_category("Images", ["JPG", "PNG", "GIF"])
        documents = self.create_tree_category("Documents", ["PDF", "DOCX", "TXT"])
        videos = self.create_tree_category("Vidéos", ["MP4", "AVI", "MKV"])
        musique = self.create_tree_category("Musique", ["MP3", "WAV", "FLAC"])
        archives = self.create_tree_category("Archives", ["ZIP", "RAR", "7Z"])
        
        self.folder_tree.itemClicked.connect(self.folder_clicked)
        nav_layout.addWidget(self.folder_tree)
        
        # Ajouter un espace extensible en bas
        nav_layout.addStretch()
        
        # Option de statistiques
        stats_btn = QPushButton("📊 Afficher les statistiques")
        stats_btn.setStyleSheet(f"background-color: {self.main_color}; color: white; padding: 8px 15px; border-radius: 4px;")
        stats_btn.clicked.connect(self.show_statistics)
        nav_layout.addWidget(stats_btn)
        
        # Ajout du widget de navigation au splitter
        splitter.addWidget(navigation_widget)
        
        # Zone principale à droite
        main_area = QWidget()
        main_area_layout = QVBoxLayout(main_area)
        main_area_layout.setContentsMargins(10, 10, 10, 10)
        
        # Barre de recherche et filtres
        search_filter_widget = QWidget()
        search_filter_layout = QHBoxLayout(search_filter_widget)
        search_filter_layout.setContentsMargins(0, 0, 0, 10)
        
        # Zone de recherche
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher des fichiers...")
        self.search_input.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 5px;")
        self.search_input.textChanged.connect(self.search_files)
        search_filter_layout.addWidget(self.search_input)
        
        # Filtres rapides
        filter_label = QLabel("Filtrer par:")
        search_filter_layout.addWidget(filter_label)
        
        # Filtre par type
        self.type_filter = QComboBox()
        self.type_filter.addItem("Tous")
        for type_name in ["Images", "Documents", "Vidéos", "Audios", "Archives", "Autres"]:
            self.type_filter.addItem(type_name)
        self.type_filter.currentTextChanged.connect(self.apply_filters)
        search_filter_layout.addWidget(self.type_filter)
        
        # Bouton de réinitialisation des filtres
        reset_btn = QPushButton("Réinitialiser")
        reset_btn.clicked.connect(self.reset_filters)
        search_filter_layout.addWidget(reset_btn)
        
        main_area_layout.addWidget(search_filter_widget)
        
        # Barre d'outils pour les actions sur les fichiers
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(0, 0, 0, 10)
        
        # Création des boutons d'action
        self.create_action_button(toolbar_layout, "Nouveau dossier", self.new_folder)
        self.create_action_button(toolbar_layout, "Ouvrir", self.open_file)
        self.create_action_button(toolbar_layout, "Renommer", self.rename_file)
        self.create_action_button(toolbar_layout, "Supprimer", self.delete_file)
        
        # Bouton d'outils supplémentaires avec menu déroulant
        more_btn = QToolButton()
        more_btn.setText("Plus d'options")
        more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        more_menu = QMenu(more_btn)
        more_menu.addAction("Compresser", self.compress_files)
        more_menu.addAction("Décompresser", self.decompress_file)
        more_menu.addAction("Analyser les doublons", self.analyze_duplicates)
        more_menu.addSeparator()
        more_menu.addAction("Convertir des fichiers", self.convert_files)
        
        more_btn.setMenu(more_menu)
        more_btn.setStyleSheet(f"background-color: {self.main_color}; color: white; padding: 8px 15px; border-radius: 4px;")
        toolbar_layout.addWidget(more_btn)
        
        # Ajouter un espace extensible
        toolbar_layout.addStretch()
        
        # Mode d'affichage
        view_label = QLabel("Affichage:")
        toolbar_layout.addWidget(view_label)
        
        view_combo = QComboBox()
        view_combo.addItems(["Détails", "Icônes", "Liste"])
        view_combo.setCurrentIndex(0)
        toolbar_layout.addWidget(view_combo)
        
        main_area_layout.addWidget(toolbar_widget)
        
        # Tableau des fichiers
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels(["Nom", "Type", "Taille", "Date de modification", "Hash"])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        self.file_table.setStyleSheet("QTableWidget {border: 1px solid #ddd; gridline-color: #f0f0f0;}")
        self.file_table.itemSelectionChanged.connect(self.update_selected_files)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.file_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self.show_context_menu)
        
        main_area_layout.addWidget(self.file_table)
        
        # Barre de progression (initialement cachée)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - Organisation en cours...")
        self.progress_bar.setVisible(False)
        main_area_layout.addWidget(self.progress_bar)
        
        # Barre de statut
        status_bar = QWidget()
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(0, 5, 0, 0)
        
        self.status_label = QLabel("0 éléments")
        status_layout.addWidget(self.status_label)
        
        # Ajouter un espace extensible
        status_layout.addStretch()
        
        # Information sur l'espace disque
        self.space_label = QLabel("Espace libre: calculing...")
        self.space_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_layout.addWidget(self.space_label)
        
        main_area_layout.addWidget(status_bar)
        
        # Ajout de la zone principale au splitter
        splitter.addWidget(main_area)
        
        # Configuration du splitter
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter)
        
        self.setCentralWidget(central_widget)
        
        # Mettre à jour l'information sur l'espace disque
        self.update_disk_space()
    
    def create_tree_category(self, name, subtypes=None):
        """Crée une catégorie dans l'arborescence avec des sous-types optionnels"""
        category = QTreeWidgetItem(self.folder_tree, [name])
        category.setIcon(0, QIcon.fromTheme("folder"))
        category.setData(0, Qt.ItemDataRole.UserRole, name.lower())
        
        # Ajouter les sous-types si fournis
        if subtypes:
            for subtype in subtypes:
                subitem = QTreeWidgetItem(category, [subtype])
                subitem.setIcon(0, QIcon.fromTheme("text-x-generic"))
                subitem.setData(0, Qt.ItemDataRole.UserRole, f"{name.lower()}_{subtype.lower()}")
        
        return category
    
    def create_action_button(self, layout, text, callback):
        """Crée un bouton d'action pour la barre d'outils"""
        button = QPushButton(text)
        button.setStyleSheet(f"background-color: {self.main_color}; color: white; padding: 8px 15px; border-radius: 4px;")
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button
    
    def select_directory(self):
        """Ouvre un dialogue pour sélectionner un dossier et charge les fichiers"""
        directory = QFileDialog.getExistingDirectory(self, "Choisir un dossier", self.current_directory)
        if directory:
            self.current_directory = directory
            self.directory_label.setText(f"Dossier: {directory}")
            self.load_files(directory)
            self.update_disk_space()
    
        def load_files(self, directory=None):
            """Charge les fichiers dans le tableau en utilisant un thread pour éviter les blocages"""
            self.file_table.setRowCount(0)
            self.status_label.setText("Chargement des fichiers...")
            QApplication.processEvents()

            target_dir = directory or self.current_directory

            if not target_dir or not os.path.isdir(target_dir):
                return

            self.loader = LoadFilesWorker(target_dir)
            self.loader.files_loaded.connect(self.populate_file_table)
            self.loader.error.connect(self.show_loading_error)
            self.loader.start()

    def toggle_watcher(self):
        """Démarre ou arrête la surveillance du dossier"""
        if self.is_watching:
            self.stop_watcher()
        else:
            self.demarrer_surveillance()
            self.is_watching = True
    
    def configure_watcher(self):
        """Ouvre la boîte de dialogue de configuration de la surveillance"""
        dialog = WatcherSettingsDialog(self)
        if dialog.exec():
            self.watcher_settings['delay'] = dialog.delay_spin.value()
            self.watcher_settings['auto_organize_by_type'] = dialog.auto_organize_by_type.isChecked()
            self.watcher_settings['auto_remove_duplicates'] = dialog.auto_remove_duplicates.isChecked()
            self.watcher_settings['recursive'] = dialog.recursive_watch.isChecked()
    def update_disk_space(self):
        """Met à jour les informations sur l'espace disque disponible"""
        try:
            if os.path.exists(self.current_directory):
                disk_info = shutil.disk_usage(self.current_directory)
                free_gb = disk_info.free / (1024**3)
                total_gb = disk_info.total / (1024**3)
                self.space_label.setText(f"Espace libre: {free_gb:.1f} GB / {total_gb:.1f} GB")
        except Exception:
            self.space_label.setText("Espace libre: inconnu")
    
    def folder_clicked(self, item, column):
        """Gère le clic sur un élément dans l'arborescence des dossiers"""
        # Récupérer les données associées à l'élément
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data:
            return
        
        # Filtrer selon le type sélectionné
        if "_" in item_data:  # Sous-type (comme "images_jpg")
            category, extension = item_data.split("_")
            self.search_input.setText(f".{extension}")
        else:  # Catégorie principale
            self.type_filter.setCurrentText(item_data.capitalize())
            self.search_input.setText("")
    
    def search_files(self):
        """Filtre les fichiers selon le texte de recherche"""
        search_text = self.search_input.text().lower()
        self.apply_filters()  # Réappliquer également les filtres
    
    def afficher_historique(self):
        """Affiche l'historique des actions."""
        history_file = os.path.join(self.current_directory, "history.txt")
        if os.path.exists(history_file):
            with open(history_file, "r") as file:
                history = file.read()
            QMessageBox.information(self, "Historique", history)
        else:
            QMessageBox.warning(self, "Historique", "Aucun historique trouvé.")

    def new_folder(self):
        """Crée un nouveau dossier dans le répertoire actuel."""
        folder_name, ok = QInputDialog.getText(self, "Nouveau dossier", "Nom du dossier :")
        if ok and folder_name:
            new_folder_path = os.path.join(self.current_directory, folder_name)
            try:
                if not os.path.exists(new_folder_path):
                    os.makedirs(new_folder_path)
                    QMessageBox.information(self, "Succès", f"Dossier '{folder_name}' créé avec succès.")
                else:
                    QMessageBox.warning(self, "Erreur", f"Le dossier '{folder_name}' existe déjà.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de créer le dossier : {str(e)}")
    
    
    def compress_files(self):
            """Compresse les fichiers sélectionnés dans un fichier ZIP."""
            if not self.selected_files:
                QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner au moins un fichier à compresser.")
                return
            
            zip_name, ok = QInputDialog.getText(self, "Compresser", "Nom du fichier ZIP :")
            if ok and zip_name:
                zip_path = os.path.join(self.current_directory, f"{zip_name}.zip")
                try:
                    with shutil.ZipFile(zip_path, 'w') as zipf:
                        for file in self.selected_files:
                            file_path = os.path.join(self.current_directory, file)
                            zipf.write(file_path, arcname=file)
                    QMessageBox.information(self, "Succès", f"Fichiers compressés dans '{zip_name}.zip'.")
                except Exception as e:
                    QMessageBox.critical(self, "Erreur", f"Erreur lors de la compression : {str(e)}")
    def decompress_file(self):
        """Décompresse un fichier ZIP sélectionné."""
        if not self.selected_files:
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner un fichier ZIP à décompresser.")
            return
        
        zip_file = self.selected_files[0]
        zip_path = os.path.join(self.current_directory, zip_file)
        
        if not zip_file.endswith(".zip"):
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner un fichier ZIP.")
            return
        
        try:
            with shutil.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(self.current_directory)
            QMessageBox.information(self, "Succès", f"Fichier '{zip_file}' décompressé avec succès.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la décompression : {str(e)}")
    
    def analyze_duplicates(self):
        """Analyse les fichiers sélectionnés pour détecter les doublons."""
        if not self.selected_files:
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner au moins un fichier à analyser.")
            return
        
        # Ici, vous pourriez appeler votre fonction existante pour l'analyse des doublons
        print(f"Analyser les doublons pour : {self.selected_files}")

    def convert_files(self):
        """Convertit les fichiers sélectionnés."""
        if not self.selected_files:
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner au moins un fichier à convertir.")
            return
        
        # Ici, vous pourriez appeler votre fonction existante pour la conversion de fichiers
        print(f"Convertir les fichiers : {self.selected_files}")
    def show_statistics(self):
        """Affiche les statistiques sur le dossier sélectionné."""
        if self.current_directory:
            num_files = len([f for f in os.listdir(self.current_directory) if os.path.isfile(os.path.join(self.current_directory, f))])
            num_folders = len([d for d in os.listdir(self.current_directory) if os.path.isdir(os.path.join(self.current_directory, d))])
            
            QMessageBox.information(self, "Statistiques", f"Fichiers : {num_files}\nDossiers : {num_folders}")
        else:
            QMessageBox.warning(self, "Statistiques", "Veuillez d'abord sélectionner un dossier.")
    def show_settings(self):
        """Affiche une boîte de dialogue pour les paramètres."""
        QMessageBox.information(self, "Paramètres", "Voici les paramètres de l'application.")
    def apply_filters(self):
        """Applique les filtres combinés (recherche et type)"""
        search_text = self.search_input.text().lower()
        type_filter = self.type_filter.currentText()
        
        for row in range(self.file_table.rowCount()):
            show_row = True
            file_name = self.file_table.item(row, 0).text().lower()
            file_type = self.file_table.item(row, 1).text()
            
            # Filtre par texte de recherche
            if search_text and search_text not in file_name:
                show_row = False
            
            # Filtre par type
            if type_filter != "Tous" and file_type != type_filter:
                show_row = False
            
            self.file_table.setRowHidden(row, not show_row)
    
    def reset_filters(self):
        """Réinitialise tous les filtres"""
        self.search_input.clear()
        self.type_filter.setCurrentText("Tous")
        # Afficher tous les fichiers
        for row in range(self.file_table.rowCount()):
            self.file_table.setRowHidden(row, False)
    
    def update_selected_files(self):
        """Met à jour la liste des fichiers sélectionnés"""
        self.selected_files = []
        selected_rows = set()
        
        for item in self.file_table.selectedItems():
            row = item.row()
            selected_rows.add(row)
        
        for row in selected_rows:
            file_name = self.file_table.item(row, 0).text()
            self.selected_files.append(file_name)
    
    def show_context_menu(self, position):
        """Affiche un menu contextuel pour les fichiers sélectionnés"""
        if not self.selected_files:
            return
        
        context_menu = QMenu(self)
        context_menu.addAction("Ouvrir", self.open_file)
        context_menu.addAction("Renommer", self.rename_file)
        context_menu.addSeparator()
        context_menu.addAction("Supprimer", self.delete_file)
        context_menu.addSeparator()
        
        # Sous-menu pour les options avancées
        advanced_menu = QMenu("Avancé", context_menu)
       # advanced_menu.addAction("Calculer le hash complet", self.calculate_full_hash)
        advanced_menu.addAction("Convertir", self.convert_files)
        context_menu.addMenu(advanced_menu)
        
        context_menu.exec(self.file_table.mapToGlobal(position))
    
    def update_selected_files(self):
        """Met à jour la liste des fichiers sélectionnés"""
        self.selected_files = []
        for item in self.file_table.selectedItems():
            if item.column() == 0:  # Colonne du nom de fichier
                self.selected_files.append(item.text())
    
    # Fonctions pour les boutons (à connecter avec vos implémentations existantes)
    def new_file(self):
        """Crée un nouveau fichier"""
        # Ici, vous pourriez appeler votre fonction existante
        print("Créer un nouveau fichier")
        
    def open_file(self):
        """Ouvre le(s) fichier(s) sélectionné(s)"""
        if not self.selected_files:
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner un fichier à ouvrir.")
            return
        
        # Ici, vous pourriez appeler votre fonction existante
        print(f"Ouvrir les fichiers: {self.selected_files}")
        
    def rename_file(self):
        """Renomme le fichier sélectionné"""
        if not self.selected_files or len(self.selected_files) > 1:
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner un seul fichier à renommer.")
            return
        
        # Ici, vous pourriez appeler votre fonction existante
        current_name = self.selected_files[0]
        new_name, ok = QInputDialog.getText(
            self, "Renommer le fichier", 
            "Nouveau nom:", 
            text=current_name
        )
        
        if ok and new_name:
            print(f"Renommer '{current_name}' en '{new_name}'")
            # Mettre à jour l'interface après le renommage
            selected_rows = self.file_table.selectedItems()
            if selected_rows and selected_rows[0].column() == 0:
                row = selected_rows[0].row()
                self.file_table.item(row, 0).setText(new_name)
        
    def delete_file(self):
        """Supprime le(s) fichier(s) sélectionné(s)"""
        if not self.selected_files:
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner un fichier à supprimer.")
            return
        
        reply = QMessageBox.question(
            self, "Confirmation de suppression", 
            f"Êtes-vous sûr de vouloir supprimer {len(self.selected_files)} fichier(s) ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Ici, vous pourriez appeler votre fonction existante
            print(f"Supprimer les fichiers: {self.selected_files}")
            
            # Supprimer de l'interface
            rows_to_remove = []
            for i in range(self.file_table.rowCount()):
                if self.file_table.item(i, 0).text() in self.selected_files:
                    rows_to_remove.append(i)
            
            # Supprimer en commençant par la fin pour éviter les décalages d'index
            for row in sorted(rows_to_remove, reverse=True):
                self.file_table.removeRow(row)
            
            # Mettre à jour le statut
            self.update_status()
        
    def organize_files(self):
        """Organise automatiquement les fichiers"""
        classer_fichier_par_type(self.current_directory)
        supprimer_doublons(self.current_directory)
        print("Organiser automatiquement les fichiers")
        QMessageBox.information(self, "Organisation automatique", 
                               "Les fichiers ont été organisés avec succès!")
        # Mettre à jour l'interface après l'organisation

# Point d'entrée de l'application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileManager()
    window.show()
=======
# -*- coding: utf-8 -*-
# Ce script crée une interface graphique pour un gestionnaire de fichiers.  
## Il permet de naviguer dans les fichiers, de les organiser, de les renommer et de les supprimer.
# Il utilise PyQt6 pour créer l'interface et gère les événements utilisateur.

# Auteur : COOVI Meessi
# Date : 07/04/2025
# Version : 1.0



import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QTreeWidget, QTreeWidgetItem, QLabel, QLineEdit, 
                            QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, 
                            QFileDialog, QInputDialog, QMessageBox, QSplitter, QFrame)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QColor
from organizer import supprimer_doublons, classer_fichier_par_type


# Classe principale de l'application
# Cette classe hérite de QMainWindow et gère l'interface utilisateur

class FileManager(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialisation de la fenêtre principale
        self.setWindowTitle("TITO-Organisateur de Fichiers")
        self.setWindowIcon(QIcon("icon.png"))  
        self.setStyleSheet("font-family: Arial; font-size: 12px;")
        self.setMinimumSize(900, 600)
        
        # Couleur principale pour la barre supérieure 
        self.main_color = "#4285F4"
        
        # Variables pour stocker le chemin courant et les fichiers sélectionnés
        self.current_path = os.path.expanduser("~")
        self.selected_files = []
        
        # Configuration de l'interface
        self.setup_ui()
        
        # Charger les fichiers initiaux
        self.load_files()
        
    def setup_ui(self):
        # Widget central
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Barre de titre
        title_bar = QWidget()
        title_bar.setStyleSheet(f"background-color: {self.main_color}; color: white;")
        title_bar_layout = QHBoxLayout(title_bar)
        title_label = QLabel("TITO-Organisateur de Fichiers")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_bar_layout.addWidget(title_label)
        
        # Boutons de contrôle (vert, jaune, rouge)
        control_layout = QHBoxLayout()

        title_bar_layout.addLayout(control_layout)
        main_layout.addWidget(title_bar)
        self.select_button = QPushButton("📂 Choisir un dossier")
        self.select_button.clicked.connect(self.select_directory)
        title_bar_layout.addWidget(self.select_button)
        self.directory_label = QLabel("Aucun dossier sélectionné")
        title_bar_layout.addWidget(self.directory_label)

        
        # Corps principal
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        
        # Zone de navigation à gauche
        navigation_widget = QWidget()
        navigation_widget.setMaximumWidth(220)
        navigation_widget.setStyleSheet("background-color: #f0f0f0;")
        nav_layout = QVBoxLayout(navigation_widget)
        
        # Label Dossiers
        folders_label = QLabel("Dossiers")
        folders_label.setStyleSheet("font-weight: bold; padding: 5px;")
        nav_layout.addWidget(folders_label)
        
        # Arborescence des dossiers
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setIndentation(15)
        
        # Créer les catégories principales
        documents = QTreeWidgetItem(self.folder_tree, ["Documents"])
        documents.setIcon(0, QIcon.fromTheme("folder"))
        documents.setData(0, Qt.ItemDataRole.UserRole, "collapsed")
        
        # Sous-dossiers pour Documents
        rapports = QTreeWidgetItem(documents, ["Rapports"])
        rapports.setIcon(0, QIcon.fromTheme("folder"))
        factures = QTreeWidgetItem(documents, ["Factures"])
        factures.setIcon(0, QIcon.fromTheme("folder"))
        
        # Autres catégories
        images = QTreeWidgetItem(self.folder_tree, ["Images"])
        images.setIcon(0, QIcon.fromTheme("folder"))
        images.setData(0, Qt.ItemDataRole.UserRole, "collapsed")
        
        videos = QTreeWidgetItem(self.folder_tree, ["Vidéos"])
        videos.setIcon(0, QIcon.fromTheme("folder"))
        videos.setData(0, Qt.ItemDataRole.UserRole, "collapsed")
        
        musique = QTreeWidgetItem(self.folder_tree, ["Musique"])
        musique.setIcon(0, QIcon.fromTheme("folder"))
        musique.setData(0, Qt.ItemDataRole.UserRole, "collapsed")
        
        # Ajouter des icônes de flèche pour les éléments qui peuvent être développés
        for item in [documents, images, videos, musique]:
            # Flèche pour indiquer qu'on peut développer/réduire
            icon = "▶" if item.data(0, Qt.ItemDataRole.UserRole) == "collapsed" else "▼"
            item.setText(0, f" {icon} {item.text(0)}")
        
        self.folder_tree.itemClicked.connect(self.folder_clicked)
        nav_layout.addWidget(self.folder_tree)
        
        # Zone principale à droite
        main_area = QWidget()
        main_area_layout = QVBoxLayout(main_area)
        main_area_layout.setContentsMargins(0, 0, 0, 0)
        
        # Barre de boutons
        button_bar = QWidget()
        button_bar.setStyleSheet("background-color: #f8f8f8;")
        button_layout = QHBoxLayout(button_bar)
        
        # Création des boutons
        self.btn_new = QPushButton("Nouveau")
        self.btn_open = QPushButton("Ouvrir")
        self.btn_rename = QPushButton("Renommer")
        self.btn_delete = QPushButton("Supprimer")
        self.btn_organize = QPushButton("Organiser automatiquement")
        
        # Style et connexion des boutons
        for btn in [self.btn_new, self.btn_open, self.btn_rename, self.btn_delete, self.btn_organize]:
            btn.setStyleSheet(f"background-color: {self.main_color}; color: white; padding: 8px 15px;")
            btn.setFixedHeight(30)
            btn.setIconSize(QSize(16, 16))
            button_layout.addWidget(btn)
        
        # Connexion des boutons aux fonctions
        self.btn_new.clicked.connect(self.new_file)
        self.btn_open.clicked.connect(self.open_file)
        self.btn_rename.clicked.connect(self.rename_file)
        self.btn_delete.clicked.connect(self.delete_file)
        self.btn_organize.clicked.connect(self.organize_files)
        
        main_area_layout.addWidget(button_bar)
        
        # Zone de recherche
        search_bar = QWidget()
        search_layout = QHBoxLayout(search_bar)
        search_layout.setContentsMargins(10, 10, 10, 10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher des fichiers...")
        self.search_input.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 5px;")
        self.search_input.textChanged.connect(self.search_files)
        search_layout.addWidget(self.search_input)
        
        main_area_layout.addWidget(search_bar)
        
        # Tableau des fichiers
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["Nom", "Type", "Taille", "Date de modification"])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.file_table.itemSelectionChanged.connect(self.update_selected_files)
        
        main_area_layout.addWidget(self.file_table)
        
        # Zone d'aperçu et de filtres
        preview_filter_layout = QHBoxLayout()
        
        # Zone d'aperçu
        preview_area = QWidget()
        preview_area.setMinimumWidth(200)
        preview_layout = QVBoxLayout(preview_area)
        
        preview_label = QLabel("Aperçu")
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(preview_label)
        
        preview_content = QLabel()
        preview_content.setStyleSheet("background-color: #f8f8f8; border: 1px solid #ddd;")
        preview_content.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_content.setMinimumHeight(100)
        preview_layout.addWidget(preview_content)
        
        # Zone de filtres
        filter_area = QWidget()
        filter_layout = QVBoxLayout(filter_area)
        
        filter_label = QLabel("Filtres")
        filter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        filter_layout.addWidget(filter_label)
        
        # Filtre par type
        type_layout = QHBoxLayout()
        type_label = QLabel("Type:")
        self.type_filter = QComboBox()
        self.type_filter.addItems(["Tous", "PDF", "PPTX", "JPG", "DOCX"])
        self.type_filter.currentTextChanged.connect(self.apply_filters)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_filter)
        filter_layout.addLayout(type_layout)
        
        # Filtre par taille
        size_layout = QHBoxLayout()
        size_label = QLabel("Taille:")
        self.size_filter = QComboBox()
        self.size_filter.addItems(["Tous", "<1 MB", "1-5 MB", ">5 MB"])
        self.size_filter.currentTextChanged.connect(self.apply_filters)
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_filter)
        filter_layout.addLayout(size_layout)
        
        # Filtre par date
        date_layout = QHBoxLayout()
        date_label = QLabel("Date:")
        self.date_filter = QComboBox()
        self.date_filter.addItems(["Tous", "Aujourd'hui", "Cette semaine", "Ce mois"])
        self.date_filter.currentTextChanged.connect(self.apply_filters)
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_filter)
        filter_layout.addLayout(date_layout)
        
        preview_filter_layout.addWidget(preview_area)
        preview_filter_layout.addWidget(filter_area)
        main_area_layout.addLayout(preview_filter_layout)
        
        # Barre de statut
        status_bar = QWidget()
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_label = QLabel("5 éléments - 13.2 MB")
        status_layout.addWidget(self.status_label)
        
        self.space_label = QLabel("Espace libre: 234.5 GB")
        self.space_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_layout.addWidget(self.space_label)
        
        main_area_layout.addWidget(status_bar)
        
        # Organisation du layout
        body_layout.addWidget(navigation_widget)
        body_layout.addWidget(main_area)
        
        main_layout.addWidget(body_widget)
        
        self.setCentralWidget(central_widget)
    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Choisir un dossier")
        if directory:
            self.current_directory = directory
            self.directory_label.setText(f"Dossier sélectionné : {directory}")
            self.load_files(directory)  # Pour afficher les fichiers dès qu’un dossier est choisi
 
    def load_files(self, directory=None):
        """Charge les fichiers dans le tableau à partir du répertoire spécifié ou utilise des fichiers d'exemple"""
        self.file_table.setRowCount(0)  # Vider le tableau
        
        if directory and os.path.isdir(directory):
            # Charger les fichiers du répertoire spécifié
            for file_name in os.listdir(directory):
                file_path = os.path.join(directory, file_name)
                if os.path.isfile(file_path):
                    file_info = os.stat(file_path)
                    row_position = self.file_table.rowCount()
                    self.file_table.insertRow(row_position)
                    
                    self.file_table.setItem(row_position, 0, QTableWidgetItem(file_name))
                    self.file_table.setItem(row_position, 1, QTableWidgetItem(file_name.split('.')[-1].upper()))
                    self.file_table.setItem(row_position, 2, QTableWidgetItem(f"{file_info.st_size / (1024 * 1024):.2f} MB"))
                    self.file_table.setItem(row_position, 3, QTableWidgetItem(datetime.fromtimestamp(file_info.st_mtime).strftime("%d/%m/%Y %H:%M")))
            name_item = QTableWidgetItem(file["name"])
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.file_table.setItem(row_position, 0, name_item)
            # Fichiers d'exemple comme dans l'image
            size_item = QTableWidgetItem(file["size"])
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.file_table.setItem(row_position, 2, size_item)
            
            example_files = [
                {"name": "rapport_financier.pdf", "type": "PDF", "size": "1.2 MB", "date": "01/04/2025"},
                {"name": "presentation_projet.pptx", "type": "PPTX", "size": "5.7 MB", "date": "03/04/2025"},
                {"name": "photo_vacances.jpg", "type": "JPG", "size": "3.4 MB", "date": "02/04/2025"},
                {"name": "facture_electricite.pdf", "type": "PDF", "size": "0.8 MB", "date": "05/04/2025"},
                {"name": "document_texte.docx", "type": "DOCX", "size": "2.1 MB", "date": "04/04/2025 11:05"}
            ]
            
            for file in example_files:
                row_position = self.file_table.rowCount()
                self.file_table.insertRow(row_position)
                
                self.file_table.setItem(row_position, 0, QTableWidgetItem(file["name"]))
                self.file_table.setItem(row_position, 1, QTableWidgetItem(file["type"]))
                self.file_table.setItem(row_position, 2, QTableWidgetItem(file["size"]))
                self.file_table.setItem(row_position, 3, QTableWidgetItem(file["date"]))
        
        # Mettre à jour le statut
        self.update_status()
        
    def update_status(self):
        """Met à jour les informations de statut"""
        total_size = 0
        for i in range(self.file_table.rowCount()):
            size_text = self.file_table.item(i, 2).text()
            size_value = float(size_text.split()[0])
            total_size += size_value
        
        self.status_label.setText(f"{self.file_table.rowCount()} éléments - {total_size:.1f} MB")
    
    def folder_clicked(self, item, column):
        """Gère le clic sur un dossier dans l'arborescence"""
        # Changer l'état (développé/réduit) et mettre à jour l'icône
        if item.data(0, Qt.ItemDataRole.UserRole) == "collapsed":
            item.setData(0, Qt.ItemDataRole.UserRole, "expanded")
            item.setText(0, item.text(0).replace("▶", "▼"))
        else:
            item.setData(0, Qt.ItemDataRole.UserRole, "collapsed")
            item.setText(0, item.text(0).replace("▼", "▶"))
        
        # Charger les fichiers appropriés selon le dossier sélectionné
        folder_name = item.text(0).strip().replace("▶", "").replace("▼", "").strip()
        
        # Filtrer les fichiers selon le dossier sélectionné
        if folder_name == "Rapports":
            self.search_input.setText("rapport")
        elif folder_name == "Factures":
            self.search_input.setText("facture")
        elif folder_name == "Images":
            self.search_input.setText(".jpg")
        elif folder_name == "Vidéos":
            self.search_input.setText(".mp4")
        elif folder_name == "Musique":
            self.search_input.setText(".mp3")
        else:
            self.search_input.setText("")
            self.load_files()
    
    def search_files(self):
        """Filtre les fichiers selon le texte de recherche"""
        search_text = self.search_input.text().lower()
        
        for row in range(self.file_table.rowCount()):
            file_name = self.file_table.item(row, 0).text().lower()
            
            if search_text in file_name:
                self.file_table.setRowHidden(row, False)
            else:
                self.file_table.setRowHidden(row, True)
    
    def apply_filters(self):
        """Applique les filtres sélectionnés aux fichiers"""
        type_filter = self.type_filter.currentText()
        size_filter = self.size_filter.currentText()
        date_filter = self.date_filter.currentText()
        
        for row in range(self.file_table.rowCount()):
            show_row = True
            
            # Filtre par type
            if type_filter != "Tous":
                file_type = self.file_table.item(row, 1).text()
                if file_type != type_filter:
                    show_row = False
            
            # Filtre par taille
            if size_filter != "Tous" and show_row:
                size_text = self.file_table.item(row, 2).text()
                size_value = float(size_text.split()[0])
                
                if size_filter == "<1 MB" and size_value >= 1.0:
                    show_row = False
                elif size_filter == "1-5 MB" and (size_value < 1.0 or size_value > 5.0):
                    show_row = False
                elif size_filter == ">5 MB" and size_value <= 5.0:
                    show_row = False
            
            # Filtre par date (simplifié pour la démonstration)
            if date_filter != "Tous" and show_row:
                date_text = self.file_table.item(row, 3).text()
                # Implémentation simplifiée, à adapter selon vos besoins
                if date_filter == "Aujourd'hui" and "04/04/2025" not in date_text:
                    show_row = False
                # Autres filtres de date à implémenter selon les besoins
            
            self.file_table.setRowHidden(row, not show_row)
    
    def update_selected_files(self):
        """Met à jour la liste des fichiers sélectionnés"""
        self.selected_files = []
        for item in self.file_table.selectedItems():
            if item.column() == 0:  # Colonne du nom de fichier
                self.selected_files.append(item.text())
    
    # Fonctions pour les boutons (à connecter avec vos implémentations existantes)
    def new_file(self):
        """Crée un nouveau fichier"""
        # Ici, vous pourriez appeler votre fonction existante
        print("Créer un nouveau fichier")
        
    def open_file(self):
        """Ouvre le(s) fichier(s) sélectionné(s)"""
        if not self.selected_files:
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner un fichier à ouvrir.")
            return
        
        # Ici, vous pourriez appeler votre fonction existante
        print(f"Ouvrir les fichiers: {self.selected_files}")
        
    def rename_file(self):
        """Renomme le fichier sélectionné"""
        if not self.selected_files or len(self.selected_files) > 1:
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner un seul fichier à renommer.")
            return
        
        # Ici, vous pourriez appeler votre fonction existante
        current_name = self.selected_files[0]
        new_name, ok = QInputDialog.getText(
            self, "Renommer le fichier", 
            "Nouveau nom:", 
            text=current_name
        )
        
        if ok and new_name:
            print(f"Renommer '{current_name}' en '{new_name}'")
            # Mettre à jour l'interface après le renommage
            selected_rows = self.file_table.selectedItems()
            if selected_rows and selected_rows[0].column() == 0:
                row = selected_rows[0].row()
                self.file_table.item(row, 0).setText(new_name)
        
    def delete_file(self):
        """Supprime le(s) fichier(s) sélectionné(s)"""
        if not self.selected_files:
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner un fichier à supprimer.")
            return
        
        reply = QMessageBox.question(
            self, "Confirmation de suppression", 
            f"Êtes-vous sûr de vouloir supprimer {len(self.selected_files)} fichier(s) ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Ici, vous pourriez appeler votre fonction existante
            print(f"Supprimer les fichiers: {self.selected_files}")
            
            # Supprimer de l'interface
            rows_to_remove = []
            for i in range(self.file_table.rowCount()):
                if self.file_table.item(i, 0).text() in self.selected_files:
                    rows_to_remove.append(i)
            
            # Supprimer en commençant par la fin pour éviter les décalages d'index
            for row in sorted(rows_to_remove, reverse=True):
                self.file_table.removeRow(row)
            
            # Mettre à jour le statut
            self.update_status()
        
    def organize_files(self):
        """Organise automatiquement les fichiers"""
        # Ici, vous pourriez appeler votre fonction existante
        print("Organiser automatiquement les fichiers")
        QMessageBox.information(self, "Organisation automatique", 
                               "Les fichiers ont été organisés avec succès!")

# Point d'entrée de l'application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileManager()
    window.show()
>>>>>>> 4e8c32b7fd5a1ee9dd936ea8042cb3b1962af7cc
    sys.exit(app.exec())