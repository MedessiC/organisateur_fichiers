import json
import os
from datetime import datetime, timedelta

HISTORY_FILE = "logs/historique.json"
DUREE_CONSERVATION_JOURS = 30

def enregistrer_action(action, source, destination=None):
    """Enregistre une action dans le fichier d’historique"""
    historique = charger_historique()

    nouvelle_entree = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "source": source,
        "destination": destination
    }
    historique.append(nouvelle_entree)
    
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(historique, f, indent=4, ensure_ascii=False)

def charger_historique():
    """Charge l'historique et supprime les anciennes entrées (30 jours)"""
    if not os.path.exists(HISTORY_FILE):
        return []

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        historique = json.load(f)

    historique_filtré = []
    maintenant = datetime.now()
    for action in historique:
        date_action = datetime.strptime(action["date"], "%Y-%m-%d %H:%M:%S")
        if maintenant - date_action <= timedelta(days=DUREE_CONSERVATION_JOURS):
            historique_filtré.append(action)

    # Écraser avec l’historique nettoyé
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(historique_filtré, f, indent=4, ensure_ascii=False)

    return historique_filtré

def afficher_historique():
    """Affiche l’historique dans la console"""
    historique = charger_historique()
    if not historique:
        print("Aucune action enregistrée.")
        return
    for action in historique:
        print(f"[{action['date']}] {action['action']} : {action['source']} → {action.get('destination', 'N/A')}")
