# -*- coding: utf-8 -*-
# Ce fichier gère l'historique des actions effectuées par l'utilisateur, y compris la sauvegarde, le chargement et l'affichage de l'historique.
# Il utilise un fichier JSON pour stocker les données et un fichier de log pour enregistrer les erreurs et les actions.
# Il inclut également des fonctionnalités pour nettoyer l'historique en fonction d'une période de rétention définie et pour exporter l'historique dans différents formats.

# Importation des bibliothèques nécessaires
import sys

import os
import json
import logging
import gzip
from datetime import datetime, timedelta
from tabulate import tabulate

# Configuration
HISTORY_FILE = "history.json"
RETENTION_DAYS = 30
LOG_FILE = r"logs/history.log"

# Configurer le logger
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def charger_historique():
    """
    Charge l'historique depuis le fichier JSON ou GZIP si disponible.
    """
    if not os.path.exists(HISTORY_FILE):
        logger.warning("Fichier d'historique introuvable.")
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de décodage JSON : {e}")
        return []

def sauvegarder_historique(historique):
    """
    Sauvegarde l'historique dans un fichier JSON.
    """
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(historique, f, indent=4)
        logger.info("Historique sauvegardé avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de l'historique : {e}")

def enregistrer_action(action: str, chemin_source: str, chemin_destination: str = None):
    """
    Ajoute une action à l'historique avec validation des entrées.
    """
    if not isinstance(action, str) or not action:
        raise ValueError("L'action doit être une chaîne non vide.")
    if not os.path.exists(chemin_source):
        raise ValueError(f"Le chemin source n'existe pas : {chemin_source}")

    historique = charger_historique()
    nouvelle_entree = {
        "date": datetime.now().isoformat(),
        "action": action,
        "source": chemin_source,
        "destination": chemin_destination or "N/A"
    }
    historique.append(nouvelle_entree)
    sauvegarder_historique(historique)
    logger.info(f"Action enregistrée : {action}, source : {chemin_source}, destination : {chemin_destination}")

def afficher_historique():
    """
    Affiche l'historique en format tabulaire.
    """
    historique = charger_historique()
    if not historique:
        print("📂 Aucun historique disponible.")
        return

    table = [[entry["date"], entry["action"], entry["source"], entry.get("destination", "N/A")] for entry in historique]
    print("\n===== 📊 HISTORIQUE =====")
    print(tabulate(table, headers=["Date", "Action", "Source", "Destination"]))

def nettoyer_historique():
    """
    Supprime les entrées de l'historique vieilles de plus de RETENTION_DAYS jours.
    """
    historique = charger_historique()
    maintenant = datetime.now()
    filtré = [
        h for h in historique
        if datetime.fromisoformat(h["date"]) > maintenant - timedelta(days=RETENTION_DAYS)
    ]
    sauvegarder_historique(filtré)
    logger.info(f"Historique nettoyé. Entrées restantes : {len(filtré)}")

def exporter_historique(format="csv"):
    """
    Exporte l'historique dans le format spécifié (CSV ou JSON).
    """
    historique = charger_historique()
    if not historique:
        logger.warning("Aucun historique à exporter.")
        return

    if format == "csv":
        try:
            with open("history.csv", "w", encoding="utf-8") as f:
                f.write("Date,Action,Source,Destination\n")
                for entry in historique:
                    f.write(f'{entry["date"]},{entry["action"]},{entry["source"]},{entry.get("destination", "N/A")}\n')
            logger.info("Historique exporté au format CSV.")
        except Exception as e:
            logger.error(f"Erreur lors de l'exportation au format CSV : {e}")
    elif format == "json":
        try:
            with open("history_export.json", "w", encoding="utf-8") as f:
                json.dump(historique, f, indent=4)
            logger.info("Historique exporté au format JSON.")
        except Exception as e:
            logger.error(f"Erreur lors de l'exportation au format JSON : {e}")
    else:
        logger.warning(f"Format d'exportation non pris en charge : {format}")

# Exemple d'utilisation
if __name__ == "__main__":
    enregistrer_action("Copie", r"C:\Users\Medessi Cvi\Desktop\Livre")
    afficher_historique()
    nettoyer_historique()
    exporter_historique("csv")
