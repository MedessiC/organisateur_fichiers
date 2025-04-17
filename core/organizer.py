import os
import shutil
import hashlib
import datetime
import time
import logging
import re
from pathlib import Path
import sys

import locale

# Configurer la langue en français
locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

def classer_par_date(dossier, mode_simulation=False, limite_traitement=None):
sys.stdout.reconfigure(encoding='utf-8')

# Dictionnaire d'extensions par type
TYPES_FICHIERS = {
    "Images": [".png", ".jpg", ".jpeg", ".gif", ".bmp"],
    "Vidéos": [".mp4", ".mkv", ".avi", ".mov"],
    "Documents": [".pdf", ".docx", ".txt", ".xlsx", ".pptx"],
    "Audios": [".mp3", ".wav", ".aac"],
    "Archives": [".zip", ".rar", ".7z"],
}

# Configuration du système de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/organizer_log.txt')
    ]
)
logger = logging.getLogger('organizer')

def creer_dossier_si_absent(path):
    """Crée un dossier s'il n'existe pas déjà."""
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Dossier créé: {path}")

def calculer_hash(fichier):
    """Calcule le hash MD5 d'un fichier."""
    hasher = hashlib.md5()
    try:
        with open(fichier, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Erreur lors du hash du fichier {fichier} : {e}")
        return None

def obtenir_date_creation(chemin_fichier):
    """Retourne la date de création ou de modification d'un fichier."""
    try:
        # Essayer d'obtenir la date de création (Windows) ou de status change (Unix)
        date = os.path.getctime(chemin_fichier)
        # Si pas disponible, utiliser la date de dernière modification
        if not date:
            date = os.path.getmtime(chemin_fichier)
        return datetime.datetime.fromtimestamp(date)
    except Exception as e:
        logger.warning(f"Impossible d'obtenir la date du fichier {chemin_fichier}: {e}")
        return datetime.datetime.now()

def generer_nouveau_nom(fichier, date=None):
    """
    Génère un nouveau nom pour le fichier basé sur un format cohérent.
    Format: YYYYMMDD_type_nom-original.extension
    """
    chemin = Path(fichier)
    nom_original = chemin.stem
    extension = chemin.suffix.lower()
    
    # Déterminer le type de fichier
    type_fichier = "autre"
    for type_, extensions in TYPES_FICHIERS.items():
        if extension in extensions:
            type_fichier = type_.lower().rstrip('s')  # Enlever le 's' final (Images -> image)
            break
    
    # Utiliser la date fournie ou obtenir la date du fichier
    if not date:
        date = obtenir_date_creation(fichier)
    
    # Formater la date en YYYYMMDD
    date_str = date.strftime("%Y%m%d")
    
    # Nettoyer le nom original (supprimer les caractères spéciaux, remplacer espaces par tirets)
    nom_nettoye = re.sub(r'[^\w\s-]', '', nom_original).strip().lower()
    nom_nettoye = re.sub(r'[-\s]+', '-', nom_nettoye)
    
    # Formater le nouveau nom
    nouveau_nom = f"{date_str}_{type_fichier}_{nom_nettoye}{extension}"
    
    return nouveau_nom

def verifier_conflit_fichier(chemin_destination):
    """
    Vérifie si un fichier existe déjà à l'emplacement de destination.
    Si oui, ajoute un suffixe numérique.
    """
    chemin = Path(chemin_destination)
    compteur = 1
    nouveau_chemin = chemin_destination
    
    while os.path.exists(nouveau_chemin):
        nouveau_nom = f"{chemin.stem}_{compteur}{chemin.suffix}"
        nouveau_chemin = os.path.join(os.path.dirname(chemin_destination), nouveau_nom)
        compteur += 1
    
    return nouveau_chemin

def classer_fichier_par_type(dossier, mode_simulation=False, limite_traitement=None):
    """
    Classe les fichiers par type dans des sous-dossiers.
    
    Args:
        dossier: Le dossier à organiser
        mode_simulation: Si True, montre les actions sans les exécuter
        limite_traitement: Nombre maximum de fichiers à traiter (None pour tous)
    """
    fichiers = [f for f in os.listdir(dossier) if os.path.isfile(os.path.join(dossier, f))]
    
    # Appliquer la limite si spécifiée
    if limite_traitement and len(fichiers) > limite_traitement:
        logger.info(f"Limitation à {limite_traitement} fichiers sur {len(fichiers)} au total")
        fichiers = fichiers[:limite_traitement]
    
    fichiers_traites = 0
    for fichier in fichiers:
        chemin_complet = os.path.join(dossier, fichier)

        if os.path.isfile(chemin_complet):
            _, extension = os.path.splitext(fichier)
            extension = extension.lower()

            destination = "Autres"
            for type_, extensions in TYPES_FICHIERS.items():
                if extension in extensions:
                    destination = type_
                    break

            dossier_destination = os.path.join(dossier, destination)
            
            if not mode_simulation:
                creer_dossier_si_absent(dossier_destination)
            
            nouveau_chemin = os.path.join(dossier_destination, fichier)
            nouveau_chemin = verifier_conflit_fichier(nouveau_chemin)
            
            if mode_simulation:
                logger.info(f"[SIMULATION] Déplacement: {fichier} → {destination}/{os.path.basename(nouveau_chemin)}")
            else:
                try:
                    shutil.move(chemin_complet, nouveau_chemin)
                    logger.info(f"Déplacé: {fichier} → {destination}/{os.path.basename(nouveau_chemin)}")
                    fichiers_traites += 1
                except Exception as e:
                    logger.error(f"Erreur lors du déplacement de {fichier}: {e}")
                    # Attendre et réessayer une fois
                    try:
                        time.sleep(1)  # Attendre 1 seconde
                        shutil.move(chemin_complet, nouveau_chemin)
                        logger.info(f"Déplacé après reprise: {fichier} → {destination}/{os.path.basename(nouveau_chemin)}")
                        fichiers_traites += 1
                    except Exception as e2:
                        logger.error(f"Échec définitif pour {fichier}: {e2}")
    
    return fichiers_traites

def classer_par_date(dossier, mode_simulation=False, limite_traitement=None):
    """
    Organise les fichiers par année/mois dans des sous-dossiers basés sur leur date de création.
    
    Args:
        dossier: Le dossier à organiser
        mode_simulation: Si True, montre les actions sans les exécuter
        limite_traitement: Nombre maximum de fichiers à traiter (None pour tous)
    """
    fichiers = [f for f in os.listdir(dossier) if os.path.isfile(os.path.join(dossier, f))]
    
    # Appliquer la limite si spécifiée
    if limite_traitement and len(fichiers) > limite_traitement:
        logger.info(f"Limitation à {limite_traitement} fichiers sur {len(fichiers)} au total")
        fichiers = fichiers[:limite_traitement]
    
    fichiers_traites = 0
    for fichier in fichiers:
        chemin_complet = os.path.join(dossier, fichier)
        
        # Obtenir la date du fichier
        date_fichier = obtenir_date_creation(chemin_complet)
        
        # Créer les dossiers année/mois
        annee = str(date_fichier.year)
        mois = date_fichier.strftime("%m-%B")  # Format "05-May"
        
        chemin_destination = os.path.join(dossier, annee, mois)
        
        if not mode_simulation:
            creer_dossier_si_absent(chemin_destination)
        
        nouveau_chemin = os.path.join(chemin_destination, fichier)
        nouveau_chemin = verifier_conflit_fichier(nouveau_chemin)
        
        if mode_simulation:
            logger.info(f"[SIMULATION] Déplacement par date: {fichier} → {annee}/{mois}/{os.path.basename(nouveau_chemin)}")
        else:
            try:
                shutil.move(chemin_complet, nouveau_chemin)
                logger.info(f"Déplacé par date: {fichier} → {annee}/{mois}/{os.path.basename(nouveau_chemin)}")
                fichiers_traites += 1
            except Exception as e:
                logger.error(f"Erreur lors du déplacement de {fichier}: {e}")
                # Attendre et réessayer une fois
                try:
                    time.sleep(1)  # Attendre 1 seconde
                    shutil.move(chemin_complet, nouveau_chemin)
                    logger.info(f"Déplacé après reprise: {fichier} → {annee}/{mois}/{os.path.basename(nouveau_chemin)}")
                    fichiers_traites += 1
                except Exception as e2:
                    logger.error(f"Échec définitif pour {fichier}: {e2}")
    
    return fichiers_traites

def renommer_fichiers(dossier, mode_simulation=False, limite_traitement=None):
    """
    Renomme les fichiers selon un format cohérent dans le dossier spécifié.
    
    Args:
        dossier: Le dossier contenant les fichiers à renommer
        mode_simulation: Si True, montre les actions sans les exécuter
        limite_traitement: Nombre maximum de fichiers à traiter (None pour tous)
    """
    fichiers = [f for f in os.listdir(dossier) if os.path.isfile(os.path.join(dossier, f))]
    
    # Appliquer la limite si spécifiée
    if limite_traitement and len(fichiers) > limite_traitement:
        logger.info(f"Limitation à {limite_traitement} fichiers sur {len(fichiers)} au total")
        fichiers = fichiers[:limite_traitement]
    
    fichiers_traites = 0
    for fichier in fichiers:
        chemin_complet = os.path.join(dossier, fichier)
        
        # Générer le nouveau nom
        date_fichier = obtenir_date_creation(chemin_complet)
        nouveau_nom = generer_nouveau_nom(fichier, date_fichier)
        nouveau_chemin = os.path.join(dossier, nouveau_nom)
        
        # Vérifier s'il y a déjà un fichier avec ce nom
        nouveau_chemin = verifier_conflit_fichier(nouveau_chemin)
        nouveau_nom = os.path.basename(nouveau_chemin)
        
        if fichier == nouveau_nom:
            logger.info(f"Pas besoin de renommer: {fichier}")
            continue
        
        if mode_simulation:
            logger.info(f"[SIMULATION] Renommage: {fichier} → {nouveau_nom}")
        else:
            try:
                os.rename(chemin_complet, nouveau_chemin)
                logger.info(f"Renommé: {fichier} → {nouveau_nom}")
                fichiers_traites += 1
            except Exception as e:
                logger.error(f"Erreur lors du renommage de {fichier}: {e}")
                # Attendre et réessayer une fois
                try:
                    time.sleep(1)  # Attendre 1 seconde
                    os.rename(chemin_complet, nouveau_chemin)
                    logger.info(f"Renommé après reprise: {fichier} → {nouveau_nom}")
                    fichiers_traites += 1
                except Exception as e2:
                    logger.error(f"Échec définitif pour {fichier}: {e2}")
    
    return fichiers_traites

def supprimer_doublons(dossier, mode_simulation=False, limite_traitement=None):
    """
    Supprime les fichiers en double dans le dossier donné.
    
    Args:
        dossier: Le dossier à analyser pour les doublons
        mode_simulation: Si True, montre les actions sans les exécuter
        limite_traitement: Nombre maximum de fichiers à traiter (None pour tous)
    """
    fichiers_vus = {}
    doublons_supprimes = 0
    fichiers_traites = 0
    
    # Collecter tous les fichiers
    tous_fichiers = []
    for racine, _, fichiers in os.walk(dossier):
        for nom_fichier in fichiers:
            tous_fichiers.append(os.path.join(racine, nom_fichier))
    
    # Appliquer la limite si spécifiée
    if limite_traitement and len(tous_fichiers) > limite_traitement:
        logger.info(f"Limitation à {limite_traitement} fichiers sur {len(tous_fichiers)} au total")
        tous_fichiers = tous_fichiers[:limite_traitement]
    
    for chemin in tous_fichiers:
        fichiers_traites += 1
        hash_fichier = calculer_hash(chemin)
        if not hash_fichier:
            continue

        if hash_fichier in fichiers_vus:
            logger.info(f"Doublon trouvé : {chemin} (identique à {fichiers_vus[hash_fichier]})")
            if not mode_simulation:
                try:
                    os.remove(chemin)
                    logger.info(f"Supprimé: {chemin}")
                    doublons_supprimes += 1
                except Exception as e:
                    logger.error(f"Erreur en supprimant {chemin} : {e}")
                    # Attendre et réessayer une fois
                    try:
                        time.sleep(1)  # Attendre 1 seconde
                        os.remove(chemin)
                        logger.info(f"Supprimé après reprise: {chemin}")
                        doublons_supprimes += 1
                    except Exception as e2:
                        logger.error(f"Échec définitif pour {chemin}: {e2}")
            else:
                logger.info(f"[SIMULATION] Suppression: {chemin}")
        else:
            fichiers_vus[hash_fichier] = chemin

    resultat = f"{doublons_supprimes} doublon(s) supprimé(s) sur {fichiers_traites} fichiers traités."
    logger.info(resultat)
    return doublons_supprimes

# Exemple d'utilisation
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Organisateur de fichiers intelligent")
    parser.add_argument("dossier", help="Dossier à organiser")
    parser.add_argument("--type", action="store_true", help="Classer par type de fichier")
    parser.add_argument("--date", action="store_true", help="Classer par date (année/mois)")
    parser.add_argument("--renommer", action="store_true", help="Renommer les fichiers selon un format cohérent")
    parser.add_argument("--doublons", action="store_true", help="Supprimer les doublons")
    parser.add_argument("--simulation", action="store_true", help="Mode simulation (n'exécute pas les actions)")
    parser.add_argument("--limite", type=int, help="Limite de fichiers à traiter par opération")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.dossier):
        logger.error(f"Le dossier {args.dossier} n'existe pas.")
        exit(1)
    
    logger.info(f"Début de l'organisation du dossier: {args.dossier}")
    
    if args.simulation:
        logger.info("MODE SIMULATION ACTIVÉ - Aucune action ne sera réellement effectuée")
    
    if args.type:
        logger.info("Classification par type...")
        nb = classer_fichier_par_type(args.dossier, args.simulation, args.limite)
        logger.info(f"{nb} fichiers traités par type")
    
    if args.date:
        logger.info("Classification par date...")
        nb = classer_par_date(args.dossier, args.simulation, args.limite)
        logger.info(f"{nb} fichiers traités par date")
    
    if args.renommer:
        logger.info("Renommage des fichiers...")
        nb = renommer_fichiers(args.dossier, args.simulation, args.limite)
        logger.info(f"{nb} fichiers renommés")
    
    if args.doublons:
        logger.info("Suppression des doublons...")
        nb = supprimer_doublons(args.dossier, args.simulation, args.limite)
        logger.info(f"{nb} doublons supprimés")
    
    logger.info("Organisation terminée!")