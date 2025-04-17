import os
import json
from pathlib import Path

PREFERENCE_FILE = "user_patterns.json"

def charger_modeles():
    """Charge les modèles de rangement depuis un fichier JSON."""
    if not os.path.exists(PREFERENCE_FILE):
        return {}
    with open(PREFERENCE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def sauvegarder_modeles(modeles):
    """Sauvegarde les modèles dans un fichier JSON."""
    with open(PREFERENCE_FILE, "w", encoding="utf-8") as f:
        json.dump(modeles, f, indent=4)

def enregistrer_habitude(extension, dossier_cible):
    """Enregistre une habitude de rangement pour une extension donnée."""
    modeles = charger_modeles()
    modeles[extension] = dossier_cible
    sauvegarder_modeles(modeles)

def proposer_destination(extension, fallback_path):
    """Retourne le chemin préféré si existant, sinon une suggestion par défaut."""
    modeles = charger_modeles()
    return modeles.get(extension.lower(), fallback_path)

def afficher_modeles():
    """Affiche les préférences connues."""
    modeles = charger_modeles()
    print("📚 Modèles d’organisation connus :")
    for ext, path in modeles.items():
        print(f"{ext} → {path}")
