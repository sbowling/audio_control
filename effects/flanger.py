import customtkinter as ctk
import threading
from .base_effect import EffectBase
from .utils import RotaryKnob

class Flanger(EffectBase):
    def __init__(self, master, client, config_file="configs/flanger.json"):
        super().__init__(master, client, config_file)
        
        # --- Stompbox UI Setup ---
        self.geometry("350x600")
        self.configure(fg_color="#FF8C00") # Dark Orange (classic Flanger color)
        self.resizable(False, False)
        
        # Hide standard header
        self.header_frame.destroy() 
        
        self.updating_from_device = False
        self.knobs = []
        
        # --- Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Title
        self.grid_rowconfigure(1, weight=1) # Knobs
        self.grid_rowconfigure(2, weight=0) # LED
        self.grid_rowconfigure(3, weight=0) # Switch
        
        # Title
        ctk.CTkLabel(self, text="Flanger", font=("Impact", 28), text_color="black").grid(row=0, column=0, pady=(20, 10))

        # Knobs Container
        self.knob_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.knob_frame.grid(row=1, column=0, sticky="n", pady=10)
        
        # Rate Knob
        self.create_knob(self.knob_frame, "RATE", self.config.get("rate_register", 70))
        
        # Spacer
        ctk.CTkLabel(self.knob_frame, text="   ").pack(side="left")
        
        # Depth Knob
        self.create_knob(self.knob_frame, "DEPTH", self.config.get("depth_register", 71))
        
        # Spacer
        ctk.CTkLabel(self.knob_frame, text="   ").pack(side="left")

        # Regen Knob
        self.create_knob(self.knob_frame, "REGEN", self.config.get("regen_register", 72))

        # LED Indicator
        self.led_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.led_frame.grid(row=2, column=0, pady=(5, 15))
        
        self.led_canvas = ctk.CTkCanvas(self.led_frame, width=20, height=20, bg="#FF8C00", highlightthickness=0)
        self.led_id = self.led_canvas.create_oval(4, 4, 16, 16, fill="#330000", outline="#550000") # Off state
        self.led_canvas.pack()
        
        ctk.CTkLabel(self.led_frame, text="CHECK", font=("Arial", 10, "bold"), text_color="black").pack()

        # Bottom Section (Foot Switch) - Just the button, no surrounding black box
        # Use transparent frame or match background color
        self.switch_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=10)
        self.switch_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="s")
        
        # Actual Button - Styled like a pedal plate
        self.pedal_btn = ctk.CTkButton(
            self.switch_frame,
            text="BYPASS",
            fg_color="#222222",
            text_color="white",
            hover_color="#333333",
            height=100,
            width=280,
            corner_radius=5,
            command=self.toggle_power
        )
        self.pedal_btn.pack(expand=True)

    def create_knob(self, parent, label, reg):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(side="left", padx=10)
        
        knob_helper = {
            "reg": reg,
            "write_pending": False,
            "value": 32767
        }
        
        def on_change(v):
            if self.updating_from_device: return
            knob_helper["value"] = int(v)
            if not knob_helper["write_pending"]:
                knob_helper["write_pending"] = True
                self.after(100, lambda: process_write(knob_helper))

        def process_write(helper):
            if self.client and self.client.connected and self.power_state:
                try:
                    lock = getattr(self.master, 'modbus_lock', None)
                    if lock:
                        with lock:
                            self.client.write_register(address=helper["reg"], value=helper["value"], slave=1)
                except Exception as e:
                    print(f"Flanger Knob Write Error: {e}")
            helper["write_pending"] = False

        knob = RotaryKnob(frame, width=70, height=70, start_val=32767, command=on_change, bg_color="#FF8C00")
        knob.pack()
        
        ctk.CTkLabel(frame, text=label, font=("Arial", 12, "bold"), text_color="black").pack(pady=(5, 0))
        
        self.knobs.append({"knob": knob, "reg": reg})

    def _update_power_ui(self):
        # Override Base Effect UI update to use our custom LED
        if self.power_state:
            self.led_canvas.itemconfig(self.led_id, fill="#ff0000", outline="#ff3333")
        else:
            self.led_canvas.itemconfig(self.led_id, fill="#330000", outline="#550000")

    def on_power_on(self):
        self._sync_knobs()

    def _sync_knobs(self):
        if not self.client: return
        self.updating_from_device = True
        threading.Thread(target=self._read_and_update_knobs, daemon=True).start()

    def _read_and_update_knobs(self):
        try:
            for item in self.knobs:
                if not self.client: break
                try:
                    with self.master.modbus_lock:
                        rr = self.client.read_holding_registers(address=item["reg"], count=1, slave=1)
                    if not rr.isError():
                        val = rr.registers[0]
                        self.after(0, lambda k=item["knob"], v=val: k.set(v))
                except Exception as e:
                    print(f"Read Error Flanger {item['reg']}: {e}")
            self.after(500, lambda: setattr(self, 'updating_from_device', False))
        except Exception as e:
            self.updating_from_device = False
