import customtkinter as ctk
import threading
from .base_effect import EffectBase
from .utils import RotaryKnob

class Chorus(EffectBase):
    def __init__(self, master, client, config_file="configs/chorus.json"):
        super().__init__(master, client, config_file)
        
        # --- Stompbox UI Setup ---
        self.geometry("350x550")
        self.configure(fg_color="#4169E1") # Royal Blue (classic Chorus color)
        self.resizable(False, False)
        
        # Hide standard header
        self.header_frame.destroy() 
        self.content_frame.destroy() # We'll use our own layout
        
        self.updating_from_device = False
        self.knobs = []
        
        # --- Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) # Top (Knobs)
        self.grid_rowconfigure(1, weight=1) # Bottom (Switch)

        # 1. Top Section (Controls & LED)
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", pady=(20, 10))
        
        # LED Indicator (Top Center or Right)
        self.led_canvas = ctk.CTkCanvas(self.top_frame, width=20, height=20, bg="#4169E1", highlightthickness=0)
        self.led_id = self.led_canvas.create_oval(4, 4, 16, 16, fill="#330000", outline="#550000") # Off state
        self.led_canvas.pack(pady=(5, 0))
        
        # Label
        ctk.CTkLabel(self.top_frame, text="CHECK", font=("Arial", 10, "bold"), text_color="white").pack()
        
        # Knobs Container
        self.knob_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.knob_frame.pack(pady=20)
        
        # Rate Knob
        self.create_knob(self.knob_frame, "RATE", self.config.get("rate_register", 60))
        
        # Spacer
        ctk.CTkLabel(self.knob_frame, text="   ").pack(side="left")
        
        # Depth Knob
        self.create_knob(self.knob_frame, "DEPTH", self.config.get("depth_register", 61))

        # Title
        ctk.CTkLabel(self, text="dsPIC33A Chorus", font=("Impact", 24), text_color="black").pack(pady=(0, 20))

        # 2. Bottom Section (Foot Switch)
        self.switch_frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=10, height=200) # Rubber pad area
        self.switch_frame.pack(fill="x", padx=20, pady=20, side="bottom")
        self.switch_frame.pack_propagate(False) # Maintain height
        
        # Actual Button (Invisible/Overlay or Styled)
        # We make a large button that looks like the pedal plate
        self.pedal_btn = ctk.CTkButton(
            self.switch_frame,
            text="",
            fg_color="#222222", # Dark rubber/metal
            hover_color="#333333",
            height=180,
            width=300,
            corner_radius=5,
            command=self.toggle_power
        )
        self.pedal_btn.pack(expand=True, fill="both", padx=5, pady=5)
        
        # Label on pedal
        self.pedal_label = ctk.CTkLabel(self.switch_frame, text="Audio Control", font=("Arial", 14, "bold"), text_color="#555555", bg_color="#222222")
        self.pedal_label.place(relx=0.5, rely=0.8, anchor="center")
        # Pass click through label to button (tricky in tkinter, usually bind to command)
        self.pedal_label.bind("<Button-1>", lambda e: self.toggle_power())

    def create_knob(self, parent, label, reg):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(side="left", padx=15)
        
        # Use our Utils Rotary Knob
        # Note: We need a unique write scheduler per knob to avoid conflict?
        # Or we can just use a dictionary to track pending writes.
        # Let's attach the pending flag to the knob object or use a helper class.
        # Actually, using a simple closure/method with tracking is fine.
        
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
                    # Access lock via app master
                    lock = getattr(self.master, 'modbus_lock', None)
                    if lock:
                        with lock:
                            self.client.write_register(address=helper["reg"], value=helper["value"], slave=1)
                except Exception as e:
                    print(f"Chorus Knob Write Error: {e}")
            helper["write_pending"] = False

        knob = RotaryKnob(frame, width=70, height=70, start_val=32767, command=on_change, bg_color="#4169E1")
        knob.pack()
        
        ctk.CTkLabel(frame, text=label, font=("Arial", 12, "bold"), text_color="white").pack(pady=(5, 0))
        
        # Store for sync
        self.knobs.append({"knob": knob, "reg": reg})

    def on_knob_change(self, value, reg):
        # Deprecated by local closure above
        pass

    def _write_knob(self, reg, val):
         # Deprecated
         pass

    def _update_power_ui(self):
        # Override Base Effect UI update to use our custom LED
        if self.power_state:
            self.led_canvas.itemconfig(self.led_id, fill="#ff0000", outline="#ff3333") # Red ON
        else:
            self.led_canvas.itemconfig(self.led_id, fill="#330000", outline="#550000") # Dark OFF

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
                    print(f"Read Error Chorus {item['reg']}: {e}")
            self.after(500, lambda: setattr(self, 'updating_from_device', False))
        except Exception as e:
            self.updating_from_device = False
