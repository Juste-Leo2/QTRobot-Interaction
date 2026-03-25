# src/scenario_engine.py
"""
Machine à états pour les 3 scénarios d'interaction QTRobot.
Chaque scénario suit un flux linéaire avec des conditions de transition
basées sur la détection d'émotions et de gestes.
"""
import time
import queue
from enum import Enum


class ScenarioState(Enum):
    IDLE = "IDLE"
    DEBUT = "DEBUT"
    EMOTION = "EMOTION"
    EXPLORATION = "EXPLORATION"
    REACTION = "REACTION"
    ACTION = "ACTION"
    CONCLUSION = "CONCLUSION"
    FINISHED = "TERMINÉ"


# ─── Seuils de détection ───
EMOTION_STREAK_REQUIRED = 3    # Nombre de détections consécutives pour valider l'émotion
GESTURE_STREAK_REQUIRED = 1    # Nombre de détections consécutives pour valider le geste
EMOTION_POLL_INTERVAL = 0.1    # Intervalle entre les vérifications (secondes)
GESTURE_POLL_INTERVAL = 0.5    # Intervalle entre les vérifications geste


class ScenarioEngine:
    """
    Moteur de scénario. Gère la logique d'états et les transitions.
    """

    def __init__(self, scenario_id, audio_manager, vest_manager, ui_callback=None):
        """
        :param scenario_id: 1, 2 ou 3
        :param audio_manager: AudioManager
        :param vest_manager: VestManager
        :param ui_callback: Fonction callback(text) pour mettre à jour l'UI
        """
        self.scenario_id = scenario_id
        self.audio = audio_manager
        self.vest = vest_manager
        self.ui_callback = ui_callback

        self.state = ScenarioState.IDLE
        self.running = False

        # Queue thread-safe pour les émotions (le thread vidéo enqueue, le scénario dequeue)
        self._emotion_queue = queue.Queue()

        # Compteurs
        self.emotion_streak = 0
        self.gesture_streak = 0
        self.last_emotion_seen = None
        self.last_gesture_seen = None
        self.audio.screen_on()

    def update_emotion(self, smoothed_emotion):
        """Appelé par le thread vidéo pour envoyer une nouvelle émotion détectée."""
        self._emotion_queue.put(smoothed_emotion)

    def _update_ui(self, text):
        """Met à jour le statut dans l'UI."""
        print(f"📌 [SCÉNARIO {self.scenario_id}] {text}")
        if self.ui_callback:
            self.ui_callback(text)

    def run(self):
        """Lance le scénario (à appeler dans un thread séparé)."""
        self.running = True
        self.state = ScenarioState.DEBUT

        if self.scenario_id == 1:
            self._run_scenario_1()
        elif self.scenario_id == 2:
            self._run_scenario_2()
        elif self.scenario_id == 3:
            self._run_scenario_3()
        else:
            print(f"❌ Scénario {self.scenario_id} inconnu.")
            return

        self.state = ScenarioState.FINISHED
        self._update_ui("✅ Scénario terminé !")
        self.running = False

    def stop(self):
        self.running = False

    # ═══════════════════════════════════════════════════════════════
    #  SCÉNARIO 1 — Le Réconfort (Tristesse → Frottement)
    # ═══════════════════════════════════════════════════════════════
    def _run_scenario_1(self):
        target_emotion = "Sadness"
        target_gesture = "Frottement"

        # ── DÉBUT ──
        self.state = ScenarioState.DEBUT
        self._update_ui("📖 DÉBUT — L'enfant lit un passage triste d'un livre")
        time.sleep(2)

        # ── ÉMOTION ──
        self.state = ScenarioState.EMOTION
        self._update_ui(f"🎭 ÉMOTION — En attente de {target_emotion} ({EMOTION_STREAK_REQUIRED}× consécutives)")
        self._wait_for_emotion(target_emotion)
        if not self.running:
            return

        # ── RÉACTION DU ROBOT ──
        self.state = ScenarioState.REACTION
        self._update_ui("😢 RÉACTION — Le robot prend un air compatissant")
        self.audio.play_emotion("QT/sad")
        time.sleep(1)
        self.audio.speak(
            "Oh, cette histoire a l'air triste... "
            "Tu veux bien me faire une petite caresse pour nous réconforter ?"
        )
        time.sleep(1)

        # ── ACTION PHYSIQUE ──
        self.state = ScenarioState.ACTION
        self._update_ui(f"🤚 ACTION — En attente du geste '{target_gesture}' ({GESTURE_STREAK_REQUIRED}× consécutives)")
        self._wait_for_gesture(target_gesture)
        if not self.running:
            return

        # ── CONCLUSION ──
        self.state = ScenarioState.CONCLUSION
        self._update_ui("😊 CONCLUSION — Le robot sourit")
        self.audio.play_emotion("QT/happy")
        self.audio.play_gesture("QT/kiss")
        time.sleep(1)
        self.audio.speak("Merci beaucoup, ça va beaucoup mieux maintenant !")

    # ═══════════════════════════════════════════════════════════════
    #  SCÉNARIO 2 — L'Encouragement Joyeux (Joie → Tape)
    # ═══════════════════════════════════════════════════════════════
    def _run_scenario_2(self):
        target_emotion = "Happiness"
        target_gesture = "Tape"

        # ── DÉBUT ──
        self.state = ScenarioState.DEBUT
        self._update_ui("👋 DÉBUT — Le robot salue l'enfant")
        self.audio.play_emotion("QT/happy")
        self.audio.play_gesture("QT/hi")
        time.sleep(1)
        self.audio.speak(
            "Coucou ! Montre-moi ton plus beau sourire pour voir si tu es en forme aujourd'hui !"
        )
        time.sleep(1)

        # ── ÉMOTION ──
        self.state = ScenarioState.EMOTION
        self._update_ui(f"🎭 ÉMOTION — En attente de {target_emotion} ({EMOTION_STREAK_REQUIRED}× consécutives)")
        self._wait_for_emotion(target_emotion)
        if not self.running:
            return

        # ── RÉACTION DU ROBOT ──
        self.state = ScenarioState.REACTION
        self._update_ui("🤩 RÉACTION — Le robot est joyeux")
        self.audio.play_emotion("QT/happy")
        self.audio.play_gesture("QT/wave")
        time.sleep(1)
        self.audio.speak(
            "Wahou, quel sourire magnifique ! "
            "Ça me donne trop d'énergie ! "
            "Allez, tope-là ! Fais-moi une belle tape sur le ventre !"
        )
        time.sleep(1)

        # ── ACTION PHYSIQUE ──
        self.state = ScenarioState.ACTION
        self._update_ui(f"🤚 ACTION — En attente du geste '{target_gesture}' ({GESTURE_STREAK_REQUIRED}× consécutives)")
        self._wait_for_gesture(target_gesture)
        if not self.running:
            return

        # ── CONCLUSION ──
        self.state = ScenarioState.CONCLUSION
        self._update_ui("🎉 CONCLUSION — Animation joyeuse")
        self.audio.play_emotion("QT/happy")
        self.audio.play_gesture("QT/nod")
        time.sleep(1)
        self.audio.speak("Ouais ! Super équipe, on va bien s'amuser !")

    # ═══════════════════════════════════════════════════════════════
    #  SCÉNARIO 3 — Le Rêve (Veille → Pincement)
    # ═══════════════════════════════════════════════════════════════
    def _run_scenario_3(self):
        target_gesture = "Pincement"

    # ── DÉBUT ──
        self.state = ScenarioState.DEBUT
        self._update_ui("😴 DÉBUT — Le robot est en mode veille (tête baissée, écran éteint)")
        
        # 1. On éteint l'écran tout de suite
        self.audio.screen_off()
        
        # Robot dort : tête baissée, yeux fermés
        self.audio.play_emotion("QT/neutral")
        self.audio.move_head(0, 70)  # Tête penchée vers le bas (en degrés)
        time.sleep(2)

        # ── EXPLORATION LIBRE ──
        self.state = ScenarioState.EXPLORATION
        self._update_ui(
            "🔍 EXPLORATION LIBRE — L'enfant peut frotter, parler... "
            f"En attente de '{target_gesture}' ({GESTURE_STREAK_REQUIRED}× consécutives)"
        )
        
        # Le robot attend de détecter le pincement
        self._wait_for_gesture(target_gesture)
        if not self.running:
            return

        # ── LE GESTE EST DÉTECTÉ ──
        
        # 2. Le pincement a été vu, on rallume l'écran !
        self.audio.screen_on()
        
        # (Optionnel) Tu peux rajouter une petite émotion de réveil juste après
        # self.audio.play_emotion("QT/happy")

        # ── RÉACTION DU ROBOT ──
        self.state = ScenarioState.REACTION
        self._update_ui("😲 RÉACTION — Le robot sursaute !")
        # Robot sursaute : tête relevée + surprise
        self.audio.move_head(0, 0)  # Tête relevée
        time.sleep(0.5)
        self.audio.play_emotion("QT/surprise")
        self.audio.play_gesture("QT/surprise")
        time.sleep(2)

        # ── CONCLUSION ──
        self.state = ScenarioState.CONCLUSION
        self._update_ui("🌟 CONCLUSION — Le robot se réveille")
        self.audio.play_emotion("QT/happy")
        time.sleep(1)
        self.audio.speak(
            "Oups ! Pardon, je faisais un super rêve ! "
            "Bonjour toi, tu m'as réveillé, tu es prêt à jouer ?"
        )

    # ═══════════════════════════════════════════════════════════════
    #  UTILITAIRES DE DÉTECTION
    # ═══════════════════════════════════════════════════════════════
    def _wait_for_emotion(self, target_emotion):
        """
        Attend que l'émotion cible soit détectée EMOTION_STREAK_REQUIRED fois
        de manière consécutive via la Queue.
        - Chaque appel à queue.get() attend une NOUVELLE détection
        - Si une émotion DIFFÉRENTE est détectée → reset du streak
        """
        self.emotion_streak = 0
        self.last_emotion_seen = None

        # Vider la queue de tout résidu
        while not self._emotion_queue.empty():
            try:
                self._emotion_queue.get_nowait()
            except queue.Empty:
                break

        print(f"🔍 [DEBUG] Attente émotion '{target_emotion}' ({EMOTION_STREAK_REQUIRED}× consécutives)")

        while self.running and self.emotion_streak < EMOTION_STREAK_REQUIRED:
            try:
                # Bloque jusqu'à recevoir une nouvelle émotion (timeout pour vérifier self.running)
                emotion = self._emotion_queue.get(timeout=0.5)
            except queue.Empty:
                # Timeout — pas de nouvelle détection, on reboucle
                continue

            # Nouvelle détection reçue
            if emotion.lower() == target_emotion.lower():
                self.emotion_streak += 1
                print(f"🔍 [DEBUG] Streak: {emotion} → {self.emotion_streak}/{EMOTION_STREAK_REQUIRED}")
                self._update_ui(
                    f"🎭 ÉMOTION — Détection: {emotion} "
                    f"({self.emotion_streak}/{EMOTION_STREAK_REQUIRED})"
                )
            else:
                if self.emotion_streak > 0:
                    print(f"🔍 [DEBUG] Reset ! '{emotion}' au lieu de '{target_emotion}'")
                    self._update_ui(
                        f"🎭 ÉMOTION — Reset ! Détecté '{emotion}' au lieu de '{target_emotion}' "
                        f"(0/{EMOTION_STREAK_REQUIRED})"
                    )
                self.emotion_streak = 0

            self.last_emotion_seen = emotion

        if self.emotion_streak >= EMOTION_STREAK_REQUIRED:
            print(f"✅ [DEBUG] ÉMOTION VALIDÉE : {target_emotion} — passage à l'étape suivante !")
            self._update_ui(f"✅ ÉMOTION VALIDÉE : {target_emotion} ({EMOTION_STREAK_REQUIRED}×)")

    def _wait_for_gesture(self, target_gesture):
        """
        Attend que le geste cible soit détecté GESTURE_STREAK_REQUIRED fois
        de manière consécutive.
        """
        self.gesture_streak = 0
        self.last_gesture_seen = None

        while self.running and self.gesture_streak < GESTURE_STREAK_REQUIRED:
            gesture = self.vest.get_gesture(clear_after=True)

            if gesture is not None:
                if gesture == target_gesture:
                    self.gesture_streak += 1
                    self._update_ui(
                        f"🤚 GESTE — Détection: {gesture} "
                        f"({self.gesture_streak}/{GESTURE_STREAK_REQUIRED})"
                    )
                else:
                    if self.gesture_streak > 0:
                        self._update_ui(
                            f"🤚 GESTE — Reset ! Détecté '{gesture}' au lieu de '{target_gesture}' "
                            f"(0/{GESTURE_STREAK_REQUIRED})"
                        )
                    self.gesture_streak = 0

                self.last_gesture_seen = gesture

            time.sleep(GESTURE_POLL_INTERVAL)

        if self.gesture_streak >= GESTURE_STREAK_REQUIRED:
            self._update_ui(f"✅ GESTE VALIDÉ : {target_gesture} ({GESTURE_STREAK_REQUIRED}×)")
