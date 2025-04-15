# 🛣️ Roadmap de développement - Organisateur de fichiers MIDEESSI

**Date de création :** 14/04/2025
**Auteur :** Medessi Coovi

---

## 🎯 Objectif du logiciel
Créer un logiciel professionnel capable d'organiser automatiquement les fichiers d'un utilisateur, tout en s'adaptant à ses habitudes et en facilitant la gestion de son espace de stockage.

---

## ✅ Étape 1 - Développement des fonctionnalités de base

### 🔹 Organisation
- [x] Tri par extensions (images, vidéos, documents...)
- [x] Création automatique des dossiers cibles
- [ ] Historique des actions de tri
- [ ] Annulation (Undo) et rétablissement (Redo)
- [ ] Tri personnalisé par type de fichier

### 🔹 Fichiers en double
- [x] Détection des doublons par hash
- [ ] Suppression intelligente (envoyer à la corbeille)

### 🔹 Statistiques
- [x] Afficher le nombre de fichiers par extension
- [x] Afficher les fichiers les plus volumineux
- [ ] Exporter les statistiques en PDF ou CSV

### 🔹 Habitudes d’utilisateur
- [ ] Apprentissage des préférences utilisateur
- [ ] Suggestions de tri personnalisées

### 🔹 Surveillance temps réel
- [x] Watcher de dossier automatique (Watchdog)
- [ ] L’utilisateur choisit les dossiers à surveiller

---

## 💻 Étape 2 - Interface graphique (PyQt6)

- [x] Interface de base avec boutons et liste
- [ ] Interface fluide et épurée (type Mac/Apple)
- [ ] Ajout d’une page de configuration (paramètres)
- [ ] Drag & Drop des fichiers
- [ ] Affichage dynamique des stats

---

## 📦 Étape 3 - Emballage & distribution

- [ ] Création d’un exécutable Windows (.exe)
- [ ] Création d’un installeur (Inno Setup)
- [ ] Ajout d’un logo et icônes
- [ ] Fichier README et manuel PDF

---

## 🌐 Étape 4 - Mise à jour automatique

- [ ] Vérification automatique d’une nouvelle version
- [ ] Téléchargement & installation automatique
- [ ] Affichage du changelog

---

## 🧪 Étape 5 - Tests & retour utilisateur

- [ ] Tests sur d’autres machines
- [ ] Collecte de feedback (via formulaire en ligne)
- [ ] Améliorations basées sur les retours

---

## 🔁 Étape 6 - Lancement officiel

- [ ] Présentation à des particuliers
- [ ] Proposition à des petites entreprises
- [ ] Promotion via la startup MIDEESSI

---

## 📁 Structure du projet

```
organisateur_fichiers/
├── main.py
├── organizer/
│   ├── organizer.py
│   ├── stats.py
│   ├── watcher.py
│   ├── user_pattern.py
├── ui/
│   └── ui_main.py
├── logger.py
├── roadmap.md
├── requirements.txt
└── README.md
```

---

📌 *Ce fichier est mis à jour tout au long de l'évolution du projet.*
