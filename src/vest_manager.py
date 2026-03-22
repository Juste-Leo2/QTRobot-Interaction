# src/vest_manager.py
"""
Abstraction capteur veste :
- Mode local  : input() dans un thread pour simuler les gestes
- Mode QT     : RaspberryManager (SSH + Socket vers le Raspberry Pi)
"""
import threading


class VestManager:
    def __init__(self, qt_mode=False, raspberry_manager=None):
        self.qt_mode = qt_mode
        self.raspberry = raspberry_manager
        self.last_gesture = None
        self._running = False
        self._thread = None

        if not self.qt_mode:
            print("🧤 [VESTE] Mode local — Simulation par terminal")
        else:
            print("🧤 [VESTE] Mode QT — RaspberryManager (SSH + Socket)")

    def start(self):
        """Démarre l'écoute des gestes."""
        self._running = True
        if not self.qt_mode:
            self._thread = threading.Thread(target=self._terminal_loop, daemon=True)
            self._thread.start()
        else:
            if self.raspberry:
                self.raspberry.connect_and_start()

    def _terminal_loop(self):
        """Boucle d'input terminal (mode local uniquement)."""
        gestes_valides = ["Tape", "Frottement", "Pincement"]
        while self._running:
            try:
                print(f"\n🧤 [VESTE] Entrez un geste ({', '.join(gestes_valides)}) : ", end="", flush=True)
                user_input = input().strip()
                if user_input in gestes_valides:
                    self.last_gesture = user_input
                    print(f"🧤 [VESTE] Geste reçu : {user_input}")
                elif user_input.lower() == "quit":
                    self._running = False
                else:
                    print(f"🧤 [VESTE] Geste inconnu : '{user_input}' (valides: {gestes_valides})")
            except EOFError:
                break

    def get_gesture(self, clear_after=True):
        """
        Retourne le dernier geste détecté ou None.
        Si clear_after=True, remet à None après lecture.
        """
        if self.qt_mode and self.raspberry:
            data = self.raspberry.get_data(clear_after=clear_after)
            return data
        else:
            gesture = self.last_gesture
            if clear_after:
                self.last_gesture = None
            return gesture

    def stop(self):
        """Arrête l'écoute."""
        self._running = False
        if self.qt_mode and self.raspberry:
            self.raspberry.stop()
        print("🧤 [VESTE] Arrêté.")
