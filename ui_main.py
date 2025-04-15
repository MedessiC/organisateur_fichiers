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
    sys.exit(app.exec())