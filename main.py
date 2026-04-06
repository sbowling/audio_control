import customtkinter as ctk
import serial.tools.list_ports
from pymodbus.client import ModbusSerialClient
from effects.graphic_eq import GraphicEQ
from effects.parametric_eq import ParametricEQ
from effects.chorus import Chorus
from effects.flanger import Flanger
from effects.phaser import Phaser
from effects.wah import Wah
from effects.reverb import Reverb
from effects.echo import Echo
from effects.mixer import Mixer
import os
import threading

class CPUBarGraph(ctk.CTkFrame):
    def __init__(self, master, register_addr, app_instance, **kwargs):
        super().__init__(master, **kwargs)
        self.register_addr = register_addr
        self.app = app_instance
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Label
        ctk.CTkLabel(self, text="CPU LOAD", font=("Arial", 12, "bold"), text_color="#aaaaaa").grid(row=0, column=0, pady=(5, 0))
        
        # Bar Canvas
        self.bar_canvas = ctk.CTkCanvas(self, width=400, height=30, bg="#222222", highlightthickness=0)
        self.bar_canvas.grid(row=1, column=0, padx=10, pady=5)
        
        # Draw empty bar background
        self.bar_id = self.bar_canvas.create_rectangle(5, 5, 395, 25, fill="#333333", outline="#555555")
        self.fill_id = self.bar_canvas.create_rectangle(5, 5, 5, 25, fill="#00ff00", outline="")
        
        # Percentage Label
        self.pct_label = ctk.CTkLabel(self, text="0%", font=("Consolas", 14, "bold"), text_color="#00ff00")
        self.pct_label.grid(row=1, column=1, padx=10)
        
        self.polling = True
        self.poll()

    def poll(self):
        if not self.polling:
            return
        
        if self.app.connected and self.app.client:
            threading.Thread(target=self._read_cpu, daemon=True).start()
        
        self.after(1000, self.poll) # Poll every 1000ms (1 second)

    def _read_cpu(self):
        try:
            with self.app.modbus_lock:
                rr = self.app.client.read_holding_registers(address=self.register_addr, count=1, slave=1)
            
            if not rr.isError():
                val = rr.registers[0]
                # 65535 = 100%
                pct = (val / 65535.0) * 100.0
                pct = min(100.0, pct) # Cap at 100%
                self.after(0, lambda p=pct: self.update_bar(p))
        except Exception as e:
            print(f"CPU Read Error: {e}")

    def update_bar(self, pct):
        # Map 0-100 to bar width (5 to 395)
        width = 5 + (pct / 100.0) * 390
        self.bar_canvas.coords(self.fill_id, 5, 5, width, 25)
        self.pct_label.configure(text=f"{pct:.0f}%")
        
        # Change color based on load
        if pct > 80:
            color = "#ff0000" # Red for high
        elif pct > 50:
            color = "#ffff00" # Yellow for medium
        else:
            color = "#00ff00" # Green for low
        self.bar_canvas.itemconfig(self.fill_id, fill=color)
        self.pct_label.configure(text_color=color)


class AudioControlApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Audio Control Center")
        self.geometry("600x600")
        ctk.set_appearance_mode("Dark")
        
        self.client = None
        self.connected = False
        self.modbus_lock = threading.Lock()
        self.effect_windows = {}
        
        # --- Connection Bar ---
        self.conn_frame = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#1a1a1a")
        self.conn_frame.pack(side="top", fill="x")
        
        self.title_label = ctk.CTkLabel(self.conn_frame, text="AUDIO CONTROL CENTER", font=("Impact", 20), text_color="#aaaaaa")
        self.title_label.pack(side="left", padx=20)
        
        self.connect_btn = ctk.CTkButton(self.conn_frame, text="CONNECT", width=100, command=self.toggle_connection, fg_color="#333333")
        self.connect_btn.pack(side="right", padx=10, pady=15)
        
        self.refresh_btn = ctk.CTkButton(self.conn_frame, text="↻", width=30, command=self.refresh_ports)
        self.refresh_btn.pack(side="right", padx=5, pady=15)
        
        self.port_combo = ctk.CTkComboBox(self.conn_frame, values=self.get_com_ports(), width=100)
        self.port_combo.pack(side="right", padx=10, pady=15)
        
        # --- Effects Grid ---
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # List of effects: Name, Class, Config Path
        self.effects_data = [
            ("Graphic EQ", GraphicEQ, "configs/graphic_eq.json"),
            ("Parametric EQ", ParametricEQ, "configs/parametric_eq.json"),
            ("Phaser", Phaser, "configs/phaser.json"),
            ("Wah", Wah, "configs/wah.json"),
            ("Echo", Echo, "configs/echo.json"),
            ("Chorus", Chorus, "configs/chorus.json"),
            ("Flanger", Flanger, "configs/flanger.json"),
            ("Reverb", Reverb, "configs/reverb.json"),
            ("Mixer", Mixer, "configs/mixer.json"),
        ]
        
        # Grid logic
        self.grid_frame.grid_columnconfigure(0, weight=1)
        self.grid_frame.grid_columnconfigure(1, weight=1)
        self.grid_frame.grid_columnconfigure(2, weight=1)
        
        for i, (name, cls, config) in enumerate(self.effects_data):
            row = i // 3
            col = i % 3
            
            btn = ctk.CTkButton(
                self.grid_frame, 
                text=name, 
                font=("Arial", 14, "bold"),
                height=60,
                corner_radius=10,
                command=lambda n=name, c=cls, cfg=config: self.open_effect(n, c, cfg)
            )
            btn.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        # --- CPU Load Bar Graph ---
        self.cpu_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=0)
        self.cpu_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 10))
        
        self.cpu_bar = CPUBarGraph(self.cpu_frame, register_addr=124, app_instance=self, fg_color="#1a1a1a")
        self.cpu_bar.pack(pady=5)

    def get_com_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports] if ports else ["No Ports"]

    def refresh_ports(self):
        self.port_combo.configure(values=self.get_com_ports())
        self.port_combo.set(self.get_com_ports()[0])

    def toggle_connection(self):
        if self.connected:
            self.disconnect()
        else:
            self.connect()

    def disconnect(self):
        if self.client:
            self.client.close()
        self.connected = False
        self.client = None
        self.connect_btn.configure(text="CONNECT", fg_color="#333333")
        self.port_combo.configure(state="normal")
        
        # Propagate disconnection to open windows
        for win in self.effect_windows.values():
            if win.winfo_exists():
                win.client = None
                win.power_state = False
                win._update_power_ui()

    def connect(self):
        port = self.port_combo.get()
        if not port or port == "No Ports": return
        
        try:
            self.client = ModbusSerialClient(
                port=port, baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=1
            )
            if self.client.connect():
                self.connected = True
                self.connect_btn.configure(text="CONNECTED", fg_color="green")
                self.port_combo.configure(state="disabled")
                
                # Propagate connection to open windows
                for win in self.effect_windows.values():
                    if win.winfo_exists():
                        win.client = self.client
                        win._sync_power_state()
            else:
                print("Connection failed")
                self.client = None
        except Exception as e:
            print(f"Connection Error: {e}")
            self.client = None

    def open_effect(self, name, effect_class, config_path):
        # Check if window exists
        if name in self.effect_windows:
            win = self.effect_windows[name]
            if win.winfo_exists():
                win.focus()
                return
            else:
                # Cleanup if closed
                del self.effect_windows[name]
        
        # Create new window
        # Pass shared client
        win = effect_class(self, self.client, config_path)
        self.effect_windows[name] = win

if __name__ == "__main__":
    app = AudioControlApp()
    app.mainloop()
