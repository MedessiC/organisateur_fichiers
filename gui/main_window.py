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
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QDate, QTimer, QUrl
import csv
from PyQt6.QtGui import QIcon, QColor, QFont, QDesktopServices

# Importation des modules d'organisation
from core.organizer import (classer_fichier_par_type, classer_par_date, renommer_fichiers, 
                      supprimer_doublons, calculer_hash, generer_nouveau_nom)
from core.history import enregistrer_action, afficher_historique, nettoyer_historique
from core.watcher import demarrer_surveillance, FolderHandler
from logs.logger import logger
import time
from .threads import LoadFilesWorker, WatcherThread
from .watcher_settings_dialog import WatcherSettingsDialog
import os
import time
from PyQt6.QtCore import QThread, pyqtSignal
import json





class FileManager(QMainWindow):
    def __init__(self):
        super().__init__()
        # Initialisation de la fenêtre principale
        self.setWindowTitle("TITO - Gestionnaire de fichiers intelligent")
        self.setWindowIcon(QIcon("icon.png"))  
        self.setMinimumSize(1000, 650)

        # Palette de couleurs moderne
        self.primary_color = "#2c3e50"      # Bleu foncé
        self.secondary_color = "#3498db"     # Bleu clair
        self.accent_color = "#e74c3c"        # Rouge/Orange pour les actions importantes
        self.light_bg = "#ecf0f1"            # Fond clair
        self.dark_text = "#2c3e50"           # Texte foncé
        self.light_text = "#ffffff"          # Texte clair
        self.hover_color = "#34495e"         # Couleur au survol
        self.border_radius = "6px"           # Rayon des bords arrondi
        
        # Configuration des polices
        font_family = "Segoe UI, Roboto, 'Helvetica Neue', Arial, sans-serif"
        self.setStyleSheet(f"font-family: {font_family}; font-size: 12px;")
        
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
        
        # Barre de titre avec style moderne
        title_bar = QWidget()
        title_bar.setStyleSheet(f"""
            background-color: {self.primary_color};
            color: {self.light_text};
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        """)
        title_bar.setFixedHeight(60)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(15, 5, 15, 5)
        
        # Logo et titre avec style moderne
        title_container = QWidget()
        title_container_layout = QVBoxLayout(title_container)
        title_container_layout.setContentsMargins(0, 0, 0, 0)
        title_container_layout.setSpacing(2)
        
        title_label = QLabel("TITO")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; letter-spacing: 1px;")
        title_container_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel("Gestionnaire de fichiers intelligent")
        desc_label.setStyleSheet("font-size: 13px; font-weight: 300; opacity: 0.8;")
        title_container_layout.addWidget(desc_label)
        
        title_bar_layout.addWidget(title_container)
        
        # Ajout d'un espace extensible
        title_bar_layout.addStretch()
        
        # Boutons de la barre supérieure avec style moderne
        button_style = f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.15);
                color: {self.light_text};
                padding: 8px 15px;
                border-radius: {self.border_radius};
                border: none;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.25);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """
        
        history_btn = QPushButton("Historique")
        history_btn.setStyleSheet(button_style)
        history_btn.setIcon(QIcon.fromTheme("history"))
        history_btn.clicked.connect(self.afficher_historique)
        title_bar_layout.addWidget(history_btn)
        
        settings_btn = QPushButton("Paramètres")
        settings_btn.setStyleSheet(button_style)
        settings_btn.setIcon(QIcon.fromTheme("settings"))
        settings_btn.clicked.connect(self.show_settings)
        title_bar_layout.addWidget(settings_btn)
        
        main_layout.addWidget(title_bar)
        
        # Corps principal avec un splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Zone de navigation à gauche avec style moderne
        navigation_widget = QWidget()
        navigation_widget.setMaximumWidth(280)
        navigation_widget.setStyleSheet(f"""
            background-color: {self.light_bg};
            border-right: 1px solid #dadce0;
        """)
        nav_layout = QVBoxLayout(navigation_widget)
        nav_layout.setContentsMargins(12, 15, 12, 15)
        nav_layout.setSpacing(10)
        
        # Bouton de sélection de dossier moderne
        self.select_button = QPushButton("📂  Choisir un dossier")
        self.select_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.secondary_color};
                color: {self.light_text};
                padding: 10px 15px;
                border-radius: {self.border_radius};
                font-weight: 500;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #2980b9;
            }}
            QPushButton:pressed {{
                background-color: #1f6aa5;
            }}
        """)
        self.select_button.clicked.connect(self.select_directory)
        nav_layout.addWidget(self.select_button)
        
        # Label du dossier actuel avec style moderne
        self.directory_label = QLabel("Dossier: Aucun dossier sélectionné")
        self.directory_label.setWordWrap(True)
        self.directory_label.setStyleSheet(f"""
            padding: 8px 10px;
            font-size: 11px;
            color: {self.dark_text};
            background-color: rgba(0, 0, 0, 0.03);
            border-radius: {self.border_radius};
        """)
        nav_layout.addWidget(self.directory_label)
        
        # Séparateur élégant
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: #dadce0; max-height: 1px;")
        nav_layout.addWidget(separator)
        
        # Options d'organisation avec des cases à cocher modernes
        organize_group = QGroupBox("Options d'organisation")
        organize_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: 600;
                font-size: 13px;
                padding-top: 15px;
                border: 1px solid #dadce0;
                border-radius: {self.border_radius};
                margin-top: 5px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 5px;
            }}
        """)
        organize_layout = QVBoxLayout(organize_group)
        organize_layout.setContentsMargins(15, 15, 15, 15)
        organize_layout.setSpacing(8)
        
        # Style moderne pour les checkboxes
        checkbox_style = f"""
            QCheckBox {{
                spacing: 8px;
                color: {self.dark_text};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 1px solid #b8b8b8;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.secondary_color};
                border: 1px solid {self.secondary_color};
                image: url(check.png);
            }}
            QCheckBox::indicator:unchecked:hover {{
                border: 1px solid {self.secondary_color};
            }}
        """
        
        # Cases à cocher pour les options d'organisation
        self.organize_by_type = QCheckBox("Organiser par type")
        self.organize_by_type.setToolTip("Classer les fichiers par type (images, vidéos, etc.)")
        self.organize_by_type.setChecked(True)
        self.organize_by_type.setStyleSheet(checkbox_style)
        organize_layout.addWidget(self.organize_by_type)
        
        self.organize_by_date = QCheckBox("Organiser par date")
        self.organize_by_date.setToolTip("Classer les fichiers par date de création ou de modification")
        self.organize_by_date.setStyleSheet(checkbox_style)
        organize_layout.addWidget(self.organize_by_date)
        
        self.rename_files = QCheckBox("Renommer les fichiers")
        self.rename_files.setToolTip("Renommer les fichiers selon un format cohérent")
        self.rename_files.setStyleSheet(checkbox_style)
        organize_layout.addWidget(self.rename_files)
        
        self.remove_duplicates = QCheckBox("Supprimer les doublons")
        self.remove_duplicates.setToolTip("Supprimer les fichiers en double")
        self.remove_duplicates.setStyleSheet(checkbox_style)
        organize_layout.addWidget(self.remove_duplicates)
        
        self.simulation_mode = QCheckBox("Mode simulation")
        self.simulation_mode.setToolTip("Montre les actions sans les exécuter")
        self.simulation_mode.setStyleSheet(checkbox_style)
        organize_layout.addWidget(self.simulation_mode)
        
        # Bouton d'organisation moderne
        self.organize_btn = QPushButton("🔄  Organiser le dossier")
        self.organize_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.accent_color};
                color: {self.light_text};
                padding: 10px 15px;
                border-radius: {self.border_radius};
                font-weight: 500;
                border: none;
                margin-top: 8px;
            }}
            QPushButton:hover {{
                background-color: #c0392b;
            }}
            QPushButton:pressed {{
                background-color: #a93226;
            }}
        """)
        self.organize_btn.setToolTip("Organiser les fichiers selon les options sélectionnées")
        self.organize_btn.clicked.connect(self.organize_files)
        organize_layout.addWidget(self.organize_btn)
        
        nav_layout.addWidget(organize_group)
        
        # Section de surveillance élégante
        watch_group = QGroupBox("Surveillance automatique")
        watch_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: 600;
                font-size: 13px;
                padding-top: 15px;
                border: 1px solid #dadce0;
                border-radius: {self.border_radius};
                margin-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 5px;
            }}
        """)
        watch_layout = QVBoxLayout(watch_group)
        watch_layout.setContentsMargins(15, 15, 15, 15)
        watch_layout.setSpacing(8)
        
        # Bouton de démarrage/arrêt de surveillance moderne
        self.watch_btn = QPushButton("👁️  Surveiller le dossier")
        self.watch_btn.setToolTip("Démarrer/Arrêter la surveillance du dossier")
        self.watch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #27ae60;
                color: {self.light_text};
                padding: 10px 15px;
                border-radius: {self.border_radius};
                font-weight: 500;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #219955;
            }}
            QPushButton:pressed {{
                background-color: #1e874b;
            }}
        """)
        self.watch_btn.clicked.connect(self.toggle_watcher)
        watch_layout.addWidget(self.watch_btn)
        
        # Bouton de configuration de surveillance avec style moderne
        self.config_watch_btn = QPushButton("⚙️  Configurer la surveillance")
        self.config_watch_btn.setToolTip("Configurer les options de surveillance")
        self.config_watch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.light_bg};
                color: {self.dark_text};
                padding: 10px 15px;
                border-radius: {self.border_radius};
                font-weight: 500;
                border: 1px solid #dadce0;
            }}
            QPushButton:hover {{
                background-color: #e0e0e0;
                border: 1px solid #c0c0c0;
            }}
            QPushButton:pressed {{
                background-color: #d0d0d0;
            }}
        """)
        self.config_watch_btn.clicked.connect(self.configure_watcher)
        watch_layout.addWidget(self.config_watch_btn)
        
        # Ajouter une étiquette d'état de surveillance élégante
        self.watch_status_label = QLabel("État: Inactif")
        self.watch_status_label.setStyleSheet(f"""
            font-style: italic;
            font-size: 11px;
            color: {self.dark_text};
            padding: 5px;
            background-color: rgba(0, 0, 0, 0.03);
            border-radius: 3px;
        """)
        watch_layout.addWidget(self.watch_status_label)
        
        nav_layout.addWidget(watch_group)
        
      
        # Option de statistiques moderne
        stats_btn = QPushButton("📊  Afficher les statistiques")
        stats_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.primary_color};
                color: {self.light_text};
                padding: 10px 15px;
                border-radius: {self.border_radius};
                font-weight: 500;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.hover_color};
            }}
            QPushButton:pressed {{
                background-color: #1e2b38;
            }}
        """)
        stats_btn.clicked.connect(self.show_statistics)
        title_bar_layout.addWidget(stats_btn)
        
        # Ajout du widget de navigation au splitter
        splitter.addWidget(navigation_widget)
        
        # Zone principale à droite avec style moderne
        main_area = QWidget()
        main_area.setStyleSheet(f"background-color: #ffffff;")
        main_area_layout = QVBoxLayout(main_area)
        main_area_layout.setContentsMargins(20, 20, 20, 20)
        main_area_layout.setSpacing(15)
        
        # Barre de recherche et filtres modernes
        search_filter_widget = QWidget()
        search_filter_layout = QHBoxLayout(search_filter_widget)
        search_filter_layout.setContentsMargins(0, 0, 0, 0)
        search_filter_layout.setSpacing(10)
        
        # Zone de recherche élégante
        search_container = QWidget()
        search_container.setStyleSheet(f"""
            background-color: {self.light_bg};
            border-radius: {self.border_radius};
            padding: 0;
        """)
        search_container_layout = QHBoxLayout(search_container)
        search_container_layout.setContentsMargins(10, 2, 10, 2)
        
        search_icon = QLabel("🔍")
        search_container_layout.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher des fichiers...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                padding: 8px;
                background: transparent;
                font-size: 13px;
            }}
        """)
        self.search_input.textChanged.connect(self.search_files)
        search_container_layout.addWidget(self.search_input)
        
        search_filter_layout.addWidget(search_container, 1)  # Stretch factor 1
        
        # Filtres rapides modernes
        filter_label = QLabel("Filtrer par:")
        filter_label.setStyleSheet(f"color: {self.dark_text}; font-weight: 500;")
        search_filter_layout.addWidget(filter_label)
        
        # Filtre par type élégant
        self.type_filter = QComboBox()
        self.type_filter.addItem("Tous")
        for type_name in ["Images", "Documents", "Vidéos", "Audios", "Archives", "Autres"]:
            self.type_filter.addItem(type_name)
        self.type_filter.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid #dadce0;
                border-radius: {self.border_radius};
                padding: 8px 15px;
                min-width: 120px;
            }}
            QComboBox:hover {{
                border: 1px solid #b8b8b8;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border-left: none;
            }}
        """)
        self.type_filter.currentTextChanged.connect(self.apply_filters)
        search_filter_layout.addWidget(self.type_filter)
        
        # Bouton de réinitialisation des filtres élégant
        reset_btn = QPushButton("Réinitialiser")
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.secondary_color};
                padding: 8px 15px;
                border: 1px solid {self.secondary_color};
                border-radius: {self.border_radius};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(52, 152, 219, 0.1);
            }}
            QPushButton:pressed {{
                background-color: rgba(52, 152, 219, 0.2);
            }}
        """)
        reset_btn.clicked.connect(self.reset_filters)
        search_filter_layout.addWidget(reset_btn)
        
        main_area_layout.addWidget(search_filter_widget)
        
        # Barre d'outils pour les actions sur les fichiers
        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet(f"""
            background-color: {self.light_bg};
            border-radius: {self.border_radius};
            padding: 5px;
        """)
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_layout.setSpacing(8)
        
        # Style pour les boutons d'action
        action_button_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {self.dark_text};
                padding: 8px 15px;
                border: none;
                border-radius: {self.border_radius};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 0, 0, 0.05);
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 0, 0, 0.1);
            }}
        """
        
        # Création des boutons d'action modernes
        new_folder_btn = QPushButton("📁 Nouveau dossier")
        new_folder_btn.setStyleSheet(action_button_style)
        new_folder_btn.clicked.connect(self.new_folder)
        toolbar_layout.addWidget(new_folder_btn)
        
        open_btn = QPushButton("📄 Ouvrir")
        open_btn.setStyleSheet(action_button_style)
        open_btn.clicked.connect(self.open_file)
        toolbar_layout.addWidget(open_btn)
        
        rename_btn = QPushButton("✏️ Renommer")
        rename_btn.setStyleSheet(action_button_style)
        rename_btn.clicked.connect(self.rename_file)
        toolbar_layout.addWidget(rename_btn)
        
        delete_btn = QPushButton("🗑️ Supprimer")
        delete_btn.setStyleSheet(action_button_style)
        delete_btn.clicked.connect(self.delete_file)
        toolbar_layout.addWidget(delete_btn)
        
        # Bouton d'outils supplémentaires avec menu déroulant moderne
        more_btn = QToolButton()
        more_btn.setText("⋮ Plus")
        more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        more_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                color: {self.dark_text};
                padding: 8px 15px;
                border: none;
                border-radius: {self.border_radius};
                font-weight: 500;
            }}
            QToolButton:hover {{
                background-color: rgba(0, 0, 0, 0.05);
            }}
            QToolButton:pressed {{
                background-color: rgba(0, 0, 0, 0.1);
            }}
            QToolButton::menu-indicator {{
                image: none;
            }}
        """)
        
        more_menu = QMenu(more_btn)
        more_menu.setStyleSheet(f"""
            QMenu {{
                background-color: white;
                border: 1px solid #dadce0;
                border-radius: {self.border_radius};
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                border-radius: 3px;
            }}
            QMenu::item:selected {{
                background-color: rgba(52, 152, 219, 0.1);
            }}
            QMenu::separator {{
                height: 1px;
                background-color: #dadce0;
                margin: 5px 15px;
            }}
        """)
        more_menu.addAction("📦 Compresser", self.compress_files)
        more_menu.addAction("📂 Décompresser", self.decompress_file)
        more_menu.addAction("🔍 Analyser les doublons", self.analyze_duplicates)
        more_menu.addSeparator()
        more_menu.addAction("🔄 Convertir des fichiers", self.convert_files)
        
        more_btn.setMenu(more_menu)
        toolbar_layout.addWidget(more_btn)
        toolbar_layout.addStretch()
        
        # Mode d'affichage élégant
        view_label = QLabel("Affichage:")
        view_label.setStyleSheet(f"color: {self.dark_text}; font-weight: 500;")
        toolbar_layout.addWidget(view_label)
        
        view_combo = QComboBox()
        view_combo.addItems(["Détails", "Icônes", "Liste"])
        view_combo.setCurrentIndex(0)
        view_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid #dadce0;
                border-radius: {self.border_radius};
                padding: 8px 15px;
                min-width: 100px;
            }}
            QComboBox:hover {{
                border: 1px solid #b8b8b8;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 20px;
                border-left: none;
            }}
        """)
        toolbar_layout.addWidget(view_combo)
        
        main_area_layout.addWidget(toolbar_widget)
        
        # Tableau des fichiers moderne
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels(["Nom", "Type", "Taille", "Date de modification", "Hash"])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        self.file_table.setStyleSheet(f"""
            QTableWidget {{
                border: 1px solid #dadce0;
                border-radius: {self.border_radius};
                gridline-color: #f5f5f5;
                selection-background-color: rgba(52, 152, 219, 0.2);
                selection-color: {self.dark_text};
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid #f5f5f5;
            }}
            QHeaderView::section {{
                background-color: {self.light_bg};
                color: {self.dark_text};
                padding: 10px;
                border: none;
                border-bottom: 1px solid #dadce0;
                font-weight: 600;
                font-size: 12px;
            }}
            QTableWidget::item:selected {{
                border-bottom: 1px solid rgba(52, 152, 219, 0.2);
            }}
        """)
        self.file_table.itemSelectionChanged.connect(self.update_selected_files)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.file_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self.show_context_menu)
        
        main_area_layout.addWidget(self.file_table)
        
        # Barre de progression moderne
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% - Organisation en cours...")
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: {self.border_radius};
                background-color: #f5f5f5;
                height: 20px;
                text-align: center;
                color: {self.dark_text};
                font-weight: 500;
            }}
            QProgressBar::chunk {{
                background-color: {self.secondary_color};
                border-radius: {self.border_radius};
            }}
        """)
        main_area_layout.addWidget(self.progress_bar)
        
        # Barre de statut moderne
        status_bar = QWidget()
        status_bar.setStyleSheet(f"""
            background-color: {self.light_bg};
            border-radius: {self.border_radius};
        """)
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(15, 10, 15, 10)
        
        self.status_label = QLabel("0 éléments")
        self.status_label.setStyleSheet(f"color: {self.dark_text}; font-weight: 500;")
        status_layout.addWidget(self.status_label)
        
        # Ajouter un espace extensible
        status_layout.addStretch()
        
        # Information sur l'espace disque avec style moderne
        self.space_label = QLabel("Espace libre: calcul en cours...")
        self.space_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.space_label.setStyleSheet(f"color: {self.dark_text}; font-weight: 500;")
        status_layout.addWidget(self.space_label)
        
        main_area_layout.addWidget(status_bar)
        
        # Ajout de la zone principale au splitter
        splitter.addWidget(main_area)
        
        # Configuration du splitter avec style moderne
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #dadce0;
                width: 1px;
            }
        """)
        splitter.setStretchFactor(0, 1)  # Navigation à gauche
        splitter.setStretchFactor(1, 3)  # Zone principale à droite
        
        main_layout.addWidget(splitter)
        
        self.setCentralWidget(central_widget)
        
        # Mettre à jour l'information sur l'espace disque
        self.update_disk_space()
    
    def create_tree_category(self, name, subtypes=None):
        """Crée une catégorie dans l'arborescence avec des sous-types optionnels"""
        category = QTreeWidgetItem(self.folder_tree, [name])
        
        # Utiliser des icônes modernes pour les catégories
        icon_map = {
            "Images": "🖼️",
            "Documents": "📄",
            "Vidéos": "🎬",
            "Musique": "🎵",
            "Archives": "📦"
        }
        
        # Ajouter une icône si elle existe dans notre dictionnaire
        category_icon = icon_map.get(name, "📁")
        category.setText(0, f"{category_icon}  {name}")
        category.setData(0, Qt.ItemDataRole.UserRole, name.lower())
        
        # Ajouter les sous-types si fournis
        if subtypes:
            for subtype in subtypes:
                subitem = QTreeWidgetItem(category, [f"{subtype}"])
                subitem.setData(0, Qt.ItemDataRole.UserRole, f"{name.lower()}_{subtype.lower()}")
        
        return category
    
    def create_action_button(self, layout, text, callback):
        """Crée un bouton d'action pour la barre d'outils"""
        # Cette méthode n'est plus nécessaire car nous avons créé 
        # individuellement chaque bouton dans setup_ui avec un style moderne
        pass
        
    def update_disk_space(self):
        """Met à jour l'information sur l'espace disque disponible"""
        try:
            if not self.current_directory:
                return
                
            disk_usage = shutil.disk_usage(self.current_directory)
            free_space = disk_usage.free
            total_space = disk_usage.total
            
            # Conversion en format lisible
            def format_size(size_bytes):
                if size_bytes < 1024**2:  # Moins de 1 MB
                    return f"{size_bytes / 1024:.1f} KB"
                elif size_bytes < 1024**3:  # Moins de 1 GB
                    return f"{size_bytes / (1024**2):.1f} MB"
                elif size_bytes < 1024**4:  # Moins de 1 TB
                    return f"{size_bytes / (1024**3):.1f} GB"
                else:
                    return f"{size_bytes / (1024**4):.1f} TB"
            
            free_space_str = format_size(free_space)
            total_space_str = format_size(total_space)
            percent_free = (free_space / total_space) * 100
            
            # Appliquer des couleurs différentes selon l'espace disponible
            color = "#27ae60"  # Vert pour beaucoup d'espace
            if percent_free < 10:
                color = self.accent_color  # Rouge pour peu d'espace
            elif percent_free < 25:
                color = "#f39c12"  # Orange pour espace modéré
                
            self.space_label.setText(f"Espace libre: <span style='color:{color};'>{free_space_str}</span> / {total_space_str}")
            self.space_label.setToolTip(f"{percent_free:.1f}% d'espace libre")
        except Exception as e:
            self.space_label.setText("Espace libre: Non disponible")
            
    def select_directory(self):
        """Ouvre une boîte de dialogue pour sélectionner un dossier"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner un dossier",
            self.current_directory or os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            self.current_directory = directory
            self.directory_label.setText(f"Dossier: {self.current_directory}")
            self.load_files(self.current_directory)
            self.update_disk_space()
            
    def folder_clicked(self, item, column):
        """Gère le clic sur un élément de l'arborescence des dossiers"""
        # Récupérer l'identifiant de l'élément
        item_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Ajouter ici la logique pour filtrer ou naviguer selon l'élément cliqué
        if item_id.startswith("images"):
            self.type_filter.setCurrentText("Images")
        elif item_id.startswith("documents"):
            self.type_filter.setCurrentText("Documents")
        elif item_id.startswith("vidéos"):
            self.type_filter.setCurrentText("Vidéos")
        elif item_id.startswith("musique"):
            self.type_filter.setCurrentText("Audios")
        elif item_id.startswith("archives"):
            self.type_filter.setCurrentText("Archives")
            
        # Si c'est un sous-type spécifique, on peut ajouter une recherche textuelle
        if "_" in item_id:
            extension = item_id.split("_")[1].upper()
            self.search_input.setText(f".{extension}")
            
    def search_files(self):
        """Filtre les fichiers selon le texte de recherche"""
        search_text = self.search_input.text().lower()
        self.apply_filters()
            
    def apply_filters(self):
        """Applique les filtres (recherche + type)"""
        search_text = self.search_input.text().lower()
        selected_type = self.type_filter.currentText()
        
        # Masquer/afficher les lignes selon les filtres
        for row in range(self.file_table.rowCount()):
            file_name = self.file_table.item(row, 0).text().lower()
            file_type = self.file_table.item(row, 1).text()
            
            # Vérifier si le fichier correspond au texte de recherche
            matches_search = search_text == "" or search_text in file_name
            
            # Vérifier si le fichier correspond au type sélectionné
            matches_type = selected_type == "Tous" or self.file_matches_type(file_type, selected_type)
            
            # Afficher ou masquer la ligne
            self.file_table.setRowHidden(row, not (matches_search and matches_type))
            
        # Mettre à jour le statut
        visible_count = sum(1 for row in range(self.file_table.rowCount()) if not self.file_table.isRowHidden(row))
        self.status_label.setText(f"{visible_count} éléments visibles sur {self.file_table.rowCount()}")
            
    def file_matches_type(self, file_type, selected_type):
        """Vérifie si un fichier correspond au type de filtre sélectionné"""
        if selected_type == "Images":
            return file_type in ["JPG", "JPEG", "PNG", "GIF", "BMP", "WEBP", "SVG", "TIFF"]
        elif selected_type == "Documents":
            return file_type in ["PDF", "DOC", "DOCX", "TXT", "RTF", "XLS", "XLSX", "PPT", "PPTX", "ODT"]
        elif selected_type == "Vidéos":
            return file_type in ["MP4", "AVI", "MKV", "MOV", "WMV", "FLV", "WEBM"]
        elif selected_type == "Audios":
            return file_type in ["MP3", "WAV", "OGG", "FLAC", "AAC", "M4A"]
        elif selected_type == "Archives":
            return file_type in ["ZIP", "RAR", "7Z", "TAR", "GZ", "BZ2"]
        else:
            return True
            
    def reset_filters(self):
        """Réinitialise tous les filtres"""
        self.search_input.clear()
        self.type_filter.setCurrentText("Tous")
        
        # Afficher toutes les lignes
        for row in range(self.file_table.rowCount()):
            self.file_table.setRowHidden(row, False)
            
        # Mettre à jour le statut
        self.status_label.setText(f"{self.file_table.rowCount()} éléments")
        
    def update_selected_files(self):
        """Met à jour la liste des fichiers sélectionnés"""
        self.selected_files = []
        
        for item in self.file_table.selectedItems():
            if item.column() == 0:  # Pour ne compter que les noms de fichiers (colonne 0)
                file_name = item.text()
                file_path = os.path.join(self.current_directory, file_name)
                self.selected_files.append(file_path)
                
    def show_context_menu(self, position):
        """Affiche un menu contextuel pour les fichiers sélectionnés"""
        context_menu = QMenu(self)
        context_menu.setStyleSheet(f"""
            QMenu {{
                background-color: white;
                border: 1px solid #dadce0;
                border-radius: {self.border_radius};
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 20px 8px 30px;
                border-radius: 3px;
            }}
            QMenu::item:selected {{
                background-color: rgba(52, 152, 219, 0.1);
            }}
            QMenu::separator {{
                height: 1px;
                background-color: #dadce0;
                margin: 5px 15px;
            }}
            QMenu::icon {{
                padding-left: 20px;
            }}
        """)
        
        if self.selected_files:
            context_menu.addAction("📄 Ouvrir", self.open_file)
            context_menu.addAction("📋 Copier", self.copy_files)
            context_menu.addAction("✂️ Couper", self.cut_files)
            context_menu.addSeparator()
            context_menu.addAction("✏️ Renommer", self.rename_file)
            context_menu.addAction("🗑️ Supprimer", self.delete_file)
            context_menu.addSeparator()
            context_menu.addAction("🔍 Propriétés", self.show_properties)
        else:
            context_menu.addAction("📁 Nouveau dossier", self.new_folder)
            context_menu.addAction("📋 Coller", self.paste_files)
            context_menu.addAction("🔄 Actualiser", lambda: self.load_files())
            
        context_menu.exec(self.file_table.mapToGlobal(position))
        
    def new_folder(self):
        """Crée un nouveau dossier"""
        folder_name, ok = QInputDialog.getText(
            self,
            "Nouveau dossier",
            "Nom du dossier:",
            QLineEdit.EchoMode.Normal,
            "Nouveau dossier"
        )
        
        if ok and folder_name:
            try:
                new_folder_path = os.path.join(self.current_directory, folder_name)
                os.makedirs(new_folder_path, exist_ok=True)
                self.load_files()  # Actualiser la liste des fichiers
                
                # Notification de succès élégante
                self.show_notification(f"Dossier '{folder_name}' créé avec succès !", "success")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Impossible de créer le dossier: {str(e)}")
                
    def show_notification(self, message, type_="info"):
        """Affiche une notification élégante à l'utilisateur"""
        notification = QDialog(self)
        notification.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        notification.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Configurer le style selon le type
        bg_color = "#3498db"  # Bleu pour info
        icon = "ℹ️"
        
        if type_ == "success":
            bg_color = "#2ecc71"  # Vert pour succès
            icon = "✅"
        elif type_ == "warning":
            bg_color = "#f39c12"  # Orange pour avertissement
            icon = "⚠️"
        elif type_ == "error":
            bg_color = "#e74c3c"  # Rouge pour erreur
            icon = "❌"
            
        layout = QHBoxLayout(notification)
        
        content = QWidget()
        content.setStyleSheet(f"""
            background-color: {bg_color};
            border-radius: 10px;
            color: white;
        """)
        content_layout = QHBoxLayout(content)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24px; padding-right: 10px;")
        content_layout.addWidget(icon_label)
        
        msg_label = QLabel(message)
        msg_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        content_layout.addWidget(msg_label)
        
        layout.addWidget(content)
        
        # Position en haut à droite
        desktop = QApplication.desktop()
        screen_rect = desktop.availableGeometry(self)
        notification.setGeometry(
            screen_rect.width() - 400,
            50,
            350,
            80
        )
        
        # Afficher et fermer après 3 secondes
        notification.show()
        QTimer.singleShot(3000, notification.close)
        
    def open_file(self):
        """Ouvre les fichiers sélectionnés"""
        if not self.selected_files:
            return
            
        for file_path in self.selected_files:
            try:
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            except Exception as e:
                QMessageBox.warning(self, "Avertissement", f"Impossible d'ouvrir {os.path.basename(file_path)}: {str(e)}")
                
    def rename_file(self):
        """Renomme le fichier sélectionné"""
        if len(self.selected_files) != 1:
            QMessageBox.warning(self, "Avertissement", "Veuillez sélectionner un seul fichier à renommer")
            return
            
        file_path = self.selected_files[0]
        old_name = os.path.basename(file_path)
        
        # Interface de renommage élégante
        rename_dialog = QDialog(self)
        rename_dialog.setWindowTitle("Renommer")
        rename_dialog.setFixedSize(400, 150)
        rename_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: white;
                border-radius: {self.border_radius};
            }}
        """)
        
        dialog_layout = QVBoxLayout(rename_dialog)
        
        # Étiquette d'information
        info_label = QLabel(f"Renommer '{old_name}'")
        info_label.setStyleSheet("font-weight: 600; font-size: 14px; margin-bottom: 10px;")
        dialog_layout.addWidget(info_label)
        
        # Champ de saisie
        new_name_input = QLineEdit(old_name)
        new_name_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 10px;
                border: 1px solid #dadce0;
                border-radius: {self.border_radius};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 2px solid {self.secondary_color};
            }}
        """)
        new_name_input.selectAll()
        dialog_layout.addWidget(new_name_input)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 8px 15px;
                background-color: #f5f5f5;
                border: none;
                border-radius: {self.border_radius};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #e0e0e0;
            }}
        """)
        cancel_btn.clicked.connect(rename_dialog.reject)
        buttons_layout.addWidget(cancel_btn)
        
        rename_btn = QPushButton("Renommer")
        rename_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 8px 15px;
                background-color: {self.secondary_color};
                color: white;
                border: none;
                border-radius: {self.border_radius};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #2980b9;
            }}
        """)
        rename_btn.clicked.connect(rename_dialog.accept)
        buttons_layout.addWidget(rename_btn)
        
        dialog_layout.addLayout(buttons_layout)
        
        # Exécuter le dialogue
        if rename_dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = new_name_input.text()
            
            if new_name and new_name != old_name:
                try:
                    new_path = os.path.join(os.path.dirname(file_path), new_name)
                    os.rename(file_path, new_path)
                    self.load_files()  # Actualiser
                    self.show_notification(f"'{old_name}' renommé en '{new_name}'", "success")
                except Exception as e:
                    QMessageBox.critical(self, "Erreur", f"Impossible de renommer le fichier: {str(e)}")
        
        # Ajouter un espace extensible
    
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
        program_directory = os.path.dirname(os.path.abspath(__file__))
        alternative_path = os.path.join(os.getcwd(), "json", "history.json")  # Dossier contenant ce fichier Python
        history_file = os.path.join(program_directory, "json", "history.json")
        if not os.path.exists(history_file):
        # Si le fichier n'est pas trouvé, essayer un chemin relatif au dossier courant
            alternative_path = os.path.join(os.getcwd(), "json", "history.json")
        
            if os.path.exists(alternative_path):
                history_file = alternative_path
            else:
                QMessageBox.warning(self, "Historique", 
                                f"Aucun historique trouvé. Chemin recherché:\n{history_file}\n"
                                f"et\n{alternative_path}")
                return
        try:
            # Charger le contenu du fichier JSON
            with open(history_file, "r", encoding="utf-8") as file:
                try:
                    history_data = json.load(file)
                except json.JSONDecodeError:
                    QMessageBox.critical(self, "Erreur", "Le fichier d'historique est corrompu.")
                    return
            
            # Afficher le chemin du fichier d'historique utilisé (pour le débogage)
            logger.debug(f"Fichier d'historique chargé: {history_file}")
            
            # Vérifier si l'historique est vide
            if not history_data:
                QMessageBox.information(self, "Historique", "L'historique est vide.")
                return
             # Création d'une fenêtre de dialogue pour afficher l'historique
            dialog = QDialog(self)
            dialog.setWindowTitle("Historique des actions")
            dialog.resize(900, 600)  # Taille initiale plus grande
            
            # Création d'un layout vertical pour la fenêtre
            layout = QVBoxLayout(dialog)
            
            # Informations sur le fichier d'historique
            info_label = QLabel(f"Fichier d'historique: {history_file}")
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            
            # Groupe pour les filtres
            filter_group = QGroupBox("Filtres")
            filter_layout = QHBoxLayout()
            
            # Filtre par date
            date_label = QLabel("Date:")
            date_filter = QDateEdit()
            date_filter.setCalendarPopup(True)
            date_filter.setDate(QDate.currentDate())
            date_filter.setEnabled(False)  # Désactivé par défaut
            
            date_check = QCheckBox("Filtrer")
            
            # Filtre par type d'action
            action_label = QLabel("Action:")
            action_filter = QComboBox()
            action_filter.addItem("Toutes les actions")
            
            # Extraire les types d'actions uniques
            actions = set()
            for entry in history_data:
                actions.add(entry.get("action", "Inconnue"))
            
            for action in sorted(actions):
                action_filter.addItem(action)
            
            # Bouton de recherche
            search_label = QLabel("Recherche:")
            search_input = QLineEdit()
            search_input.setPlaceholderText("Rechercher dans les chemins...")
            
            # Ajout des widgets de filtre au layout
            filter_layout.addWidget(date_label)
            filter_layout.addWidget(date_filter)
            filter_layout.addWidget(date_check)
            filter_layout.addSpacing(20)
            filter_layout.addWidget(action_label)
            filter_layout.addWidget(action_filter)
            filter_layout.addSpacing(20)
            filter_layout.addWidget(search_label)
            filter_layout.addWidget(search_input)
            
            filter_group.setLayout(filter_layout)
            layout.addWidget(filter_group)
            
            # Création du tableau pour afficher l'historique
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Date et heure", "Action", "Source", "Destination"])
            
            # Ajuster les colonnes pour qu'elles s'adaptent au contenu
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)


            # Fonction pour rafraîchir le tableau avec les filtres
            def refresh_table():
                table.setRowCount(0)  # Effacer le tableau
                
                filtered_history = history_data
                
                # Appliquer le filtre de date
                if date_check.isChecked():
                    selected_date = date_filter.date().toString("yyyy-MM-dd")
                    filtered_history = [
                        entry for entry in filtered_history
                        if entry.get("date", "").startswith(selected_date)
                    ]

                # Appliquer le filtre d'action
                if action_filter.currentText() != "Toutes les actions":
                    selected_action = action_filter.currentText()
                    filtered_history = [
                        entry for entry in filtered_history
                        if entry.get("action") == selected_action
                    ]

                    # Appliquer la recherche textuelle
                if search_text := search_input.text().strip():
                    search_text = search_text.lower()
                    filtered_history = [
                        entry for entry in filtered_history
                        if (search_text in entry.get("source", "").lower() or 
                            search_text in entry.get("destination", "").lower())
                    ]
                 # Tri par date décroissante (le plus récent en premier)
                filtered_history.sort(key=lambda x: x.get("date", ""), reverse=True)
                
                # Remplir le tableau
                table.setRowCount(len(filtered_history))

                for row, entry in enumerate(filtered_history):
                # Formater la date et l'heure
                    try:
                        date_str = entry.get("date", "")
                        datetime_obj = datetime.fromisoformat(date_str)
                        formatted_date = datetime_obj.strftime("%d/%m/%Y %H:%M:%S")
                    except (ValueError, TypeError):
                        formatted_date = date_str
                    
                    # Ajouter les éléments dans le tableau
                    table.setItem(row, 0, QTableWidgetItem(formatted_date))
                    table.setItem(row, 1, QTableWidgetItem(entry.get("action", "")))
                    
                    # Raccourcir les chemins longs pour l'affichage
                    source_path = entry.get("source", "")
                    dest_path = entry.get("destination", "N/A")
                    
                    # Ajouter les éléments source et destination
                    source_item = QTableWidgetItem(source_path)
                    source_item.setToolTip(source_path)  # Afficher le chemin complet au survol
                    table.setItem(row, 2, source_item)
                    
                    dest_item = QTableWidgetItem(dest_path)
                    dest_item.setToolTip(dest_path)  # Afficher le chemin complet au survol
                    table.setItem(row, 3, dest_item)

            # Connecter les widgets de filtre aux événements
            date_check.stateChanged.connect(lambda: date_filter.setEnabled(date_check.isChecked()))
            date_check.stateChanged.connect(refresh_table)
            date_filter.dateChanged.connect(refresh_table)
            action_filter.currentIndexChanged.connect(refresh_table)
            search_input.textChanged.connect(refresh_table)
            
            # Ajouter le tableau au layout
            layout.addWidget(table)
            
            # Boutons d'action
            button_layout = QHBoxLayout()
            
            export_button = QPushButton("Exporter")
            clear_button = QPushButton("Effacer l'historique")
            close_button = QPushButton("Fermer")
            
            button_layout.addWidget(export_button)
            button_layout.addWidget(clear_button)
            button_layout.addStretch()
            button_layout.addWidget(close_button)
            
            layout.addLayout(button_layout)
            
            # Label pour afficher les statistiques
            stats_label = QLabel()
            stats_label.setText(f"Total: {len(history_data)} entrées")
            layout.addWidget(stats_label)
            def export_history():
                options = QFileDialog.Options()  # Correction ici
                filename, _ = QFileDialog.getSaveFileName(
                    None,  # `dialog` n'est pas défini, donc passe `None` si ce n'est pas un widget PyQt
                    "Exporter l'historique",
                    "",
                    "Fichiers CSV (*.csv);;Fichiers JSON (*.json)",
                    options=options
                )
                
                if not filename:
                    return
                    
                try:
                    if filename.endswith(".csv"):
                        with open(filename, "w", encoding="utf-8", newline="") as f:
                            writer = csv.writer(f)
                            writer.writerow(["Date", "Action", "Source", "Destination"])
                            for entry in history_data:
                                writer.writerow([
                                    entry.get("date", ""),
                                    entry.get("action", ""),
                                    entry.get("source", ""),
                                    entry.get("destination", "N/A")
                                ])
                    elif filename.endswith(".json"):
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(history_data, f, indent=4)
                    else:
                        # Ajouter l'extension par défaut
                        filename += ".csv"
                        with open(filename, "w", encoding="utf-8", newline="") as f:
                            writer = csv.writer(f)
                            writer.writerow(["Date", "Action", "Source", "Destination"])
                            for entry in history_data:
                                writer.writerow([
                                    entry.get("date", ""),
                                    entry.get("action", ""),
                                    entry.get("source", ""),
                                    entry.get("destination", "N/A")
                                ])
                    
                    QMessageBox.information(dialog, "Exportation", f"L'historique a été exporté avec succès vers {filename}")
                except Exception as e:
                    QMessageBox.critical(dialog, "Erreur", f"Erreur lors de l'exportation: {str(e)}")
            
            # Fonction pour effacer l'historique
            def clear_history():
                reply = QMessageBox.question(
                    dialog,
                    "Confirmation",
                    "Êtes-vous sûr de vouloir effacer tout l'historique ?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    try:
                        # Sauvegarder une copie de sauvegarde
                        backup_file = history_file + ".bak"
                        shutil.copy2(history_file, backup_file)
                        
                        # Écrire un tableau vide
                        with open(history_file, "w", encoding="utf-8") as f:
                            json.dump([], f)
                        
                        QMessageBox.information(
                            dialog,
                            "Historique effacé",
                            f"L'historique a été effacé. Une sauvegarde a été créée: {os.path.basename(backup_file)}"
                        )
                        
                        # Fermer la fenêtre
                        dialog.accept()
                    except Exception as e:
                        QMessageBox.critical(dialog, "Erreur", f"Erreur lors de l'effacement: {str(e)}")
            
            # Connecter les boutons
            export_button.clicked.connect(export_history)
            clear_button.clicked.connect(clear_history)
            close_button.clicked.connect(dialog.accept)
            
            # Double-clic sur un élément pour afficher plus de détails
            def show_details(row, column):
                source = table.item(row, 2).text()
                destination = table.item(row, 3).text()
                action = table.item(row, 1).text()
                date = table.item(row, 0).text()
                
                detail_dialog = QDialog(dialog)
                detail_dialog.setWindowTitle(f"Détails - {action}")
                detail_dialog.resize(700, 300)
                
                detail_layout = QVBoxLayout(detail_dialog)
                
                detail_form = QFormLayout()
                detail_form.addRow("Date:", QLabel(date))
                detail_form.addRow("Action:", QLabel(action))
                
                source_text = QTextEdit()
                source_text.setReadOnly(True)
                source_text.setText(source)
                source_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

                
                dest_text = QTextEdit()
                dest_text.setReadOnly(True)
                dest_text.setText(destination)
                source_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

                
                detail_form.addRow("Source:", source_text)
                detail_form.addRow("Destination:", dest_text)
                
                detail_layout.addLayout(detail_form)
                
                # Boutons d'action pour le fichier source et destination
                file_buttons_layout = QHBoxLayout()
                
                # Vérifier si les fichiers existent
                source_exists = os.path.exists(source)
                dest_exists = os.path.exists(destination) and destination != "N/A"
                
                if source_exists:
                    open_source_button = QPushButton("Ouvrir dossier source")
                    open_source_button.clicked.connect(lambda: os.startfile(os.path.dirname(source)))
                    file_buttons_layout.addWidget(open_source_button)
                
                if dest_exists:
                    open_dest_button = QPushButton("Ouvrir dossier destination")
                    open_dest_button.clicked.connect(lambda: os.startfile(os.path.dirname(destination)))
                    file_buttons_layout.addWidget(open_dest_button)
                
                if file_buttons_layout.count() > 0:
                    detail_layout.addLayout(file_buttons_layout)
                
                button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)

                button_box.accepted.connect(detail_dialog.accept)
                detail_layout.addWidget(button_box)
                
                detail_dialog.exec()
            
            table.cellDoubleClicked.connect(show_details)
            
            # Charger les données initiales
            refresh_table()
            
            # Mettre à jour les statistiques
            def update_stats():
                visible_rows = table.rowCount()
                total_entries = len(history_data)
                if visible_rows == total_entries:
                    stats_label.setText(f"Total: {total_entries} entrées")
                else:
                    stats_label.setText(f"Affichées: {visible_rows} sur {total_entries} entrées")
            
            # Connecter les événements pour mettre à jour les statistiques
            date_check.stateChanged.connect(update_stats)
            date_filter.dateChanged.connect(update_stats)
            action_filter.currentIndexChanged.connect(update_stats)
            search_input.textChanged.connect(update_stats)
            
            # Afficher la fenêtre
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'affichage de l'historique: {str(e)}")
            import traceback
            logger.error(f"Exception dans afficher_historique: {traceback.format_exc()}")
            
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

def lancer_interface():
        app = QApplication(sys.argv)
        window = FileManager()
        window.show()
        sys.exit(app.exec())