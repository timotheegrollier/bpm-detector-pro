# Guide de Build - BPM Detector Pro

Ce projet utilise **PyInstaller** pour créer des exécutables autonomes.

## 🚀 Build Optimisé (Recommandé)

Le build optimisé produit un exécutable **~50 MB** au lieu de 150 MB, avec un démarrage **3-5x plus rapide**.

### Windows - Build Optimisé
```powershell
# Depuis le dossier scripts/
.\build_windows.ps1

# La commande télécharge automatiquement UPX pour la compression
# Output: dist\BPM-Detector-Pro.exe (~50 MB)
```

### Linux - Build Optimisé
```bash
pip install pyinstaller
pyinstaller bpm-detector-optimized.spec --clean

# Output: dist/BPM-Detector-Pro (~45 MB)
```

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
# Build minimal (léger)
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

### Build trop lent
- Utilisez `--onedir` au lieu de `--onefile` (plus rapide à builder, mais dossier au lieu de .exe unique)

### L'app démarre lentement sur Windows
- Antivirus qui scanne le .exe → Ajoutez une exception
- Premier démarrage (cache) → Le 2ème lancement sera plus rapide
