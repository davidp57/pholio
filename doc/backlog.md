# Backlog — Pholio 📸

Tickets de développement. Format : `PHO-NNN`. Priorités : P1 (critique), P2 (important), P3 (nice-to-have).  
Les estimations représentent le **temps Copilot** (temps d'implémentation AI). Formule : temps brut × 1.15, arrondi à 5 min.

---

## Calibration estimations

| Lot | Estimé Copilot | Réel Copilot | Ratio | Commentaire |
|---|---|---|---|---|
| — | — | — | — | Pas encore de lots complétés |

> Facteur de marge actuel : **1.15** (15%)

---

## Lots actifs

*(Aucun lot actif pour l'instant — initialisation du projet en cours)*

---

## Hors lots (tickets isolés)

| Ticket | Titre | Priorité | Statut | Estimé | Réel |
|---|---|---|---|---|---|
| PHO-001 | Initialisation projet (Poetry, gitflow, qualité) | P1 | ✅ Fait | 30 min | — |

---

## Lots planifiés

### Lot CORE — v0.2 (À planifier)

Scan d'images, thumbnails, persistance de session, squelette API.  
Estimé : ~2h Copilot + 15 min gestion

<details>
<summary>Détail des tickets</summary>

| Ticket | Titre | Priorité | Estimé | Réel |
|---|---|---|---|---|
| PHO-010 | CLI entry point (argparse, uvicorn, open browser) | P1 | 20 min | — |
| PHO-011 | Scan album folder + métadonnées EXIF | P1 | 25 min | — |
| PHO-012 | Génération de thumbnails WEBP avec cache | P1 | 25 min | — |
| PHO-013 | Config page formats (a4-landscape, etc.) | P1 | 15 min | — |
| PHO-014 | Save/load session JSON | P1 | 20 min | — |
| PHO-015 | Routes API albums + session | P1 | 25 min | — |
| PHO-016 | FastAPI app factory + serve static | P1 | 15 min | — |
| PHO-017 | Tests unitaires image_utils + state | P2 | 30 min | — |
| PHO-018 | Tests intégration routes API | P2 | 25 min | — |

</details>

---

### Lot LAYOUT — v0.3 (À planifier)

Moteur de mise en page : 3 algorithmes + mécanisme de lock.  
Estimé : ~3h Copilot + 15 min gestion

<details>
<summary>Détail des tickets</summary>

| Ticket | Titre | Priorité | Estimé | Réel |
|---|---|---|---|---|
| PHO-020 | Structures de données (PageConfig, PhotoPlacement, LayoutResult) | P1 | 20 min | — |
| PHO-021 | Algorithme grid (grille régulière N colonnes) | P1 | 35 min | — |
| PHO-022 | Algorithme mosaic (justified layout Flickr-style) | P1 | 50 min | — |
| PHO-023 | Algorithme columns (masonry Pinterest-style) | P1 | 35 min | — |
| PHO-024 | run_layout() avec relock_behaviour (keep/first/unlock) | P1 | 25 min | — |
| PHO-025 | Routes API layout (compute, manual-move, resize, toggle-lock) | P1 | 30 min | — |
| PHO-026 | Tests unitaires layout ≥ 90% couverture | P1 | 45 min | — |

</details>

---

### Lot UI — v0.4 (À planifier)

Interface navigateur interactive : canvas, drag/resize, lock, tri.  
Estimé : ~4h Copilot + 15 min gestion

<details>
<summary>Détail des tickets</summary>

| Ticket | Titre | Priorité | Estimé | Réel |
|---|---|---|---|---|
| PHO-030 | Structure HTML (sidebar, canvas, toolbar) | P1 | 25 min | — |
| PHO-031 | Rendu canvas : pages + miniatures positionnées | P1 | 45 min | — |
| PHO-032 | Drag & drop photos (Interact.js) | P1 | 40 min | — |
| PHO-033 | Resize photos (poignées Interact.js) | P1 | 30 min | — |
| PHO-034 | Lock/unlock par photo (icône cadenas) | P1 | 20 min | — |
| PHO-035 | Panneau de tri (filename / date / drag-to-reorder) | P2 | 35 min | — |
| PHO-036 | Modal re-layout (keep / first / unlock) | P1 | 25 min | — |
| PHO-037 | Sélection album + formulaire config | P1 | 30 min | — |
| PHO-038 | Boutons Sauvegarder et Exporter PDF | P1 | 20 min | — |

</details>

---

### Lot PDF — v0.5 (À planifier)

Export PDF haute résolution.  
Estimé : ~1h30 Copilot + 15 min gestion

<details>
<summary>Détail des tickets</summary>

| Ticket | Titre | Priorité | Estimé | Réel |
|---|---|---|---|---|
| PHO-040 | pdf_export.py : assemblage fpdf2 depuis LayoutResult | P1 | 40 min | — |
| PHO-041 | Correction orientation EXIF dans le PDF | P1 | 15 min | — |
| PHO-042 | Route API POST /api/export/pdf | P1 | 15 min | — |
| PHO-043 | Tests intégration export PDF | P2 | 20 min | — |

</details>

---

## Archive des lots

*(Vide pour l'instant)*
