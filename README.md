# Pholio 📸

> Générateur d'albums photo en PDF avec mise en page automatique.  
> Photo album PDF generator with smart automatic layout.

---

## Présentation / Overview

**Pholio** est une application web locale (Python + navigateur) qui permet de composer des albums photo en PDF à partir d'un dossier d'images.

**Pholio** is a local web application (Python + browser) for composing photo albums as PDFs from a folder of images.

**Fonctionnalités / Features:**
- 📐 Mise en page automatique (grille, mosaïque, colonnes) / Automatic layout (grid, mosaic, columns)
- 🔒 Édition manuelle avec verrouillage de position / Manual editing with position lock
- 📷 Page de couverture avec titre / Cover page with title
- 🔍 Zoom canvas (40 %–200 %) / Canvas zoom (40%–200%)
- 💾 Sauvegarde et reprise de session / Save and resume sessions
- 👁 Prévisualisation en temps réel / Real-time preview
- 📄 Export PDF haute résolution / High-resolution PDF export
- 📏 Formats de page configurables (A4, A3, carré, Letter, personnalisé) / Configurable page formats
- 📦 Exécutable autonome Windows (PyInstaller) / Standalone Windows executable (PyInstaller)

---

## Démarrage rapide / Quick Start

```powershell
# Prérequis : Python 3.11+, Poetry
# Prerequisites: Python 3.11+, Poetry

# Installer les dépendances / Install dependencies
poetry install

# Lancer l'application / Start the application
poetry run pholio

# Le navigateur s'ouvre automatiquement sur http://localhost:8000
# The browser opens automatically at http://localhost:8000

# Options / Options
poetry run pholio --port 8080          # changer le port / change port
poetry run pholio --host 0.0.0.0       # exposer sur le réseau local / expose on LAN
```

### Exécutable Windows / Windows Executable

```powershell
# Générer l'exécutable / Build the executable
poetry run pholio-build --onefile      # → dist/pholio.exe

# Lancer / Run
.\dist\pholio.exe
```

---

## Documentation

| Document | Langue / Language | Lien / Link |
|---|---|---|
| Plan technique | EN | [doc/plan.md](doc/plan.md) |
| Manuel utilisateur | FR | [doc/user/manuel.md](doc/user/manuel.md) |
| Documentation développeur | EN | [doc/dev/architecture.md](doc/dev/architecture.md) |
| Roadmap | EN | [doc/roadmap.md](doc/roadmap.md) |
| Backlog | FR | [doc/backlog.md](doc/backlog.md) |
| CHANGELOG | FR | [CHANGELOG.md](CHANGELOG.md) |

---

## Stack

- **Backend** : FastAPI + Pillow + fpdf2
- **Frontend** : HTML/CSS/JS vanilla + Interact.js (vendorisé)
- **Tests** : pytest + ruff + mypy
- **Packaging** : Poetry + PyInstaller

---

## Licence / License

MIT
