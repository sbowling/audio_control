import customtkinter as ctk
import threading
import json
import os
from .base_effect import EffectBase

FREQ_LABELS = ["31.5", "63", "125", "250", "500", "1K", "2K", "4K", "8K", "16K"]
SLIDER_RANGE = (0, 65535)

class SliderStrip(ctk.CTkFrame):
    def __init__(self, master, label_text, register_addr, app_instance, **kwargs):
        super().__init__(master, **kwargs)
        self.register_addr = register_addr
        self.app = app_instance
        self.value = 0
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.val_label = ctk.CTkLabel(self, text="0", font=("Consolas", 12), text_color="#00ff00")
        self.val_label.grid(row=0, column=0, pady=(5, 0))
        
        self.slider = ctk.CTkSlider(
            self, 
            from_=SLIDER_RANGE[0], 
            to=SLIDER_RANGE[1], 
            orientation="vertical",
            command=self.on_slider_change,
            height=200,
            width=20,
            progress_color="#00ff00",
            button_color="#cccccc",
            button_hover_color="#ffffff"
        )
        self.slider.set(0)
        self.slider.grid(row=1, column=0, pady=10, sticky="ns")
        
        self.freq_label = ctk.CTkLabel(self, text=label_text, font=("Arial", 10, "bold"))
        self.freq_label.grid(row=2, column=0, pady=(0, 5))

        self.write_pending = False

    def on_slider_change(self, value):
        if self.app.updating_from_device:
            self.val_label.configure(text=f"{(int(value) - 32768) / 32768.0:.2f}")
            self.value = int(value)
            return

        val = int(value)
        self.value = val
        norm_val = (val - 32768) / 32768.0
        self.val_label.configure(text=f"{norm_val:.2f}")
        
        if not self.write_pending:
            self.write_pending = True
            self.after(100, self.process_write)

    def process_write(self):
        if self.app.client and self.app.client.connected and self.app.power_state:
            try:
                self.app.client.write_register(address=self.register_addr, value=self.value, slave=1)
            except Exception as e:
                print(f"Error writing to {self.register_addr}: {e}")
        
        self.write_pending = False

class GraphicEQ(EffectBase):
    def __init__(self, master, client, config_file="configs/graphic_eq.json"):
        super().__init__(master, client, config_file)
        self.geometry("1100x700")
        self.updating_from_device = False
        self.all_sliders = []
        
        # Reset Button (specific to EQ)
        self.reset_btn = ctk.CTkButton(self.header_frame, text="EQ RESET", width=80, command=self.reset_eq, fg_color="#333333")
        self.reset_btn.grid(row=0, column=1, padx=5)

        # EQ Layout
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=1)
        
        self.left_frame = ctk.CTkFrame(self.content_frame, fg_color="#222222", corner_radius=10)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.left_frame, text="LEFT CHANNEL", font=("Arial", 14, "bold"), text_color="#888888").pack(pady=10)
        self.left_sliders = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.left_sliders.pack(expand=True, fill="both", padx=10, pady=10)
        self.create_sliders(self.left_sliders, self.config["left_channel_registers"])

        self.right_frame = ctk.CTkFrame(self.content_frame, fg_color="#222222", corner_radius=10)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.right_frame, text="RIGHT CHANNEL", font=("Arial", 14, "bold"), text_color="#888888").pack(pady=10)
        self.right_sliders = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.right_sliders.pack(expand=True, fill="both", padx=10, pady=10)
        self.create_sliders(self.right_sliders, self.config["right_channel_registers"])

    def create_sliders(self, parent, registers):
        for i, freq in enumerate(FREQ_LABELS):
            reg = registers[i] if i < len(registers) else 0
            strip = SliderStrip(parent, label_text=freq, register_addr=reg, app_instance=self, fg_color="transparent")
            strip.pack(side="left", expand=True, fill="y", padx=2)
            self.all_sliders.append(strip)

    def reset_eq(self):
        center_val = 32767
        for strip in self.all_sliders:
            strip.slider.set(center_val)
            strip.on_slider_change(center_val)

    def on_power_on(self):
        self._sync_all_sliders()

    def _sync_all_sliders(self):
        if not self.client: return
        self.updating_from_device = True
        threading.Thread(target=self._read_and_update_sliders, daemon=True).start()

    def _read_and_update_sliders(self):
        try:
            for strip in self.all_sliders:
                if not self.client: break
                try:
                    rr = self.client.read_holding_registers(address=strip.register_addr, count=1, slave=1)
                    if not rr.isError():
                        val = rr.registers[0]
                        self.after(0, lambda s=strip, v=val: self._update_slider_ui(s, v))
                except Exception as e:
                    print(f"Read Error for {strip.register_addr}: {e}")
            self.after(500, lambda: setattr(self, 'updating_from_device', False))
        except Exception as e:
             self.updating_from_device = False

    def _update_slider_ui(self, strip, value):
        self.updating_from_device = True 
        strip.slider.set(value)
        strip.on_slider_change(value)
