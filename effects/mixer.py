import customtkinter as ctk
import threading
from .base_effect import EffectBase

SLIDER_RANGE = (0, 65535)

class MixerSlider(ctk.CTkFrame):
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
                lock = getattr(self.app.master, 'modbus_lock', None)
                if lock:
                    with lock:
                        self.app.client.write_register(address=self.register_addr, value=self.value, slave=1)
            except Exception as e:
                print(f"Error writing to {self.register_addr}: {e}")
        
        self.write_pending = False

    def set_value(self, val):
        self.value = int(val)
        self.slider.set(val)
        self.val_label.configure(text=f"{(int(val) - 32768) / 32768.0:.2f}")

class Mixer(EffectBase):
    def __init__(self, master, client, config_file="configs/mixer.json"):
        super().__init__(master, client, config_file)
        self.geometry("900x600")
        self.configure(fg_color="#2b2b2b")
        self.resizable(False, False)
        
        # Hide standard header
        self.header_frame.destroy() 
        
        self.updating_from_device = False
        self.sliders = []
        
        # --- Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0) # Title
        self.grid_rowconfigure(1, weight=1) # Sliders
        self.grid_rowconfigure(2, weight=0) # Switch

        # Title
        ctk.CTkLabel(self, text="EFFECTS MIXER", font=("Impact", 24), text_color="#aaaaaa").grid(row=0, column=0, columnspan=2, pady=15)

        # Input Sliders Frame
        self.input_frame = ctk.CTkFrame(self, fg_color="#222222", corner_radius=10)
        self.input_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.input_frame, text="INPUT GAIN", font=("Arial", 14, "bold"), text_color="#888888").pack(pady=10)
        
        self.input_sliders_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.input_sliders_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.create_sliders(self.input_sliders_frame, self.config.get("input_registers", list(range(200, 208))), "IN")

        # Output Slider Frame
        self.output_frame = ctk.CTkFrame(self, fg_color="#222222", corner_radius=10)
        self.output_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.output_frame, text="OUTPUT GAIN", font=("Arial", 14, "bold"), text_color="#888888").pack(pady=10)
        
        self.output_sliders_frame = ctk.CTkFrame(self.output_frame, fg_color="transparent")
        self.output_sliders_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        self.create_sliders(self.output_sliders_frame, [self.config.get("output_register", 208)], "OUT")

        # Bottom Section (ON Switch)
        self.switch_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.switch_frame.grid(row=2, column=0, columnspan=2, pady=15)
        
        # Power Button
        self.power_btn = ctk.CTkButton(
            self.switch_frame, 
            text="ON", 
            width=80, 
            height=40,
            corner_radius=20,
            fg_color="#333333",
            hover_color="#555555",
            command=self.toggle_power,
            font=("Arial", 14, "bold")
        )
        self.power_btn.pack(side="left", padx=10)
        
        # LED Indicator
        self.led_canvas = ctk.CTkCanvas(self.switch_frame, width=20, height=20, bg="#2b2b2b", highlightthickness=0)
        self.led_id = self.led_canvas.create_oval(4, 4, 16, 16, fill="#330000", outline="#550000")
        self.led_canvas.pack(side="left", padx=10)

    def create_sliders(self, parent, registers, prefix):
        for i, reg in enumerate(registers):
            label = f"{prefix}\n{i+1}"
            strip = MixerSlider(parent, label_text=label, register_addr=reg, app_instance=self, fg_color="transparent")
            strip.pack(side="left", expand=True, fill="y", padx=2)
            self.sliders.append(strip)

    def _update_power_ui(self):
        if self.power_state:
            self.led_canvas.itemconfig(self.led_id, fill="#ff0000", outline="#ff3333")
            self.power_btn.configure(fg_color="#550000")
        else:
            self.led_canvas.itemconfig(self.led_id, fill="#330000", outline="#550000")
            self.power_btn.configure(fg_color="#333333")

    def on_power_on(self):
        self._sync_sliders()

    def _sync_sliders(self):
        if not self.client: return
        self.updating_from_device = True
        threading.Thread(target=self._read_and_update_sliders, daemon=True).start()

    def _read_and_update_sliders(self):
        try:
            for strip in self.sliders:
                if not self.client: break
                try:
                    with self.master.modbus_lock:
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
        strip.set_value(value)
