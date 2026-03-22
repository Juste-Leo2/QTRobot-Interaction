import customtkinter as ctk
from PIL import Image

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class UI(ctk.CTk):
    def __init__(self, scenario_id=1):
        super().__init__()

        self.title(f"QTRobot — Scénario {scenario_id}")
        self.geometry("960x600")

        # --- Layout : 2 colonnes (image + statut) ---
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Cadre Image (Gauche) ---
        self.left_frame = ctk.CTkFrame(self, corner_radius=0)
        self.left_frame.grid(row=0, column=0, sticky="nsew")
        
        self.image_label = ctk.CTkLabel(self.left_frame, text="Démarrage caméra...")
        self.image_label.place(relx=0.5, rely=0.5, anchor="center")

        # --- Cadre Statut (Droite) ---
        self.right_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # Titre scénario
        self.title_label = ctk.CTkLabel(
            self.right_frame, 
            text=f"Scénario {scenario_id}",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_label.pack(pady=(10, 5))

        # Label état principal
        state_title = ctk.CTkLabel(
            self.right_frame, text="État", 
            font=ctk.CTkFont(weight="bold")
        )
        state_title.pack(anchor="w", pady=(15, 0))

        self.state_label = ctk.CTkLabel(
            self.right_frame, 
            text="⏳ En attente...",
            font=ctk.CTkFont(size=13),
            wraplength=250,
            justify="left"
        )
        self.state_label.pack(anchor="w", padx=5, pady=(5, 10))

        # Label émotion détectée
        emo_title = ctk.CTkLabel(
            self.right_frame, text="Émotion détectée",
            font=ctk.CTkFont(weight="bold")
        )
        emo_title.pack(anchor="w", pady=(10, 0))

        self.emotion_label = ctk.CTkLabel(
            self.right_frame,
            text="—",
            font=ctk.CTkFont(size=13),
            wraplength=250,
            justify="left"
        )
        self.emotion_label.pack(anchor="w", padx=5, pady=(5, 10))

        # Log compact
        log_title = ctk.CTkLabel(
            self.right_frame, text="Logs",
            font=ctk.CTkFont(weight="bold")
        )
        log_title.pack(anchor="w", pady=(10, 0))

        self.log_textbox = ctk.CTkTextbox(self.right_frame, height=200)
        self.log_textbox.pack(fill="both", expand=True, pady=(5, 0))

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def mettre_a_jour_image(self, pil_image):
        """Reçoit une image PIL et l'affiche."""
        w, h = pil_image.size
        ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(w, h))
        self.image_label.configure(image=ctk_img, text="")

    def update_status(self, text):
        """Met à jour le label d'état du scénario."""
        self.state_label.configure(text=text)

    def update_emotion(self, text):
        """Met à jour le label d'émotion."""
        self.emotion_label.configure(text=text)

    def add_log(self, text):
        """Ajoute une ligne au log compact."""
        self.log_textbox.insert("end", text + "\n")
        self.log_textbox.see("end")

    def on_closing(self):
        self.destroy()