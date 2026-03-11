import customtkinter as ctk
from effects.base_effect import EffectBase

class ParametricEQ(EffectBase):
    def __init__(self, master, client, config_file):
        super().__init__(master, client, config_file)
        self.geometry("400x300")
        self.label = ctk.CTkLabel(self.content_frame, text="Parametric EQ Controls Placeholder", font=("Arial", 16))
        self.label.pack(expand=True)

class Echo(EffectBase):
    def __init__(self, master, client, config_file):
        super().__init__(master, client, config_file)
        self.geometry("400x300")
        self.label = ctk.CTkLabel(self.content_frame, text="Echo Controls Placeholder", font=("Arial", 16))
        self.label.pack(expand=True)

class Reverb(EffectBase):
    def __init__(self, master, client, config_file):
        super().__init__(master, client, config_file)
        self.geometry("400x300")
        self.label = ctk.CTkLabel(self.content_frame, text="Reverb Controls Placeholder", font=("Arial", 16))
        self.label.pack(expand=True)
