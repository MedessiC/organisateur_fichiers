import os
import time
from organizer import supprimer_doublons, classer_fichier_par_type
from logger import logger
from watcher import demarrer_surveillance
from history import afficher_historique

# Juste pour test ou accès rapide
afficher_historique()

def organiser_dossier(dossier):
    if not os.path.isdir(dossier):
        logger.error("❌ Le chemin fourni n'est pas un dossier valide.")
        return

    logger.info("🧹 Début de l'organisation des fichiers...")

    # 1. Trier par type
    classer_fichier_par_type(dossier)

    # 2. Supprimer les doublons
    supprimer_doublons(dossier)

    logger.info("✅ Organisation terminée avec succès !")

def main():
    print("🗂️ Bienvenue dans l'organisateur de fichiers MIDEESSI")
    dossier_cible = input("📁 Entrez le chemin du dossier à organiser : ").strip()

    if not os.path.isdir(dossier_cible):
        logger.error("❌ Le chemin fourni est invalide ou n'existe pas.")
        return

    # Demander à l'utilisateur s'il veut activer la surveillance continue
    reponse = input("👀 Activer la surveillance automatique du dossier ? (o/n) : ").strip().lower()
    
    if reponse == 'o':
        logger.info("👁️ Surveillance en temps réel activée.")
        # Démarre la surveillance dans un thread séparé
        try:
            classer_fichier_par_type(dossier_cible)
            supprimer_doublons(dossier_cible)
            demarrer_surveillance(dossier_cible)
        except Exception as e:
            logger.error(f"⚠️ Erreur lors du démarrage de la surveillance : {e}")
    else:
        logger.info("⚙️ Mode manuel sélectionné.")
        organiser_dossier(dossier_cible)

if __name__ == "__main__":
    main()
