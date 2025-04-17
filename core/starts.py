# -*- coding: utf-8 -*-

# Ce script génère des statistiques sur l'utilisation du disque dur.
# Il parcourt les fichiers d'un répertoire donné et enregistre des informations sur les types de fichiers,
# leur taille, et les fichiers les plus volumineux.
# Auteur : COOVI Meessi
import os
from collections import defaultdict
from humanize import naturalsize
from logger import logger  # Assure-toi que logger.py est bien configuré

def generer_statistiques(racine="C:\\"):
    extensions = defaultdict(int)
    tailles = defaultdict(int)
    fichiers_volumineux = []

    total_fichiers = 0
    total_taille = 0

    # Dossiers à ignorer pour éviter les problèmes d'accès
    exclusions = ['C:\\Windows', 'C:\\Program Files', 'C:\\Program Files (x86)', 'C:\\$Recycle.Bin']

    logger.info(f"🔍 Début de l’analyse du disque à partir de : {racine}")

    for dossier, _, fichiers in os.walk(racine):
        if any(dossier.startswith(e) for e in exclusions):
            logger.debug(f"Dossier ignoré : {dossier}")
            continue

        for fichier in fichiers:
            try:
                chemin = os.path.join(dossier, fichier)
                taille = os.path.getsize(chemin)
                ext = os.path.splitext(fichier)[1].lower()

                extensions[ext] += 1
                tailles[ext] += taille
                total_fichiers += 1
                total_taille += taille

                fichiers_volumineux.append((chemin, taille))
            except Exception as e:
                logger.warning(f"Erreur avec le fichier : {os.path.join(dossier, fichier)} — {e}")
                continue

    fichiers_volumineux = sorted(fichiers_volumineux, key=lambda x: x[1], reverse=True)[:10]

    logger.info("✅ Statistiques générées avec succès.")
    print(naturalsize(os.path.getsize(r"C:\\")))

    print("\n===== 📊 STATISTIQUES DU DISQUE =====")
    print(f"📁 Total de fichiers : {total_fichiers}")
    print(f"💾 Espace total utilisé : {naturalsize(total_taille)}")

    print("\n🔥 Top 10 fichiers les plus volumineux :")
    for f, t in fichiers_volumineux:
        print(f"- {f} : {naturalsize(t)}")

    print("\n📂 Types de fichiers les plus fréquents :")
    for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:10]:
        taille = naturalsize(tailles[ext])
        print(f"{ext or '[Aucun]'} : {count} fichiers — {taille}")

if __name__ == "__main__":
    generer_statistiques(r"C:\Users\Medessi Cvi\Desktop\Livre")