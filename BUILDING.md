# Guide de Build - BPM Detector Pro

Ce projet utilise **PyInstaller** pour créer des exécutables autonomes.

## 🚀 Build Optimisé (Recommandé)

Le build optimisé produit un exécutable **~50 MB** au lieu de 150 MB, avec un démarrage **3-5x plus rapide**.

### Windows - Build Optimisé
```powershell
# Depuis le dossier scripts/
.\build_windows.ps1

# Output:
# - dist\BPM-Detector-Pro\                  (dossier ONEDIR)
# - dist\BPM-Detector-Pro-Windows-x64.zip   (archive de release)
```
Par défaut, le build Windows utilise **ONEDIR** (exe + `_internal`) pour réduire les erreurs de chargement DLL.
Un ZIP de release est généré automatiquement : `dist\BPM-Detector-Pro-Windows-x64.zip`.

Le script synchronise automatiquement la version de l'app depuis le **dernier tag git** (ex: `v1.1.4`).
Vous pouvez forcer une version : `set APP_VERSION=1.1.4` avant de lancer le build.

### Linux - Build Optimisé
```bash
pip install pyinstaller
pyinstaller bpm-detector-optimized.spec --clean

# Output: dist/BPM-Detector-Pro (~45 MB)
```
Le script `scripts/build_linux.sh` synchronise aussi la version depuis le tag git.

## 📦 Build Classique (Full librosa)

Si vous avez besoin de toutes les fonctionnalités de librosa (précision maximale) :

### Windows
```powershell
$env:USE_LEGACY_BUILD = "1"
.\scripts\build_windows.ps1
```

### Linux
```bash
pyinstaller bpm-detector.spec --clean
```

## ⚙️ Prérequis

1. **FFmpeg** - Placez le binaire dans :
   - Windows: `packaging/ffmpeg/windows/ffmpeg.exe`
   - Linux: `packaging/ffmpeg/linux/ffmpeg`
   
2. **Dépendances Python** :
```bash
# Build minimal (léger, sans SciPy)
pip install -r requirements-minimal.txt pyinstaller

# Build complet (avec librosa)
pip install -r requirements.txt pyinstaller
```

## 🔧 Optimisations Appliquées

| Optimisation | Gain |
|--------------|------|
| Lazy-loading des librairies | Démarrage ~3x plus rapide |
| Exclusions agressives (numba, matplotlib, etc.) | -60 MB |
| Compression UPX | -30% taille |
| Analyse limitée à 45s par défaut | CPU réduit |
| Mode single-thread (pas de fork) | Startup instantané |

## 📊 Comparaison des Builds

| Métrique | Build Classique | Build Optimisé |
|----------|-----------------|----------------|
| Taille | ~150 MB | ~50 MB |
| Temps démarrage (cold) | 8-15s | 2-5s |
| Temps démarrage (warm) | 3-5s | <1s |
| Précision BPM | 100% | ~98% |

## ❓ Dépannage

### "FFmpeg introuvable"
Téléchargez depuis https://ffmpeg.org/download.html et placez le binaire au bon endroit.

### Avertissements Windows Defender / SmartScreen
- Les exécutables **non signés** peuvent déclencher SmartScreen (éditeur inconnu) jusqu'à ce qu'une réputation soit établie.
- Le build Windows publie **ONEDIR** (ZIP) pour limiter les faux positifs et les erreurs de chargement DLL.
- **UPX** peut augmenter les détections heuristiques. Le build Windows **désactive UPX par défaut**.
  - Pour activer la compression : `set USE_UPX=1` puis relancez `.\scripts\build_windows.ps1`
- Pour une distribution professionnelle, **signez** l'exécutable (Authenticode) et ajoutez un horodatage. Un certificat EV accélère la réputation.

### Build trop lent
- Utilisez le build optimisé (`requirements-minimal.txt` + `bpm-detector-optimized.spec`) pour réduire significativement le temps de build.

### L'app démarre lentement sur Windows
- Antivirus qui scanne le .exe → Ajoutez une exception
- Premier démarrage (cache) → Le 2ème lancement sera plus rapide

### "python311.dll / python3.dll introuvable"
- Assurez-vous d'avoir **dézippé tout le dossier** `BPM-Detector-Pro` et de lancer l'exe depuis ce dossier.
- Lancez `START-BPM-Detector-Pro.cmd` (il enlève les blocages "fichier téléchargé" avant de démarrer l'exe).
- Si l'erreur persiste : réparez/installez `Microsoft Visual C++ Redistributable 2015-2022 (x64)`.
- Le script de build vérifie désormais la présence de `pythonXY.dll`, `vcruntime140.dll` et `vcruntime140_1.dll` dans `_internal`, et inclut `msvcp140.dll` en best-effort.
