import customtkinter as ctk
import math
import threading
from .base_effect import EffectBase

class RotaryKnob(ctk.CTkCanvas):
    def __init__(self, master, width=60, height=60, min_val=0, max_val=65535, start_val=32767, command=None, bg_color="#2b2b2b", **kwargs):
        # Note: Canvas cannot be truly transparent on all platforms. 
        # We match the background color of the parent container (#2b2b2b used in sections).
        super().__init__(master, width=width, height=height, bg=bg_color, highlightthickness=0, **kwargs)
        
        self.min_val = min_val
        self.max_val = max_val
        self.value = start_val
        self.command = command
        
        self.cx = width / 2
        self.cy = height / 2
        self.radius = min(width, height) / 2 - 5
        
        self.bind("<Button-1>", self.start_drag)
        self.bind("<B1-Motion>", self.drag)
        self.last_y = 0
        
        self.draw()

    def start_drag(self, event):
        self.last_y = event.y

    def drag(self, event):
        dy = self.last_y - event.y # Drag up increases value
        self.last_y = event.y
        
        # Sensitivity
        step = (self.max_val - self.min_val) / 200 # 200 pixels for full range
        delta = dy * step
        
        new_val = self.value + delta
        new_val = max(self.min_val, min(self.max_val, new_val))
        
        if new_val != self.value:
            self.value = new_val
            self.draw()
            if self.command:
                self.command(self.value)

    def set(self, value):
        self.value = max(self.min_val, min(self.max_val, value))
        self.draw()

    def get(self):
        return self.value

    def draw(self):
        self.delete("all")
        
        # Background Circle
        self.create_oval(
            self.cx - self.radius, self.cy - self.radius,
            self.cx + self.radius, self.cy + self.radius,
            fill="#333333", outline="#555555", width=2
        )
        
        fraction = (self.value - self.min_val) / (self.max_val - self.min_val)
        
        # Visual mapping: 
        # Start at ~135 degrees (Bottom Left)
        # End at ~405 degrees (Bottom Right)
        # 0 value -> 135 deg
        # 1 value -> 405 deg
        
        # Tkinter create_arc uses degrees counter-clockwise from 3 o'clock (0).
        # 0 deg (canvas) = 3 o'clock
        # 90 deg = 12 o'clock (Up)
        # 180 deg = 9 o'clock (Left)
        # 270 deg = 6 o'clock (Down)
        
        # Start (Bottom Left): ~225 deg
        # End (Bottom Right): ~315 deg (going clockwise means -45 deg or 315)
        # Total span: 270 degrees (leaving 90 gap at bottom)
        
        start_angle = 225
        span = -270 # Clockwise
        
        current_angle = start_angle + (fraction * span)
        rad = math.radians(current_angle)
        
        # Line end point
        # x = cx + r * cos(a)
        # y = cy - r * sin(a) (minus because y is up in math, down in screen)
        
        ix = self.cx + (self.radius * 0.8) * math.cos(rad)
        iy = self.cy - (self.radius * 0.8) * math.sin(rad)
        
        self.create_line(self.cx, self.cy, ix, iy, fill="#00ff00", width=3, capstyle="round")

class KnobFrame(ctk.CTkFrame):
    def __init__(self, master, label, register, app_instance, start_val=32767, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.register = register
        self.app = app_instance
        self.value = start_val
        
        # Get background color from parent (or assume #2b2b2b based on ParametricEQ theme)
        self.knob = RotaryKnob(self, width=60, height=60, start_val=start_val, command=self.on_change, bg_color="#2b2b2b")
        self.knob.pack(pady=5)
        
        self.label = ctk.CTkLabel(self, text=label, font=("Arial", 10, "bold"))
        self.label.pack()
        
        self.val_label = ctk.CTkLabel(self, text="0.00", font=("Consolas", 10), text_color="#aaaaaa")
        self.val_label.pack()
        
        self.write_pending = False
        
        # Init label
        self.update_label(start_val)

    def on_change(self, value):
        if self.app.updating_from_device:
            self.value = int(value)
            self.update_label(self.value)
            return

        self.value = int(value)
        self.update_label(self.value)
        
        if not self.write_pending:
            self.write_pending = True
            self.after(100, self.process_write)

    def update_label(self, val):
        norm = (val - 32768) / 32768.0
        self.val_label.configure(text=f"{norm:.2f}")

    def set_value(self, val):
        self.value = int(val)
        self.knob.set(self.value)
        self.update_label(self.value)

    def process_write(self):
        if self.app.client and self.app.client.connected and self.app.power_state and not self.app.updating_from_device:
            try:
                # Use lock from app (EffectBase master)
                # KnobFrame.app_instance is ParametricEQ, ParametricEQ.master is AudioControlApp
                with self.app.master.modbus_lock:
                    self.app.client.write_register(address=self.register, value=self.value, slave=1)
            except Exception as e:
                print(f"Knob Write Error {self.register}: {e}")
        self.write_pending = False

class ParametricEQ(EffectBase):
    def __init__(self, master, client, config_file="configs/parametric_eq.json"):
        super().__init__(master, client, config_file)
        self.geometry("900x600")
        self.updating_from_device = False
        self.knobs = []
        
        # Reset Button
        self.reset_btn = ctk.CTkButton(self.header_frame, text="EQ RESET", width=80, command=self.reset_eq, fg_color="#333333")
        self.reset_btn.grid(row=0, column=1, padx=5)

        # Main Layout: 2 Channels (Left, Right)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # --- Left Channel ---
        self.left_frame = ctk.CTkFrame(self.content_frame, fg_color="#222222", corner_radius=10)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.left_frame, text="LEFT CHANNEL", font=("Arial", 16, "bold"), text_color="#888888").pack(pady=10)
        
        self.build_channel_strip(self.left_frame, self.config.get("left_channel", {}))

        # --- Right Channel ---
        self.right_frame = ctk.CTkFrame(self.content_frame, fg_color="#222222", corner_radius=10)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.right_frame, text="RIGHT CHANNEL", font=("Arial", 16, "bold"), text_color="#888888").pack(pady=10)
        
        self.build_channel_strip(self.right_frame, self.config.get("right_channel", {}))

    def build_channel_strip(self, parent, config):
        # High Section (Top)
        high_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=5)
        high_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(high_frame, text="HIGH SHELF", font=("Arial", 12, "bold"), text_color="#aaaaaa").pack(pady=5)
        
        hf_knobs = ctk.CTkFrame(high_frame, fg_color="transparent")
        hf_knobs.pack(pady=5)
        self.create_knob(hf_knobs, "GAIN", config.get("high_section", {}).get("gain_reg", 0))
        self.create_knob(hf_knobs, "FREQ", config.get("high_section", {}).get("freq_reg", 0))

        # Mid Section (Middle)
        mid_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=5)
        mid_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(mid_frame, text="MID PEAK", font=("Arial", 12, "bold"), text_color="#aaaaaa").pack(pady=5)
        
        mf_knobs = ctk.CTkFrame(mid_frame, fg_color="transparent")
        mf_knobs.pack(pady=5)
        self.create_knob(mf_knobs, "GAIN", config.get("mid_section", {}).get("gain_reg", 0))
        self.create_knob(mf_knobs, "FREQ", config.get("mid_section", {}).get("freq_reg", 0))
        self.create_knob(mf_knobs, "Q", config.get("mid_section", {}).get("q_reg", 0))

        # Low Section (Bottom)
        low_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=5)
        low_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(low_frame, text="LOW SHELF", font=("Arial", 12, "bold"), text_color="#aaaaaa").pack(pady=5)
        
        lf_knobs = ctk.CTkFrame(low_frame, fg_color="transparent")
        lf_knobs.pack(pady=5)
        self.create_knob(lf_knobs, "GAIN", config.get("low_section", {}).get("gain_reg", 0))
        self.create_knob(lf_knobs, "FREQ", config.get("low_section", {}).get("freq_reg", 0))

    def create_knob(self, parent, label, reg):
        # Default middle value (32767)
        k = KnobFrame(parent, label, reg, self, start_val=32767)
        k.pack(side="left", padx=10)
        self.knobs.append(k)

    def reset_eq(self):
        center_val = 32767
        # Direct set and label update
        # We also want to write to Modbus
        for k in self.knobs:
            k.set_value(center_val)
            # set_value doesn't trigger write automatically in my implementation above (it just sets visual)
            # Let's trigger write manually or use on_change
            k.on_change(center_val)

    def on_power_on(self):
        self._sync_knobs()

    def _sync_knobs(self):
        if not self.client: return
        self.updating_from_device = True
        threading.Thread(target=self._read_and_update_knobs, daemon=True).start()

    def _read_and_update_knobs(self):
        try:
            for k in self.knobs:
                if not self.client: break
                try:
                    with self.master.modbus_lock:
                        rr = self.client.read_holding_registers(address=k.register, count=1, slave=1)
                    if not rr.isError():
                        val = rr.registers[0]
                        self.after(0, lambda knob=k, v=val: self._update_knob_ui(knob, v))
                except Exception as e:
                    print(f"Read Error {k.register}: {e}")
            self.after(500, lambda: setattr(self, 'updating_from_device', False))
        except Exception as e:
            self.updating_from_device = False

    def _update_knob_ui(self, knob, value):
        self.updating_from_device = True
        knob.set_value(value)
