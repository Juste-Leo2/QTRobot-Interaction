#!/usr/bin/env python3
"""
download_model.py - Script de vérification et téléchargement des modèles IA
Supporte Windows et Linux. Télécharge uniquement Vosk (STT) et Piper (TTS).
Utilise urllib + RETRY pour pallier les erreurs de connexion reset sur Windows.
"""

import os
import sys
import yaml
import tempfile
import zipfile
import shutil
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple

# --- FIX WINDOWS ENCODING ---
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Configuration
CONFIG_PATH = "config/config.yaml"
PROJECT_ROOT = Path(__file__).parent.parent

def load_config() -> Dict:
    """Charge la configuration depuis config.yaml"""
    config_file = PROJECT_ROOT / CONFIG_PATH
    if not config_file.exists():
        print(f"❌ Erreur: Fichier de configuration non trouvé: {config_file}")
        sys.exit(1)
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def download_file(url: str, destination: Path, desc: str = "", retries: int = 5) -> bool:
    """
    Télécharge un fichier avec urllib.request (Python Natif)
    Inclus une logique de RETRY automatique pour gérer les micro-coupures (WinError 10054).
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for attempt in range(retries):
        try:
            print(f"📥 Téléchargement {desc} (Tentative {attempt + 1}/{retries})...")
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as response, open(destination, 'wb') as out_file:
                total_size_header = response.info().get('Content-Length')
                total_size = int(total_size_header) if total_size_header else -1
                downloaded = 0
                block_size = 1024 * 32 # 32KB blocks
                
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    out_file.write(buffer)
                    
                    if total_size > 0:
                        percent = int(downloaded * 100 // total_size)
                        bar_len = 30
                        filled_len = int(bar_len * downloaded // total_size)
                        bar = '#' * filled_len + '-' * (bar_len - filled_len)
                        sys.stdout.write(f"\r   [{bar}] {percent}% ({downloaded / (1024*1024):.1f} MB)")
                        sys.stdout.flush()
                print() # Fin de ligne si succès
            return True
        except Exception as e:
            if attempt < retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"\n⚠️  Problème de connexion ({e}). Nouvel essai dans {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"\n❌ Échec final pour {desc} après {retries} tentatives : {e}")
                return False

def extract_archive(archive_path: Path, extract_to: Path, expected_item: str, is_directory: bool) -> bool:
    """
    Extrait une archive zip.
    """
    print(f"📦 Extraction de {archive_path.name}...")
    
    try:
        if archive_path.suffix == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)

        # Vérification finale
        full_path = extract_to / expected_item
        if is_directory:
            if full_path.exists() and full_path.is_dir(): return True
        else:
            if full_path.exists() and full_path.is_file(): return True
            found = list(extract_to.rglob(expected_item))
            if found:
                shutil.move(str(found[0]), str(full_path))
                return True
        
        print(f"❌ Échec extraction : {expected_item} non trouvé. Contenu extrait : {[p.name for p in extract_to.iterdir()]}")
        return False

    except Exception as e:
        print(f"❌ Erreur extraction: {e}")
        return False

def main():
    print("=" * 70)
    print(f"VÉRIFICATION ET TÉLÉCHARGEMENT DES MODÈLES IA [{sys.platform.upper()}]")
    print("=" * 70)

    config = load_config()

    models_to_check: List[Tuple[str, str, str, str, bool]] = [
        (config['models']['stt_vosk']['fr'], "https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip", "zip", "VOSK FR", True),
        (config['models']['stt_vosk']['en'], "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip", "zip", "VOSK EN", True),
        (config['models']['tts_piper']['fr_upmc'], "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx?download=true", "file", "Piper TTS Model FR", False),
        (str(config['models']['tts_piper']['fr_upmc']) + ".json", "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx.json?download=true", "file", "Piper TTS Config FR", False),
        (config['models']['tts_piper']['en_amy'], "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx?download=true", "file", "Piper TTS Model EN", False),
        (str(config['models']['tts_piper']['en_amy']) + ".json", "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json?download=true", "file", "Piper TTS Config EN", False),
    ]

    print(f"--- Vérification des {len(models_to_check)} fichiers requis ---")
    
    for model_path, url, dl_type, desc, is_dir in models_to_check:
        full_dest_path = PROJECT_ROOT / model_path
        
        if full_dest_path.exists():
            print(f"✅ {desc} présent.")
            continue
            
        time.sleep(1.0)  # Délai augmenté pour éviter le flood
        temp_dir = tempfile.mkdtemp()
        try:
            if dl_type == "file":
                download_file(url, full_dest_path, desc)
            else:
                archive_name = "temp.zip" 
                archive_dest = Path(temp_dir) / archive_name
                if download_file(url, archive_dest, desc):
                    extract_dir = PROJECT_ROOT / Path(model_path).parent
                    item_to_extract = Path(model_path).name
                    extract_archive(archive_dest, extract_dir, item_to_extract, is_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n🎉 Vérification terminée.")

if __name__ == "__main__":
    main()