import requests
import subprocess
import time
import sys
import os
import socket
import numpy as np
import cv2
from src.ROS.Transfer import FileTransfer

BRIDGE_URL = "http://127.0.0.1:5000"
AUDIO_PORT = 5001

class RemoteRosClient:
    def __init__(self):
        self.transfer = FileTransfer()
        # --- NETTOYAGE AUTOMATIQUE DU PORT 5000 ---
        print("🧹 Nettoyage des anciens processus ROS...")
        subprocess.run("fuser -k 5000/tcp", shell=True, stderr=subprocess.DEVNULL)
        time.sleep(1) # Pause pour laisser le temps au système de fermer le port
        
        self._ensure_server_running()
        self.audio_sock = None

    def _ensure_server_running(self):
        # On tente de lancer le serveur
        script_path = os.path.join(os.getcwd(), "src", "ROS", "bridge_server.py")
        print(f"🚀 Démarrage du Pont ROS : {script_path}")
        
        # On lance le serveur en arrière-plan
        subprocess.Popen(["/usr/bin/python3", script_path], stdout=sys.stdout, stderr=sys.stderr)
        
        # On attend qu'il soit prêt
        for i in range(10):
            try:
                requests.get(f"{BRIDGE_URL}/status", timeout=1)
                print("✅ Pont ROS Connecté !")
                return
            except: 
                time.sleep(1)
                print(f"⏳ Attente connexion... ({i+1}/10)")
        
        print("❌ ECHEC : Impossible de connecter le Pont ROS.")

    def _send(self, cmd, payload=""):
        try:
            requests.post(f"{BRIDGE_URL}/command", json={"command": cmd, "payload": payload}, timeout=0.5)
        except Exception as e:
            # On ignore les timeouts courts (normal pour les commandes rapides)
            pass

    # --- COMMANDES ---
    def wakeup(self): 
        print("🦾 Envoi commande Wakeup...")
        self._send("wakeup")
        time.sleep(2) # Attente que les moteurs s'allument

    def gesture(self, name): self._send("gesture", name)
    def emotion(self, name): self._send("emotion", name)
    def move_head(self, yaw, pitch): 
        # On envoie une string simple "0.5,0.2"
        self._send("head", f"{yaw},{pitch}")

    def screen_off(self):
        """Éteint l'écran du robot en passant par le SSH du FileTransfer"""
        self.transfer.control_screen("off")

    def screen_on(self):
        """Allume l'écran du robot en passant par le SSH du FileTransfer"""
        self.transfer.control_screen("on")

    def play(self, filename):
        if filename.startswith("QT/"):
            self._send("play", filename)
        elif os.path.exists(filename):
            remote_path = self.transfer.send(filename, "stream_audio")
            if remote_path: self._send("play", remote_path)

    # --- VIDEO ---
    def get_camera_frame(self):
        try:
            resp = requests.get(f"{BRIDGE_URL}/camera", timeout=0.5)
            if resp.status_code == 200:
                arr = np.frombuffer(resp.content, np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                return img
        except: pass
        return None

    # --- AUDIO MANAGEMENT ---
    def start_listening(self):
        try:
            self.audio_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.audio_sock.settimeout(2)
            self.audio_sock.connect(("127.0.0.1", AUDIO_PORT))
        except: self.audio_sock = None

    def get_audio_chunk(self):
        if not self.audio_sock: return None
        try: return self.audio_sock.recv(4096)
        except: return None

    def stop_listening(self):
        if self.audio_sock: 
            self.audio_sock.close(); self.audio_sock = None

    def clear_socket_buffer(self):
        if not self.audio_sock: return
        try:
            self.audio_sock.setblocking(0)
            while True:
                data = self.audio_sock.recv(4096)
                if not data: break
        except BlockingIOError: pass
        except Exception as e: print(f"⚠️ Warning flush audio: {e}")
        finally:
            self.audio_sock.setblocking(1)
            self.audio_sock.settimeout(2)