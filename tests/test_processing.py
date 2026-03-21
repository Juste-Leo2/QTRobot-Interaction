# tests/test_processing.py

import pytest
import json
import numpy as np
from pathlib import Path
from vosk import Model, KaldiRecognizer

# Imports du code source
from src.data_acquisition.vosk_function import VoskRecognizer
from src.data_acquisition.mtcnn_function import detect_faces
from src.data_acquisition.emotions import EmotionAnalyzer
from src.final_interaction.tts_piper import PiperTTS

# ==========================================
# TESTS VOSK (STT) - Français & Anglais
# ==========================================

def test_vosk_fr_initialization(config):
    """Test d'initialisation du modèle Vosk Français."""
    model_path = Path(config['models']['stt_vosk']['fr'])
    if not model_path.exists():
        pytest.skip("Modèle Vosk FR absent")
    try:
        VoskRecognizer(models_dict={'fr': str(model_path)})
    except Exception as e:
        pytest.fail(f"Init Vosk FR échouée: {e}")

def test_vosk_en_initialization(config):
    """Test d'initialisation du modèle Vosk Anglais."""
    model_path = Path(config['models']['stt_vosk']['en'])
    if not model_path.exists():
        pytest.skip("Modèle Vosk EN absent")
    try:
        VoskRecognizer(models_dict={'en': str(model_path)})
    except Exception as e:
        pytest.fail(f"Init Vosk EN échouée: {e}")

def test_vosk_fr_recognize_silence(config):
    """Test de reconnaissance vocale sur audio silencieux (FR)."""
    model_path = Path(config['models']['stt_vosk']['fr'])
    if not model_path.exists():
        pytest.skip("Modèle Vosk FR absent")
    
    # Utilisation directe de Vosk pour tester la reconnaissance
    model = Model(str(model_path))
    rec = KaldiRecognizer(model, 16000)
    
    # Audio silencieux : 1 seconde de silence à 16kHz, 16-bit mono
    silence = np.zeros(16000, dtype=np.int16)
    rec.AcceptWaveform(silence.tobytes())
    result = json.loads(rec.Result())
    # Le résultat doit contenir la clé 'text' (vide pour du silence)
    assert "text" in result
    assert isinstance(result["text"], str)

def test_vosk_en_recognize_silence(config):
    """Test de reconnaissance vocale sur audio silencieux (EN)."""
    model_path = Path(config['models']['stt_vosk']['en'])
    if not model_path.exists():
        pytest.skip("Modèle Vosk EN absent")
    
    model = Model(str(model_path))
    rec = KaldiRecognizer(model, 16000)
    
    silence = np.zeros(16000, dtype=np.int16)
    rec.AcceptWaveform(silence.tobytes())
    result = json.loads(rec.Result())
    assert "text" in result
    assert isinstance(result["text"], str)

# ==========================================
# TESTS PIPER (TTS) - Français & Anglais
# ==========================================

def test_piper_fr_synthesis(config, setup_output_dir):
    """Test de synthèse vocale Piper en Français."""
    model_path = Path(config['models']['tts_piper']['fr_upmc'])
    if not model_path.exists():
        pytest.skip("Modèle Piper FR absent")
    
    out = Path(setup_output_dir) / "test_fr.wav"
    try:
        tts = PiperTTS(model_path=str(model_path))
        tts.synthesize("Bonjour, ceci est un test.", str(out), speaker_id=0)
        assert out.exists(), "Fichier WAV FR non créé"
        assert out.stat().st_size > 0, "Fichier WAV FR vide"
    except Exception as e:
        pytest.fail(f"TTS FR échouée: {e}")

def test_piper_en_synthesis(config, setup_output_dir):
    """Test de synthèse vocale Piper en Anglais."""
    model_path = Path(config['models']['tts_piper']['en_amy'])
    if not model_path.exists():
        pytest.skip("Modèle Piper EN absent")
    
    out = Path(setup_output_dir) / "test_en.wav"
    try:
        tts = PiperTTS(model_path=str(model_path))
        tts.synthesize("Hello, this is a test.", str(out), speaker_id=0)
        assert out.exists(), "Fichier WAV EN non créé"
        assert out.stat().st_size > 0, "Fichier WAV EN vide"
    except Exception as e:
        pytest.fail(f"TTS EN échouée: {e}")

# ==========================================
# TESTS MTCNN (Détection de visages)
# ==========================================

def test_mtcnn_no_face_on_blank_image():
    """MTCNN ne doit détecter aucun visage sur une image blanche."""
    blank_image = np.ones((480, 640, 3), dtype=np.uint8) * 255  # Image blanche
    faces = detect_faces(blank_image)
    assert isinstance(faces, list)
    assert len(faces) == 0, f"MTCNN a détecté {len(faces)} visage(s) sur une image blanche"

def test_mtcnn_no_face_on_black_image():
    """MTCNN ne doit détecter aucun visage sur une image noire."""
    black_image = np.zeros((480, 640, 3), dtype=np.uint8)  # Image noire
    faces = detect_faces(black_image)
    assert isinstance(faces, list)
    assert len(faces) == 0, f"MTCNN a détecté {len(faces)} visage(s) sur une image noire"

def test_mtcnn_handles_empty_input():
    """MTCNN doit retourner une liste vide sur une image vide."""
    empty_image = np.zeros((0, 0, 3), dtype=np.uint8)
    faces = detect_faces(empty_image)
    assert isinstance(faces, list)
    assert len(faces) == 0

# ==========================================
# TESTS HSEMOTION (Reconnaissance d'émotions)
# ==========================================

def test_hsemotion_initialization():
    """Test d'initialisation de l'analyseur d'émotions HSEmotion."""
    try:
        analyzer = EmotionAnalyzer(device="cpu", window_size=5, confidence_threshold=0.3)
        assert analyzer.fer is not None, "Le modèle EmotiEffLib n'a pas été chargé"
    except Exception as e:
        pytest.fail(f"Init HSEmotion échouée: {e}")

def test_hsemotion_prediction_no_face():
    """HSEmotion doit retourner None quand aucun visage n'est fourni."""
    analyzer = EmotionAnalyzer(device="cpu", window_size=5)
    result = analyzer.process_emotion(
        frame_rgb=np.zeros((480, 640, 3), dtype=np.uint8),
        faces_det=[]  # Pas de visages
    )
    smoothed, raw, box = result
    assert smoothed is None
    assert raw is None
    assert box is None

def test_hsemotion_prediction_with_fake_face():
    """
    HSEmotion doit pouvoir prédire une émotion sur un faux visage (image colorée).
    Le résultat n'a pas besoin d'être pertinent, mais la logique doit fonctionner.
    """
    analyzer = EmotionAnalyzer(device="cpu", window_size=5, confidence_threshold=0.0)
    
    # Image colorée uniforme (pas un vrai visage, mais on teste la logique)
    fake_frame = np.full((480, 640, 3), fill_value=128, dtype=np.uint8)
    
    # Simuler une détection MTCNN avec un faux visage
    fake_faces = [{
        'box': [100, 100, 200, 200],  # x, y, w, h
        'confidence': 0.99,
        'keypoints': {}
    }]
    
    smoothed, raw, box = analyzer.process_emotion(fake_frame, fake_faces)
    
    # La prédiction doit retourner quelque chose (même si pas pertinent)
    assert raw is not None, "La prédiction brute ne doit pas être None"
    assert isinstance(raw, str), f"L'émotion brute doit être une chaîne, reçu: {type(raw)}"
    assert box is not None, "La bounding box ne doit pas être None"