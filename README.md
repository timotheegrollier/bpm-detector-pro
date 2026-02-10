# 🎵 BPM Detector Pro

**Détecteur de BPM haute précision** — Analyse le tempo de n'importe quel fichier audio avec une précision exceptionnelle.

![Version](https://img.shields.io/badge/version-1.1.3-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey)

## ✨ Fonctionnalités

- 🎯 **Détection ultra-précise** : Algorithme hybride ACF/Beats avec snapping intelligent
- 🖥️ **Interface graphique moderne** : GUI native sombre et réactive (Tkinter optimisé)
- 💻 **Interface en ligne de commande** : Pour l'automatisation et les scripts
- 🌐 **Interface web** : Serveur Flask pour une utilisation via navigateur
- 📦 **Binaires portables légers** : ~50 Mo (v1.1 optimisée), aucune installation requise
- 🔊 **Tous formats audio** : MP3, FLAC, WAV, M4A, OGG, AAC, et plus (via FFmpeg intégré)
- 📊 **Analyse de segments** : Visualisation des variations de tempo tout au long du morceau
- ⚡ **Démarrage instantané** : Nouveau moteur "Fast Startup" (chargement < 2s)

## 🚀 Installation Rapide

### Option 1 : Binaire Portable (Recommandé)

Téléchargez le binaire directement depuis les [Releases GitHub](../../releases) :
- **Linux** : `BPM-Detector-Pro` (exécutable directement)
- **Windows** : `BPM-Detector-Pro.exe` (double-cliquez pour lancer)

Aucune installation requise — c'est portable !

### Option 2 : Depuis les Sources

```bash
# Cloner le repo
git clone https://github.com/VOTRE_USER/bpm-detector.git
cd bpm-detector

# Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# ou: .venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt
```

> **Note** : FFmpeg doit être installé sur votre système pour l'utilisation depuis les sources.

## 📖 Utilisation

### Interface Graphique (GUI)

```bash
python bpm_gui.py
# ou lancez directement le binaire : ./BPM-Detector-Pro
```

Une fenêtre s'ouvre avec :
- Bouton pour sélectionner un fichier audio
- Options de configuration (sample rate, durée, etc.)
- Affichage du BPM détecté et confiance
- Graphique des segments de tempo

### Ligne de Commande (CLI)

```bash
python bpm_detect.py fichier_audio.mp3
```

**Options disponibles :**

| Option | Description | Défaut |
|--------|-------------|--------|
| `--start N` | Début de l'analyse (secondes) | 0 |
| `--duration N` | Durée à analyser (secondes) | fichier entier |
| `--sr N` | Sample rate d'analyse | 22050 |
| `--hop-length N` | Précision (plus petit = plus précis mais plus lent) | 96 |
| `--min-bpm N` | BPM minimum | 60 |
| `--max-bpm N` | BPM maximum | 200 |
| `--no-hpss` | Désactive la séparation percussive | off |
| `--no-snap` | Désactive le snapping automatique | off |
| `--json` | Sortie au format JSON | off |
| `--variations` | Affiche les variations de tempo | off |

**Exemples :**

```bash
# Analyse basique
python bpm_detect.py ma_track.mp3

# Analyse de 60 secondes à partir de 30s
python bpm_detect.py ma_track.mp3 --start 30 --duration 60

# Sortie JSON pour scripting
python bpm_detect.py ma_track.mp3 --json

# Haute précision pour tracks rapides (D&B, Jungle)
python bpm_detect.py dnb_track.flac --min-bpm 140 --max-bpm 190 --hop-length 64
```

### Interface Web

```bash
python app.py
```

Ouvrez `http://127.0.0.1:5000` dans votre navigateur.

## 🔧 Build des Binaires

### Linux

```bash
# Place FFmpeg dans packaging/ffmpeg/linux/ffmpeg
./scripts/build_linux.sh
# Résultat : dist/BPM-Detector-Pro
```

### Windows

```powershell
# Place FFmpeg dans packaging/ffmpeg/windows/ffmpeg.exe
.\scripts\build_windows.ps1
# Résultat : dist/BPM-Detector-Pro.exe
```

Consultez [BUILDING.md](BUILDING.md) pour plus de détails.

## 🗂️ Structure du Projet

```
bpm/
├── bpm_gui.py          # Interface graphique (Qt)
├── bpm_detector.py     # Moteur de détection (logique métier)
├── bpm_detect.py       # Interface CLI
├── app.py              # Serveur web Flask
├── requirements.txt    # Dépendances Python
├── bpm-detector.spec   # Configuration PyInstaller
├── scripts/
│   ├── build_linux.sh      # Build Linux
│   ├── build_windows.ps1   # Build Windows
│   └── build_appimage.sh   # Build AppImage
├── packaging/
│   └── ffmpeg/             # Binaires FFmpeg par plateforme
├── static/                 # Assets web (CSS)
└── templates/              # Templates HTML (Flask)
```

## ⚙️ Calibration & Précision

Le moteur de détection utilise :
- **Sample Rate** : 22050 Hz (équilibre précision/performance)
- **Hop Length** : 96 (haute précision temporelle)
- **Snapping** : Arrondi intelligent vers les BPM courants (±0.5 BPM)
- **Analyse** : Jusqu'à 90 secondes à partir du début du drop

Ces paramètres sont optimisés pour la musique électronique (House, Techno, D&B) mais fonctionnent excellemment sur tous les genres.

## 📋 Changelog

### v1.1.3 (Hotfix) 🚑
- 🐛 **Build Fix**: Suppression de l'option obsolète `win_private_assemblies` (PyInstaller 6+)
- 🐛 **Windows**: Inclusion explicite de `python3.dll` pour éviter les erreurs de runtime

### v1.1.2 (Hotfix) 🚑
- 🐛 **Correctif Windows** : Tentative de correction "python3.dll introuvable" (Rollback changements build)

### v1.1.0 ⚡
- 🚀 **Performance** : Démarrage < 2s avec "Fast Startup"
- 📉 **Taille** : Binaire réduit de 150 Mo à ~50 Mo
- 🧠 **Optimisation** : Lazy loading des modules et exclusions agressives

### v1.0.0 (Initial) 🎉
- ✅ Détection BPM avec algorithme hybride ACF/Beats
- ✅ Interface graphique Qt avec thème sombre
- ✅ Interface CLI complète avec options avancées
- ✅ Support de tous les formats audio courants (via FFmpeg)
- ✅ Analyse de segments avec visualisation
- ✅ Snapping intelligent vers BPM entiers

### Build & Packaging
- ✅ Build Linux natif (binaire portable)
- ✅ Build Windows natif (.exe portable)
- ✅ Scripts de build automatisés
- ✅ FFmpeg intégré dans les binaires
- ✅ Processus isolé pour la stabilité

### Qualité
- ✅ Calibration précise testée sur D&B (175 BPM), House (128 BPM), etc.
- ✅ Gestion des erreurs robuste
- ✅ Logs de débogage optionnels

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/amazing-feature`)
3. Commit vos changements (`git commit -m 'Add amazing feature'`)
4. Push la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

---

**Made with ❤️ for DJs and music producers**
