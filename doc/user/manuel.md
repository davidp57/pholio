# Manuel utilisateur — Pholio 📸

## Présentation

Pholio est une application qui génère des albums photo en PDF à partir de dossiers d'images. Elle tourne localement sur votre ordinateur : pas de connexion internet, pas de compte à créer.

---

## Démarrage

### Prérequis

- Python 3.11 ou supérieur
- Poetry installé (`pip install poetry`)

### Installation

```powershell
cd d:\dev\_misc\photos
poetry install
```

### Lancer l'application

```powershell
poetry run pholio
```

Le navigateur s'ouvre automatiquement sur `http://localhost:8000`.

Options disponibles :

```powershell
poetry run pholio --folder "images/Voyage à Prague"  # ouvrir directement un album
poetry run pholio --port 8080                        # changer le port
```

---

## Interface

L'interface comporte trois zones :

1. **Panneau gauche** — Configuration (album, format de page, type de mise en page, ordre des photos)
2. **Zone centrale** — Aperçu des pages (canvas interactif)
3. **Barre d'actions** — Sauvegarder, Exporter PDF

---

## Choisir un album

Au démarrage, sélectionnez l'un des dossiers détectés dans `images/`. Chaque dossier correspond à un album.

---

## Configurer la mise en page

### Format de page

| Option | Dimensions |
|---|---|
| A4 paysage (défaut) | 297 × 210 mm |
| A4 portrait | 210 × 297 mm |
| A3 paysage | 420 × 297 mm |
| A3 portrait | 297 × 420 mm |
| Carré 30 cm | 300 × 300 mm |
| Carré 20 cm | 200 × 200 mm |
| Letter paysage | 279 × 216 mm |
| Letter portrait | 216 × 279 mm |
| Personnalisé | Largeur × hauteur au choix |

### Type de mise en page

- **Grille** : toutes les photos à la même taille, disposées en N colonnes régulières
- **Mosaïque** : chaque rangée remplit la largeur complète, les photos conservent leurs proportions
- **Colonnes** : style Pinterest — chaque photo est placée dans la colonne la plus courte

Changer le type de mise en page relance le calcul automatiquement.

### Ordre des photos

- **Nom de fichier** : ordre alphabétique/numérique
- **Date EXIF** : date de prise de vue lue dans les métadonnées
- **Manuel** : faites glisser les photos dans le panneau de liste pour les réorganiser

---

## Modifier manuellement une photo

Dans l'aperçu, vous pouvez :

- **Déplacer** une photo : cliquez et faites-la glisser vers la position souhaitée
- **Redimensionner** une photo : tirez les poignées aux coins

Après une modification manuelle, la photo est **verrouillée** (icône 🔒) : elle reste à sa position même si vous relancez la mise en page.

### Déverrouiller une photo

Cliquez sur l'icône 🔒 à côté de la photo pour la déverrouiller. Elle reprend sa place dans la mise en page automatique.

---

## Relancer la mise en page

Quand vous changez le type de layout, l'ordre, ou le format de page, Pholio relance le calcul. Si des photos sont verrouillées, une fenêtre vous demande :

- **Conserver les photos verrouillées à leur place** *(recommandé)* — les autres se replacent autour
- **Remettre les photos verrouillées en premier** — elles sont replacées en tête de liste, dans l'ordre auto
- **Déverrouiller toutes les photos** — recalcul complet depuis zéro

---

## Sauvegarder le travail

Cliquez sur **Sauvegarder** pour enregistrer l'état actuel (config, ordre, verrous, positions). La session est stockée dans `sessions/{nom-album}.json`.

Au prochain lancement de Pholio avec le même album, la session est automatiquement restaurée.

---

## Exporter en PDF

Cliquez sur **Exporter PDF** pour générer le fichier. Le PDF est téléchargé par le navigateur. Les photos sont incluses en pleine résolution.

---

## Formats d'image supportés

- JPEG (`.jpg`, `.jpeg`) — principal
- PNG, WEBP, TIFF, BMP — si Pillow peut les ouvrir

---

## Problèmes fréquents

**L'application ne s'ouvre pas**  
Vérifiez que le port 8000 n'est pas déjà utilisé par une autre application. Utilisez `--port 8080` pour changer de port.

**Les photos apparaissent de côté**  
Pholio corrige automatiquement l'orientation EXIF. Si certaines photos restent mal orientées, le fichier source n'a peut-être pas de métadonnée EXIF d'orientation.

**Une session ancienne ne se charge pas**  
Supprimez le fichier `sessions/{nom-album}.json` pour repartir de zéro.
