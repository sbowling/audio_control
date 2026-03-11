import customtkinter as ctk
import threading
from .base_effect import EffectBase

class WahPedal(ctk.CTkCanvas):
    def __init__(self, master, width=300, height=400, min_val=0, max_val=65535, start_val=32767, command=None, bg_color="#444444", **kwargs):
        super().__init__(master, width=width, height=height, bg=bg_color, highlightthickness=0, **kwargs)
        
        self.min_val = min_val
        self.max_val = max_val
        self.value = start_val
        self.command = command
        
        # Pedal dimensions
        self.pedal_width = 120
        self.pedal_height = 20
        self.hinge_y = height - 50 # Where the pedal pivots
        self.pedal_x = width / 2
        
        # Bind mouse events
        self.bind("<Button-1>", self.start_drag)
        self.bind("<B1-Motion>", self.drag)
        self.last_y = 0
        
        self.draw()

    def start_drag(self, event):
        self.last_y = event.y

    def drag(self, event):
        dy = self.last_y - event.y
        self.last_y = event.y
        
        # Map vertical mouse movement to value
        # Up movement = increase value (heel down to toe down)
        step = (self.max_val - self.min_val) / 200
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
        
        # Background - subtle texture hint
        # Draw hinge point
        hinge_x = self.winfo_width() / 2
        hinge_y = self.winfo_height() - 50
        
        # Draw base/housing (trapezoid shape)
        self.create_polygon(
            50, self.winfo_height() - 20,
            self.winfo_width() - 50, self.winfo_height() - 20,
            self.winfo_width() - 80, hinge_y + 60,
            80, hinge_y + 60,
            fill="#222222", outline="#555555", width=2
        )
        
        # Calculate pedal angle based on value
        # 0 (bottom) = -30 degrees, 65535 (top) = +30 degrees
        fraction = (self.value - self.min_val) / (self.max_val - self.min_val)
        angle = -30 + (fraction * 60) # -30 to +30 degrees
        import math
        rad = math.radians(angle)
        
        # Pedal arm length
        arm_len = 180
        
        # Calculate pedal tip position
        # The pedal rotates around the hinge
        # Tip position calculation
        tip_x = hinge_x - arm_len * math.sin(rad)
        tip_y = hinge_y + arm_len * math.cos(rad)
        
        # Draw pedal arm
        self.create_line(hinge_x, hinge_y, tip_x, tip_y, fill="#888888", width=12, capstyle="round")
        
        # Draw pedal pad (treadle)
        # Calculate perpendicular angle for width
        perp_angle = rad + math.pi / 2
        pad_w = 50
        
        px1 = tip_x + pad_w * math.cos(perp_angle)
        py1 = tip_y + pad_w * math.sin(perp_angle)
        px2 = tip_x - pad_w * math.cos(perp_angle)
        py2 = tip_y - pad_w * math.sin(perp_angle)
        
        self.create_polygon(
            px1, py1, px2, py2,
            tip_x - 20 * math.cos(rad), tip_y - 20 * math.sin(rad),
            tip_x + 20 * math.cos(rad), tip_y + 20 * math.sin(rad),
            fill="#111111", outline="#666666", width=2
        )
        
        # Draw hinge circle
        self.create_oval(hinge_x-15, hinge_y-15, hinge_x+15, hinge_y+15, fill="#333333", outline="#666666", width=2)
        
        # Draw value indicator (arc)
        self.create_arc(20, self.winfo_height()-180, self.winfo_width()-20, self.winfo_height()-20, 
                        start=180, extent=int(fraction * 180), style="arc", outline="#00ff00", width=3)

class Wah(EffectBase):
    def __init__(self, master, client, config_file="configs/wah.json"):
        super().__init__(master, client, config_file)
        
        # --- Stompbox UI Setup ---
        self.geometry("350x550")
        self.configure(fg_color="#444444") # Dark Grey (Wah pedal color)
        self.resizable(False, False)
        
        # Hide standard header
        self.header_frame.destroy() 
        
        self.updating_from_device = False
        self.write_pending = False
        
        # --- Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Title
        self.grid_rowconfigure(1, weight=1) # Pedal
        self.grid_rowconfigure(2, weight=0) # LED
        self.grid_rowconfigure(3, weight=0) # Switch

        # Title
        ctk.CTkLabel(self, text="Wah", font=("Impact", 28), text_color="white").grid(row=0, column=0, pady=(10, 0))

        # Pedal Canvas
        self.pedal = WahPedal(self, width=300, height=350, start_val=32767, command=self.on_pedal_change, bg_color="#444444")
        self.pedal.grid(row=1, column=0, pady=10)

        # Value Label
        self.val_label = ctk.CTkLabel(self, text="0.00", font=("Consolas", 16), text_color="#00ff00")
        self.val_label.grid(row=1, column=0, pady=(20, 0))

        # LED Indicator
        self.led_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.led_frame.grid(row=2, column=0, pady=(5, 10))
        
        self.led_canvas = ctk.CTkCanvas(self.led_frame, width=20, height=20, bg="#444444", highlightthickness=0)
        self.led_id = self.led_canvas.create_oval(4, 4, 16, 16, fill="#330000", outline="#550000")
        self.led_canvas.pack()
        
        ctk.CTkLabel(self.led_frame, text="BYPASS", font=("Arial", 10, "bold"), text_color="white").pack()

        # Bottom Section (Foot Switch)
        self.switch_frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=10)
        self.switch_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="s")
        
        # Actual Button
        self.pedal_btn = ctk.CTkButton(
            self.switch_frame,
            text="BYPASS",
            fg_color="#222222",
            text_color="white",
            hover_color="#333333",
            height=60,
            width=200,
            corner_radius=5,
            command=self.toggle_power
        )
        self.pedal_btn.pack(expand=True)

    def on_pedal_change(self, value):
        if self.updating_from_device:
            self.update_label(int(value))
            return

        val = int(value)
        self.update_label(val)
        
        if not self.write_pending:
            self.write_pending = True
            self.after(50, self.process_write)

    def update_label(self, val):
        norm = (val - 32768) / 32768.0
        self.val_label.configure(text=f"{norm:.2f}")

    def process_write(self):
        if self.client and self.client.connected and self.power_state:
            try:
                reg = self.config.get("position_register", 90)
                lock = getattr(self.master, 'modbus_lock', None)
                if lock:
                    with lock:
                        self.client.write_register(address=reg, value=self.pedal.value, slave=1)
            except Exception as e:
                print(f"Wah Write Error: {e}")
        self.write_pending = False

    def _update_power_ui(self):
        if self.power_state:
            self.led_canvas.itemconfig(self.led_id, fill="#ff0000", outline="#ff3333")
        else:
            self.led_canvas.itemconfig(self.led_id, fill="#330000", outline="#550000")

    def on_power_on(self):
        self._sync_pedal()

    def _sync_pedal(self):
        if not self.client: return
        self.updating_from_device = True
        threading.Thread(target=self._read_and_update_pedal, daemon=True).start()

    def _read_and_update_pedal(self):
        try:
            reg = self.config.get("position_register", 90)
            with self.master.modbus_lock:
                rr = self.client.read_holding_registers(address=reg, count=1, slave=1)
            
            if not rr.isError():
                val = rr.registers[0]
                self.after(0, lambda v=val: self._update_pedal_ui(v))
            self.after(500, lambda: setattr(self, 'updating_from_device', False))
        except Exception as e:
            self.updating_from_device = False

    def _update_pedal_ui(self, value):
        self.updating_from_device = True
        self.pedal.set(value)
        self.update_label(value)
