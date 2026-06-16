import socket
import time
import collections
from collections import Counter
import numpy as np
import onnxruntime as ort
import sys
import os
import threading

# --- CONFIGURATION DU SERVEUR ---
HOST = '0.0.0.0'
PORT = 65432

# --- PARAMÈTRES IA / SIGNAL ---
ACQUISITION_FREQ = 1000        # 1kHz d'acquisition matérielle
DOWNSAMPLING = 10              # Moyenne tous les 10 points (-> Vrai 100Hz effectif)
MODEL_PATH = "tactile_deriv_drop_model.onnx"

# Nos 5 classes
CLASSES = [
    "Rien / Bruit", 
    "Tape_Attention", 
    "Caresse_Reconfortante", 
    "Chatouilles", 
    "Calin"
]

# Pondération neutre (le Z-score fait le travail)
CLASS_WEIGHTS = np.array([1.0, 0.3, 1.0, 1.0, 1.0]) 

WINDOW_SIZE = 500              
INFERENCE_STRIDE = 300         

# On garde un seuil un peu plus bas (0.50) car le Label Smoothing 
# empêche le modèle de monter à 99% de certitude.
SCORE_THRESHOLD = 0.50        

# Le signal n'est plus divisé par 1023, on remet le seuil d'ADC brut à 0.5
SEUIL_STABILITE = 0.5       

VOTE_WINDOW_SIZE = 2           
CONFIRMATION_SIZE = 2          
COOLDOWN_DELAY = 5.0           

# --- CONFIGURATION MATÉRIELLE (SPI) ---
SPI_BUS = 0
SPI_DEVICE = 0
CANAUX = [4, 3, 0, 1, 2]       

SPIDEV_AVAILABLE = False
try:
    import spidev
    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_DEVICE)
    spi.max_speed_hz = 1350000
    SPIDEV_AVAILABLE = True
except Exception as e:
    pass 

def read_adc(canal):
    if SPIDEV_AVAILABLE:
        r = spi.xfer2([1, (8 + canal) << 4, 0])
        val = ((r[1] & 3) << 8) + r[2]
        return val
    else:
        return 512 + np.random.randint(-10, 10)

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

class GestureThread(threading.Thread):
    def __init__(self, client_socket=None):
        super().__init__()
        self.client_socket = client_socket
        self.running = True
        
        clear_terminal()
        print(f"--- Démarrage Serveur Veste (PID: {os.getpid()}) ---")
        
        if not os.path.exists(MODEL_PATH):
            print(f"ERREUR: {MODEL_PATH} introuvable.")
            self.running = False
            return

        try:
            self.session = ort.InferenceSession(MODEL_PATH)
            self.input_name = self.session.get_inputs()[0].name
            print("Modèle chargé avec succès.")
        except Exception as e:
            print(f"Erreur ONNX: {e}")
            self.running = False

        self.raw_buffer = collections.deque(maxlen=WINDOW_SIZE)
        self.vote_buffer = collections.deque(maxlen=VOTE_WINDOW_SIZE)
        self.confirmation_buffer = collections.deque(maxlen=CONFIRMATION_SIZE)
        self.historique_gestes = collections.deque(maxlen=5) 
        
        self.accumulator = []
        self._reset_buffers(initial_fill=True)

    def _reset_buffers(self, initial_fill=False):
        self.vote_buffer.clear()
        for _ in range(VOTE_WINDOW_SIZE): 
            self.vote_buffer.append(0)
        
        self.confirmation_buffer.clear()
        self.accumulator = []
        
        if initial_fill:
            vals = []
            for _ in range(10):
                vals.append([read_adc(c) for c in CANAUX])
            avg_start = np.mean(vals, axis=0) 
            
            self.raw_buffer.clear()
            for _ in range(WINDOW_SIZE): 
                self.raw_buffer.append(avg_start)

    def run(self):
        print("Démarrage de la boucle d'inférence temps réel dans 2 secondes...")
        time.sleep(2)
        points_processed_counter = 0 
        
        while self.running:
            try:
                loop_start = time.time()
                
                current_vals = [read_adc(c) for c in CANAUX]
                self.accumulator.append(current_vals)
                
                if len(self.accumulator) >= DOWNSAMPLING:
                    avg_val = np.mean(self.accumulator, axis=0)
                    self.accumulator = []
                    
                    self.raw_buffer.append(avg_val)
                    points_processed_counter += 1
                    
                    valeurs_str = " | ".join([f"C{i}:{int(v):>4}" for i, v in enumerate(avg_val)])
                    sys.stdout.write(f"\r[CAPTEURS 100Hz] {valeurs_str} ")
                    sys.stdout.flush()
                    
                    if points_processed_counter % INFERENCE_STRIDE == 0:
                        
                        raw_signal = np.array(self.raw_buffer, dtype=np.float32)
                        
                        ecart_type = np.std(raw_signal)
                        instant_pred = 0
                        
                        clear_terminal()
                        print("=" * 70)
                        print("🤖 --- TABLEAU DE BORD IA (Mise à jour toutes les 3s) --- 🤖")
                        print("=" * 70)
                        print(f"Écart-type du signal : {ecart_type:.2f} (Seuil d'éveil: {SEUIL_STABILITE})")
                        print("-" * 70)
                        print(f"Derniers gestes validés : {list(self.historique_gestes) if self.historique_gestes else 'Aucun'}")
                        print("-" * 70)
                        
                        if ecart_type >= SEUIL_STABILITE:
                            
                            # 1. Calcul de la dérivée
                            derivative = np.diff(raw_signal, axis=0)
                            pad_zeros = np.zeros((1, 5), dtype=np.float32)
                            derivative = np.vstack((pad_zeros, derivative))
                            
                            # 2. Formatage [Batch=1, Canaux=5, Temps=500]
                            input_data = derivative.transpose(1, 0)
                            input_data = input_data.reshape(1, 5, WINDOW_SIZE)
                            
                            # Normalisation
                            input_data = input_data / 1023.0
                            
                            # 3. Lancement ONNX
                            outputs = self.session.run(None, {self.input_name: input_data})
                            
                            # 4. Calcul du Softmax
                            exp_preds = np.exp(outputs[0][0])
                            raw_probs = exp_preds / np.sum(exp_preds)
                            
                            # Pondération neutre
                            weighted_probs = raw_probs * CLASS_WEIGHTS
                            final_probs = weighted_probs / np.sum(weighted_probs)
                            
                            probs_str = " | ".join([f"{CLASSES[i]}:{final_probs[i]*100:>3.0f}%" for i in range(len(CLASSES))])
                            print(f"\n[PROBABILITÉS] {probs_str}")
                            
                            if np.max(final_probs) > SCORE_THRESHOLD:
                                instant_pred = np.argmax(final_probs)
                        else:
                            print("\n[IA EN VEILLE] Signal trop faible, en attente de mouvement...")
                        
                        self.vote_buffer.append(instant_pred)
                        winner_class, _ = Counter(self.vote_buffer).most_common(1)[0]
                        
                        if ecart_type >= SEUIL_STABILITE:
                            noms_vote_buffer = [CLASSES[v] for v in self.vote_buffer]
                            print(f"[VOTE CT]      Préd. Instant: {CLASSES[instant_pred]:<21}")
                            print(f"               Gagnant CT   : {CLASSES[winner_class]:<21} | Buffer: {noms_vote_buffer}")
                        
                        self.confirmation_buffer.append(winner_class)

                        if len(self.confirmation_buffer) == CONFIRMATION_SIZE:
                            unique_votes = set(self.confirmation_buffer)
                            
                            if ecart_type >= SEUIL_STABILITE:
                                noms_conf_buffer = [CLASSES[v] for v in self.confirmation_buffer]
                                print(f"[CONFIRMATION] Buffer : {noms_conf_buffer}")
                            
                            if len(unique_votes) == 1:
                                confirmed_gesture = list(unique_votes)[0]
                                
                                if confirmed_gesture != 0:
                                    nom = CLASSES[confirmed_gesture]
                                    print("\n" + "★" * 50)
                                    print(f"  >>> GESTE DÉTECTÉ ET VALIDÉ : {nom} <<<")
                                    print("★" * 50 + "\n")
                                    
                                    heure = time.strftime("%H:%M:%S")
                                    self.historique_gestes.append(f"{nom} ({heure})")
                                    
                                    if self.client_socket is not None:
                                        try:
                                            self.client_socket.sendall((nom + '\n').encode('utf-8'))
                                        except (BrokenPipeError, ConnectionResetError):
                                            self.client_socket = None
                                    
                                    self._reset_buffers(initial_fill=True)
                                    continue 
                        
                        print("\n")

                elapsed = time.time() - loop_start
                sleep_time = (1.0 / ACQUISITION_FREQ) - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            except Exception as e:
                print(f"\n[Thread] Erreur fatale boucle: {e}")
                self.running = False

    def stop(self):
        self.running = False

if __name__ == "__main__":
    clear_terminal()
    print("Initialisation Réseau...")
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    client = None
    try:
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)
        server_socket.settimeout(1.0) 
        
        print(f"En attente de connexion du PC sur {HOST}:{PORT} (Facultatif)...")
        try:
            client, addr = server_socket.accept()
            print(f"--- PC Hôte Connecté : {addr} ---")
            client.settimeout(None)
        except socket.timeout:
            print("--- Aucun PC connecté. Lancement en mode AUTONOME. ---")
        
        gesture_thread = GestureThread(client)
        gesture_thread.start()
        
        while gesture_thread.is_alive():
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nArrêt manuel demandé par l'utilisateur.")
    except Exception as e:
        print(f"Erreur globale dans le Main: {e}")
    finally:
        if 'gesture_thread' in locals():
            gesture_thread.stop()
            gesture_thread.join()
        if client is not None:
            client.close()
        server_socket.close()
        print("Serveur éteint proprement.")
