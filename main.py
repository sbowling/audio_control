import customtkinter as ctk
import serial.tools.list_ports
from pymodbus.client import ModbusSerialClient
from effects.graphic_eq import GraphicEQ
from effects.parametric_eq import ParametricEQ
from effects.chorus import Chorus
from effects.other_effects import Phaser, Wah, Echo, Flanger, Reverb
import os
import threading

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
        ]
        
        # Grid logic
        self.grid_frame.grid_columnconfigure(0, weight=1)
        self.grid_frame.grid_columnconfigure(1, weight=1)
        
        for i, (name, cls, config) in enumerate(self.effects_data):
            row = i // 2
            col = i % 2
            
            btn = ctk.CTkButton(
                self.grid_frame, 
                text=name, 
                font=("Arial", 16, "bold"),
                height=80,
                corner_radius=10,
                # Lambda capture requires explicit args or partial
                command=lambda n=name, c=cls, cfg=config: self.open_effect(n, c, cfg)
            )
            btn.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

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
