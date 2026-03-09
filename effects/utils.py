import customtkinter as ctk
import math

class RotaryKnob(ctk.CTkCanvas):
    def __init__(self, master, width=60, height=60, min_val=0, max_val=65535, start_val=32767, command=None, bg_color="#2b2b2b", **kwargs):
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
        
        # Knob Body
        self.create_oval(
            self.cx - self.radius, self.cy - self.radius,
            self.cx + self.radius, self.cy + self.radius,
            fill="#111111", outline="#333333", width=2
        )
        
        # Indicator Line
        fraction = (self.value - self.min_val) / (self.max_val - self.min_val)
        
        # Visual mapping: 
        # Start (Bottom Left): ~225 deg
        # End (Bottom Right): ~315 deg (going clockwise means -45 deg or 315)
        # Total span: 270 degrees (leaving 90 gap at bottom)
        
        start_angle = 225
        span = -270 # Clockwise
        
        current_angle = start_angle + (fraction * span)
        rad = math.radians(current_angle)
        
        ix = self.cx + (self.radius * 0.8) * math.cos(rad)
        iy = self.cy - (self.radius * 0.8) * math.sin(rad)
        
        self.create_line(self.cx, self.cy, ix, iy, fill="#ffffff", width=3, capstyle="round")

class KnobFrame(ctk.CTkFrame):
    def __init__(self, master, label, register, app_instance, start_val=32767, text_color="black", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.register = register
        self.app = app_instance
        self.value = start_val
        
        # Allow passing bg_color for knob canvas if needed via kwargs or infer
        # We'll use the parent's fg_color if possible, or pass explicit
        bg = kwargs.get("bg_color", master.cget("fg_color"))
        if bg == "transparent": bg = "#3366cc" # Default fallback for chorus blue if transparent
        
        self.knob = RotaryKnob(self, width=60, height=60, start_val=start_val, command=self.on_change, bg_color=bg)
        self.knob.pack(pady=5)
        
        self.label = ctk.CTkLabel(self, text=label, font=("Arial", 12, "bold"), text_color=text_color)
        self.label.pack()
        
        # Optional: Value display
        # self.val_label = ctk.CTkLabel(self, text="0.00", font=("Consolas", 10), text_color=text_color)
        # self.val_label.pack()
        
        self.write_pending = False

    def on_change(self, value):
        if hasattr(self.app, 'updating_from_device') and self.app.updating_from_device:
            self.value = int(value)
            return

        self.value = int(value)
        
        if not self.write_pending:
            self.write_pending = True
            self.after(100, self.process_write)

    def set_value(self, val):
        self.value = int(val)
        self.knob.set(self.value)

    def process_write(self):
        if self.app.client and self.app.client.connected and self.app.power_state:
            try:
                # Use lock from app master
                lock = getattr(self.app.master, 'modbus_lock', None)
                if lock:
                    with lock:
                        self.app.client.write_register(address=self.register, value=self.value, slave=1)
                else:
                    self.app.client.write_register(address=self.register, value=self.value, slave=1)
            except Exception as e:
                print(f"Knob Write Error {self.register}: {e}")
        self.write_pending = False
