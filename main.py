# main.py
"""
Point d'entrée principal — QTRobot Interaction (3 Scénarios)

Usage:
    python main.py --scenario 1           # Mode local (caméra locale, Piper local, terminal pour veste)
    python main.py --scenario 2 --QT      # Mode QT (caméra ROS, audio ROS, veste Raspberry)
"""
import sys
import os
import argparse
import threading
import time
import cv2
from PIL import Image

from src.ui import UI
from src.camera_manager import CameraManager
from src.vest_manager import VestManager
from src.audio_manager import AudioManager
from src.scenario_engine import ScenarioEngine, ScenarioState
from src.data_acquisition.emotions import EmotionAnalyzer
from src.data_acquisition.mtcnn_function import detect_faces
from src.utils import redimensionner_image_pour_ui
from src.face_tracking import FaceTracker


def parse_args():
    parser = argparse.ArgumentParser(description="QTRobot — Scénarios d'interaction")
    parser.add_argument("--scenario", type=int, required=True, choices=[1, 2, 3],
                        help="Numéro du scénario (1, 2 ou 3)")
    parser.add_argument("--QT", action="store_true",
                        help="Active le mode QT Robot (ROS + Raspberry Pi)")
    parser.add_argument("--follow", action="store_true",
                        help="Active le suivi du visage du robot (nécessite --QT)")
    args = parser.parse_args()
    
    if args.follow and not args.QT:
        parser.error("L'argument --follow nécessite obligatoirement l'argument --QT pour fonctionner.")
        
    return args


def main():
    args = parse_args()
    qt_mode = args.QT
    scenario_id = args.scenario

    print("=" * 60)
    print(f"  QTRobot — Scénario {scenario_id}")
    print(f"  Mode : {'QT (ROS + Raspberry)' if qt_mode else 'Local'}")
    print("=" * 60)

    # ─── Initialisation ROS Client (si mode QT) ───
    ros_client = None
    raspberry = None

    if qt_mode:
        from src.ROS.remote_client import RemoteRosClient
        from src.touch.robot_net import RaspberryManager

        print("\n🤖 Initialisation ROS...")
        ros_client = RemoteRosClient()
        ros_client.wakeup()

        # Config Raspberry Pi pour la veste
        print("\n🧤 Initialisation Raspberry Pi (veste)...")
        raspberry = RaspberryManager(
            ip="192.168.100.3",        # IP du Raspberry
            user="qt",
            password="qtrobot",
            script_path="/home/qt/Documents/inferenceQT0526.py",
            venv_path="/home/qt/Documents/.venv/bin/activate",
            port=65432
        )

    # ─── Initialisation des managers ───
    camera = CameraManager(qt_mode=qt_mode, ros_client=ros_client)
    vest = VestManager(qt_mode=qt_mode, raspberry_manager=raspberry)
    audio = AudioManager(
        qt_mode=qt_mode,
        ros_client=ros_client,
        piper_model_path="models/tts_piper/fr_FR-upmc-medium.onnx"
    )

    # ─── Détection d'émotions ───
    emotion_analyzer = EmotionAnalyzer(confidence_threshold=0.5)

    # ─── UI ───
    app = UI(scenario_id=scenario_id)

    # Callback pour l'UI (thread-safe via after())
    def ui_status_callback(text):
        app.after(0, app.update_status, text)
        app.after(0, app.add_log, text)

    # ─── Scénario ───
    engine = ScenarioEngine(
        scenario_id=scenario_id,
        audio_manager=audio,
        vest_manager=vest,
        ui_callback=ui_status_callback
    )

    # ─── Suivi de visage ───
    tracker = None
    if args.follow:
        tracker = FaceTracker(audio)
        tracker.start()
        print("👀 [TRACKING] Suivi de visage activé.")

    # ─── Démarrage veste ───
    vest.start()

    # ─── Variable de contrôle ───
    stop_event = threading.Event()

    # ─── Thread : Scénario ───
    def scenario_thread():
        # Petit délai pour laisser la caméra et l'UI démarrer
        time.sleep(2)
        engine.run()

    scenario_t = threading.Thread(target=scenario_thread, daemon=True)
    scenario_t.start()

    # ─── Boucle principale (UI + Vidéo + Détection émotion) ───
    frame_counter = 0
    DETECTION_SKIP = 3  # Détection MTCNN toutes les N frames (optimisation)

    # Persistance du dernier résultat de détection entre les frames
    last_box = None
    last_raw = None
    last_smoothed = None

    def video_loop():
        nonlocal frame_counter, last_box, last_raw, last_smoothed

        if stop_event.is_set():
            return

        frame = camera.get_frame()

        if frame is not None:
            frame_counter += 1

            # Détection visage + émotion (toutes les N frames seulement)
            if frame_counter % DETECTION_SKIP == 0:
                try:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    faces = detect_faces(frame_rgb)

                    if faces:
                        smoothed, raw, box = emotion_analyzer.process_emotion(frame_rgb, faces)

                        # Sauvegarder les résultats pour les frames intermédiaires
                        last_box = box
                        last_raw = raw
                        last_smoothed = smoothed

                        # Envoyer au scénario seulement si on a une émotion valide
                        if smoothed:
                            engine.update_emotion(smoothed)
                            app.after(0, app.update_emotion, f"{smoothed} (raw: {raw})")
                    else:
                        # Pas de visage détecté → on efface les infos
                        last_box = None
                        last_raw = None
                        last_smoothed = None
                        app.after(0, app.update_emotion, "Aucun visage détecté")

                except Exception as e:
                    print(f"⚠️ Erreur détection : {e}")

            # Gestion du Face Tracking
            if tracker:
                # Si le robot fait autre chose (réaction, conclusion, début), on arrête le suivi
                if engine.state in [ScenarioState.DEBUT, ScenarioState.REACTION, ScenarioState.CONCLUSION]:
                    tracker.stop()
                else:
                    tracker.start()
                
                if frame_counter % DETECTION_SKIP == 0 and last_box:
                    h, w, _ = frame.shape
                    tracker.update(last_box, frame_w=w, frame_h=h)

            # Dessiner le rectangle sur CHAQUE frame (pas seulement les frames de détection)
            if last_box:
                x1, y1, x2, y2 = last_box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                if last_raw:
                    label = f"{last_raw}"
                    if last_smoothed and last_smoothed != last_raw:
                        label += f" -> {last_smoothed}"
                    cv2.putText(frame, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Affichage dans l'UI
            try:
                resized = redimensionner_image_pour_ui(frame, target_width=640)
                if resized is not None:
                    pil_img = Image.fromarray(resized)
                    app.mettre_a_jour_image(pil_img)
            except Exception as e:
                print(f"⚠️ Erreur UI image : {e}")

        # Reprogram la boucle (~30 fps)
        app.after(33, video_loop)

    # Lancer la boucle vidéo
    app.after(100, video_loop)

    # ─── Lancement UI (bloquant) ───
    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n🛑 Arrêt en cours...")
        stop_event.set()
        engine.stop()
        vest.stop()
        camera.release()
        print("👋 Terminé.")


if __name__ == "__main__":
    main()
