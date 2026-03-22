# src/camera_manager.py
"""
Abstraction caméra : OpenCV local ou caméra ROS via RemoteRosClient.
"""
import cv2


class CameraManager:
    def __init__(self, qt_mode=False, ros_client=None):
        self.qt_mode = qt_mode
        self.ros_client = ros_client
        self.cap = None

        if not self.qt_mode:
            print("📷 [CAMERA] Mode local — OpenCV VideoCapture(0)")
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise RuntimeError("Impossible d'ouvrir la caméra locale.")
        else:
            print("📷 [CAMERA] Mode QT — Caméra ROS via RemoteRosClient")

    def get_frame(self):
        """Retourne une frame BGR (numpy array) ou None."""
        if self.qt_mode:
            return self.ros_client.get_camera_frame()
        else:
            ret, frame = self.cap.read()
            return frame if ret else None

    def release(self):
        if self.cap:
            self.cap.release()
            print("📷 [CAMERA] Caméra locale libérée.")
