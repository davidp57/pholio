# Changelog — Pholio 📸

Toutes les modifications notables de ce projet sont documentées ici.  
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/)  
Versionnage : [Semantic Versioning](https://semver.org/)

---

## [Non publié]

---

## [1.1.0] — 2026-05-18

### Ajouté

- **Bas de page** (PHO-070) : texte de bas de page configurable rendu en bas à droite de chaque page du PDF (champ « Bas de page » dans la barre latérale) ; aperçu en temps réel dans le canvas
- **Légendes** (PHO-071) : bouton ✏️ sur chaque photo pour saisir une légende ; affichée en superposition dans le canvas et rendue comme bande sombre en bas de la photo dans le PDF ; persistée dans la session
- **Panneau filmstrip** (PHO-072) : panneau vertical redimensionnable sur la droite du canvas affichant toutes les photos actives ; drag & drop pour réorganiser l'ordre ; bouton de suppression par photo ; bascule automatique en mode « Manuel »
- **Support HEIC/HEIF** (PHO-073) : ouverture des fichiers `.heic` et `.heif` via `pillow-heif` lorsque la bibliothèque est installée
- **Résolution PDF** : sélecteur DPI dans la barre latérale (72 / 100 / 150 / 200 / **300**) ; valeur par défaut 300 dpi ; persistée en session
- **Export couverture JPG** : option pour exporter la photo de couverture en JPG en même temps que le PDF (avec correction d'orientation EXIF)

---

## [1.0.1] — 2026-05-18

### Corrigé

- Crash de l'exe au chargement des photos (`ValueError: is not in the subpath of`) — chemin de miniature relatif non résolu avant `relative_to()` dans `main.py`

---

## [1.0.0] — 2026-05-17

Première version stable. L'application est complète et utilisable de bout en bout.

### Ajouté

**Infrastructure**
- Projet Poetry (FastAPI, Pillow, fpdf2, pytest, ruff, mypy)
- Structure gitflow (main / develop / feature / fix / release)
- CI GitHub Actions : lint Python, vérification JS, build exe Windows
- Script `pholio-build` pour générer un exécutable autonome (PyInstaller, onedir ou onefile)
- Affichage de la version (`v1.0.0`) dans la barre latérale
- Message de démarrage console avec URL et raccourci quitter

**Backend**
- Scan automatique des dossiers `images/` : détection JPEG, PNG, WEBP, TIFF, BMP
- Génération et cache de miniatures WEBP (400 px max, correction EXIF)
- Persistance de session JSON dans `sessions/{album}.json`
- Moteur de mise en page : algorithmes **grille**, **mosaïque** (justified), **colonnes** (masonry)
- Mécanisme de verrouillage de position (keep / first / unlock)
- Surcharge de taille par photo (`SizeOverride`) indépendante du verrouillage de position
- Page de couverture : photo choisie + titre (pleine page, page 0)
- Export PDF haute résolution (fpdf2, DPI configurable, correction orientation EXIF, crop aspect ratio)
- Support multi-format : A4, A3, carré 30/20 cm, Letter, format personnalisé

**Interface**
- Sélection d'album, configuration complète (format, layout, marges, espacement, ordre)
- Aperçu canvas interactif : drag-and-drop et redimensionnement (Interact.js, vendorisé)
- Icône cadenas par photo, déverrouillage au clic
- Modal de re-layout pour les photos verrouillées (conserver / remettre en premier / tout déverrouiller)
- Sélection multiple de photos (Ctrl+clic) + redimensionnement en lot
- Zoom canvas (curseur, boutons +/−/reset, Ctrl+molette) de 40 % à 200 %
- Tri : nom de fichier, date EXIF, manuel (glisser-déposer dans la liste)
- Sauvegarde de session et export PDF depuis l'interface
- Panneau couverture : sélectionner une photo, saisir un titre

### Sécurité
- Validation des chemins de miniatures contre la traversée de répertoire
- Validation du nom d'album dans l'export PDF (résolution sous `IMAGES_DIR`)
- Validation des `photo_id` dans `pdf_export.py` (résolution sous le dossier album)
- Interact.js vendorisé localement (pas de CDN, fonctionnement hors-ligne garanti)

### Tests
- 50 tests (pytest) : moteur de layout, export PDF, API, utilitaires image, persistance session
- Couverture layout ≥ 90 %, API ≥ 80 %

---

## [0.1.0] — 2026-05-17

### Ajouté
- Initialisation du projet (Poetry, FastAPI, Pillow, fpdf2)
- Structure de base : src/pholio, tests, doc, static
- Configuration gitflow (main, develop, feature/*, fix/*)
- Configuration qualité : ruff, mypy, pytest
