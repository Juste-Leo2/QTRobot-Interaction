# src/audio_manager.py
"""
Abstraction audio et animation robot :
- Mode local : PiperTTS + lecture audio locale (utils.jouer_fichier_audio)
- Mode QT    : PiperTTS + transfert WAV + RemoteRosClient (play, emotion, gesture, head)
"""
import os
from src.final_interaction.tts_piper import PiperTTS
from src.utils import jouer_fichier_audio


class AudioManager:
    def __init__(self, qt_mode=False, ros_client=None, piper_model_path=None):
        self.qt_mode = qt_mode
        self.ros_client = ros_client
        self.tts = None

        # Initialisation Piper TTS
        if piper_model_path and os.path.exists(piper_model_path):
            try:
                self.tts = PiperTTS(piper_model_path)
            except Exception as e:
                print(f"⚠️ [AUDIO] Erreur chargement Piper : {e}")
        else:
            print(f"⚠️ [AUDIO] Modèle Piper introuvable : {piper_model_path}")

        mode_str = "QT (ROS)" if self.qt_mode else "Local"
        print(f"🔊 [AUDIO] Mode {mode_str} initialisé.")

    def speak(self, text, output_path="temp_tts.wav"):
        """Synthétise le texte et le joue."""
        print(f"🗣️  [TTS] \"{text}\"")

        if not self.tts:
            print("⚠️ [AUDIO] Piper non disponible, texte non synthétisé.")
            return

        try:
            self.tts.synthesize(text, output_path)

            if self.qt_mode and self.ros_client:
                # Envoyer le WAV au robot et le jouer
                print(f"🔊 [AUDIO → QT] Envoi et lecture de '{output_path}' sur le robot")
                self.ros_client.play(output_path)
            else:
                # Lecture locale
                print(f"🔊 [AUDIO → LOCAL] Lecture de '{output_path}'")
                jouer_fichier_audio(output_path)

        except Exception as e:
            print(f"⚠️ [AUDIO] Erreur synthèse/lecture : {e}")

    def play_emotion(self, name):
        """Affiche une émotion sur l'écran du robot. Ex: 'QT/happy', 'QT/sad'."""
        print(f"🎭 [ROBOT] Émotion → {name}")
        if self.qt_mode and self.ros_client:
            self.ros_client.emotion(name)

    def play_gesture(self, name):
        """Joue une gestuelle du robot. Ex: 'QT/hi', 'QT/surprise'."""
        print(f"💪 [ROBOT] Gestuelle → {name}")
        if self.qt_mode and self.ros_client:
            self.ros_client.gesture(name)

    def move_head(self, yaw, pitch):
        """Bouge la tête du robot. yaw=gauche/droite, pitch=haut/bas."""
        print(f"🤖 [ROBOT] Tête → yaw={yaw}, pitch={pitch}")
        if self.qt_mode and self.ros_client:
            self.ros_client.move_head(yaw, pitch)

    def show_image(self, image_name):
        """Affiche une image sur l'écran du robot."""
        print(f"🖼️  [ROBOT] Affichage image → {image_name}")
        if self.qt_mode and self.ros_client:
            self.ros_client.show_image(image_name)

    def show_text(self, text):
        """Affiche du texte sur l'écran du robot."""
        print(f"📝 [ROBOT] Affichage texte → \"{text}\"")
        if self.qt_mode and self.ros_client:
            self.ros_client.show_text(text)

    def wakeup(self):
        """Réveille les moteurs du robot (mode QT uniquement)."""
        print("🦾 [ROBOT] Wakeup moteurs")
        if self.qt_mode and self.ros_client:
            self.ros_client.wakeup()
