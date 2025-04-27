# Configuration
# Ce fichier contient des configurations et des constantes utilisées dans l'application.

#
# Importation des modules nécessaires
TYPES_FICHIERS = {
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".odt"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
    "Vidéos": [".mp4", ".avi", ".mov", ".mkv"],
    "Musique": [".mp3", ".wav", ".aac", ".flac"],
    "Archives": [".zip", ".rar", ".tar", ".gz", ".7z"],
    "Exécutables": [".exe", ".msi", ".bat", ".sh", ".apk"],
    "Feuilles de calcul": [".xls", ".xlsx", ".csv", ".ods"],
    "Présentations": [".ppt", ".pptx", ".odp"],
    "Code": [".py", ".java", ".c", ".cpp", ".js", ".html", ".css"],
}


RETENTION_DAYS = 30  # Nombre de jours pour conserver l'historique
