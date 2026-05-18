# Backlog — Pholio 📸

Tickets de développement. Format : `PHO-NNN`. Priorités : P1 (critique), P2 (important), P3 (nice-to-have).  
Les estimations représentent le **temps Copilot** (temps d'implémentation AI). Formule : temps brut × 1.15, arrondi à 5 min.

---

## Calibration estimations

| Lot | Estimé Copilot | Réel Copilot | Ratio | Commentaire |
|---|---|---|---|---|
| INIT (v0.1→v1.0) | — | ~4h | — | Lot unique : scaffold + core + layout + UI + PDF + release |

> Facteur de marge actuel : **1.15** (15%)

---

## Lots actifs

### Lot POST-1.0 — v1.1 🛠️ En cours

Fonctionnalités supplémentaires post-release (tout en un seul PR sur `develop`).

| Ticket | Titre | Priorité | Statut | Estimé | Réel |
|---|---|---|---|---|---|
| PHO-070 | Filigrane sur les pages (texte, bas-droite) | P3 | ✅ Fait | 30 min | — |
| PHO-071 | Légende textuelle sur les photos | P3 | ✅ Fait | 40 min | — |
| PHO-072 | Panneau filmstrip avec réorganisation par drag | P2 | ✅ Fait | 50 min | — |
| PHO-073 | Support HEIC/HEIF via `pillow-heif` | P3 | ✅ Fait | 20 min | — |

Note : Support RAW (CR2, NEF, ARW) non implémenté — nécessite `rawpy`/libraw, incompatible PyInstaller. Créer un ticket séparé PHO-074 si besoin.

---

## Hors lots (tickets isolés)

| Ticket | Titre | Priorité | Statut | Estimé | Réel |
|---|---|---|---|---|---|
| PHO-001 | Initialisation projet (Poetry, gitflow, qualité) | P1 | ✅ Fait | 30 min | — |
| PHO-064 | Hotfix : crash exe — chemin miniature relatif non résolu avant `relative_to()` | P1 | ✅ Fait | 10 min | — |

---

## Lots planifiés

### Lot POST-1.1 — v1.2 📋 Planifié

Améliorations visuelles, mise en page avancée et interactivité.

| Ticket | Titre | Priorité | Statut | Estimé | Réel |
|---|---|---|---|---|---|
| PHO-080 | Couleur de fond des pages (sélecteur, appliqué dans PDF) | P2 | 🔲 À faire | 35 min | — |
| PHO-081 | Couleur de fond différente sur la page de garde | P3 | 🔲 À faire | 20 min | — |
| PHO-082 | Placement libre de la photo de garde (sans recadrage forcé) | P2 | 🔲 À faire | 45 min | — |
| PHO-083 | Icônes filmstrip : lock position, lock taille, choisir comme garde (toujours visibles) | P2 | 🔲 À faire | 40 min | — |
| PHO-084 | Tri filmstrip synchronisé avec l'ordre défini par l'utilisateur | P2 | 🔲 À faire | 30 min | — |
| PHO-085 | Synchronisation scroll filmstrip ↔ document | P3 | 🔲 À faire | 25 min | — |
| PHO-086 | Bloc texte libre (police, couleur, effets, placement drag) | P2 | 🔲 À faire | 90 min | — |

**Total estimé** : 285 min + 15 min gestion = **300 min (5 h)**

---

## Lots livrés

### Lot INIT — v1.0 ✅ Livré (2026-05-17)

Scaffold complet → application fonctionnelle de bout en bout.

<details>
<summary>Détail des tickets</summary>

| Ticket | Titre | Priorité | Statut | Estimé | Réel |
|---|---|---|---|---|---|
| PHO-010 | CLI entry point (argparse, uvicorn, open browser) | P1 | ✅ | 20 min | — |
| PHO-011 | Scan album folder + métadonnées EXIF | P1 | ✅ | 25 min | — |
| PHO-012 | Génération de thumbnails WEBP avec cache | P1 | ✅ | 25 min | — |
| PHO-013 | Config page formats (a4-landscape, etc.) | P1 | ✅ | 15 min | — |
| PHO-014 | Save/load session JSON | P1 | ✅ | 20 min | — |
| PHO-015 | Routes API albums + session | P1 | ✅ | 25 min | — |
| PHO-016 | FastAPI app factory + serve static | P1 | ✅ | 15 min | — |
| PHO-017 | Tests unitaires image_utils + state | P2 | ✅ | 30 min | — |
| PHO-018 | Tests intégration routes API | P2 | ✅ | 25 min | — |
| PHO-020 | Structures de données layout | P1 | ✅ | 20 min | — |
| PHO-021 | Algorithme grid | P1 | ✅ | 35 min | — |
| PHO-022 | Algorithme mosaic | P1 | ✅ | 50 min | — |
| PHO-023 | Algorithme columns | P1 | ✅ | 35 min | — |
| PHO-024 | run_layout() avec relock_behaviour | P1 | ✅ | 25 min | — |
| PHO-025 | Route API layout/compute | P1 | ✅ | 30 min | — |
| PHO-026 | Tests unitaires layout ≥ 90 % couverture | P1 | ✅ | 45 min | — |
| PHO-030 | Structure HTML (sidebar, canvas, toolbar) | P1 | ✅ | 25 min | — |
| PHO-031 | Rendu canvas : pages + miniatures positionnées | P1 | ✅ | 45 min | — |
| PHO-032 | Drag & drop photos (Interact.js) | P1 | ✅ | 40 min | — |
| PHO-033 | Resize photos (poignées Interact.js) | P1 | ✅ | 30 min | — |
| PHO-034 | Lock/unlock par photo (icône cadenas) | P1 | ✅ | 20 min | — |
| PHO-035 | Panneau de tri (filename / date / drag-to-reorder) | P2 | ✅ | 35 min | — |
| PHO-036 | Modal re-layout (keep / first / unlock) | P1 | ✅ | 25 min | — |
| PHO-037 | Sélection album + formulaire config | P1 | ✅ | 30 min | — |
| PHO-038 | Boutons Sauvegarder et Exporter PDF | P1 | ✅ | 20 min | — |
| PHO-040 | pdf_export.py : assemblage fpdf2 depuis LayoutResult | P1 | ✅ | 40 min | — |
| PHO-041 | Correction orientation EXIF dans le PDF | P1 | ✅ | 15 min | — |
| PHO-042 | Route API POST /api/export/pdf | P1 | ✅ | 15 min | — |
| PHO-043 | Tests intégration export PDF | P2 | ✅ | 20 min | — |
| PHO-050 | Page de couverture (photo + titre, pleine page) | P2 | ✅ | 35 min | — |
| PHO-051 | Sélection multiple + redimensionnement en lot | P2 | ✅ | 30 min | — |
| PHO-052 | Surcharge de taille sans verrouillage de position | P2 | ✅ | 25 min | — |
| PHO-053 | Zoom canvas (curseur + Ctrl+molette) | P2 | ✅ | 20 min | — |
| PHO-060 | Script pholio-build (PyInstaller onedir/onefile) | P2 | ✅ | 25 min | — |
| PHO-061 | Affichage version dans l'UI | P3 | ✅ | 10 min | — |
| PHO-062 | CI GitHub Actions (pytest + JS check + build exe) | P2 | ✅ | 20 min | — |
| PHO-063 | Correctifs sécurité (path traversal, CDN) | P1 | ✅ | 25 min | — |

</details>

---

## Lots planifiés

*(Aucun lot planifié pour l’instant)*
