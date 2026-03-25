# src/face_tracking.py
"""
Logique de suivi de visage pour le robot QT.
Convertit les coordonnées en pixels d'un visage en commandes de mouvement (yaw, pitch) en degrés.
"""

class FaceTracker:
    def __init__(self, audio_manager):
        self.audio = audio_manager
        self.active = False
        self.yaw = 0.0
        self.pitch = 0.0
        
        # Paramètres de contrôle PID simples (Proportionnel)
        self.k_yaw = 0.05
        self.k_pitch = 0.05
        
        # Limites du robot QT (approximatives)
        self.max_yaw = 60.0
        self.min_yaw = -60.0
        self.max_pitch = 20.0
        self.min_pitch = -20.0
        
    def start(self):
        self.active = True
        
    def stop(self):
        self.active = False
        
    def reset_position(self):
        self.yaw = 0.0
        self.pitch = 0.0
        if self.audio:
            self.audio.move_head(0, 0)
            
    def update(self, box, frame_w=640, frame_h=480):
        """
        Met à jour la position de la tête du robot en fonction de la bounding box du visage.
        :param box: [x1, y1, x2, y2]
        """
        if not self.active or box is None:
            return
            
        # Extraction du centre du visage
        x1, y1, x2, y2 = box
        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0
        
        # Calcul de l'erreur par rapport au centre de l'image
        err_x = center_x - (frame_w / 2.0)
        err_y = center_y - (frame_h / 2.0)
        
        # Zone neutre (deadzone) pour éviter les tremblements
        if abs(err_x) < 30 and abs(err_y) < 30:
            return
            
        # Mise à jour des angles
        # QT yaw: positif = gauche, négatif = droite. 
        # Si err_x > 0 (visage à droite), on tourne à droite (yaw diminue)
        self.yaw -= err_x * self.k_yaw
        
        # QT pitch: positif = bas, négatif = haut.
        # Si err_y > 0 (visage en bas), on baisse la tête (pitch augmente)
        self.pitch += err_y * self.k_pitch
        
        # Limitation aux bornes de sécurité
        self.yaw = max(self.min_yaw, min(self.max_yaw, self.yaw))
        self.pitch = max(self.min_pitch, min(self.max_pitch, self.pitch))
        
        # Envoi de la commande au robot
        if self.audio:
            self.audio.move_head(int(self.yaw), int(self.pitch))
