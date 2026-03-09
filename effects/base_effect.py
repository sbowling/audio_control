import customtkinter as ctk
import threading
import json
import os

class EffectBase(ctk.CTkToplevel):
    def __init__(self, master, client, config_file):
        super().__init__(master)
        self.client = client
        self.config_file = config_file
        self.config = self.load_config()
        self.power_state = False
        
        # Window setup
        self.title(self.config.get("name", "Audio Effect"))
        self.geometry("600x400")
        
        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Main content

        # Header Frame
        self.header_frame = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#1a1a1a")
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1) # Spacer

        # Title Label
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text=self.config.get("name", "Audio Effect").upper(), 
            font=("Impact", 20), 
            text_color="#555555"
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Power Section (Right)
        self.power_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.power_frame.grid(row=0, column=2, padx=20)
        
        # LED Canvas
        self.led_canvas = ctk.CTkCanvas(self.power_frame, width=20, height=20, bg="#1a1a1a", highlightthickness=0)
        self.led_id = self.led_canvas.create_oval(2, 2, 18, 18, fill="#330000", outline="#550000") # Off state
        self.led_canvas.pack(side="left", padx=5)
        
        # Power Button
        self.power_btn = ctk.CTkButton(
            self.power_frame, 
            text="POWER", 
            width=80, 
            height=30,
            corner_radius=15,
            fg_color="#333333",
            hover_color="#555555",
            command=self.toggle_power,
            font=("Arial", 12, "bold")
        )
        self.power_btn.pack(side="left", padx=5)
        
        # Content Frame (To be populated by subclasses)
        self.content_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=0)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        
        # Sync initial state
        self.after(500, self._sync_power_state)

    def load_config(self):
        try:
            with open(self.config_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config {self.config_file}: {e}")
            return {"name": "Unknown", "power_register": 125, "power_bit": 0}

    def _sync_power_state(self):
        if not self.client or not self.client.connected:
            return
            
        threading.Thread(target=self._read_power_thread, daemon=True).start()

    def _read_power_thread(self):
        try:
            reg_addr = self.config.get("power_register", 125)
            bit = self.config.get("power_bit", 0)
            
            with self.master.modbus_lock:
                rr = self.client.read_holding_registers(address=reg_addr, count=1, slave=1)
            
            if not rr.isError():
                current_val = rr.registers[0]
                is_on = (current_val & (1 << bit)) > 0
                
                if self.power_state != is_on:
                    self.power_state = is_on
                    self.after(0, self._update_power_ui)
                    
                    if self.power_state:
                        self.after(100, self.on_power_on) # Hook for subclasses

        except Exception as e:
            print(f"Sync Power Error ({self.config.get('name')}): {e}")

    def toggle_power(self):
        if not self.client or not self.client.connected:
            return
        threading.Thread(target=self._toggle_power_thread, daemon=True).start()

    def _toggle_power_thread(self):
        try:
            reg_addr = self.config.get("power_register", 125)
            bit = self.config.get("power_bit", 0)
            
            # Read-Modify-Write
            with self.master.modbus_lock:
                rr = self.client.read_holding_registers(address=reg_addr, count=1, slave=1)
                
                if not rr.isError():
                    current_val = rr.registers[0]
                    is_currently_on = (current_val & (1 << bit)) > 0
                    new_state = not is_currently_on
                    
                    if new_state:
                        new_val = current_val | (1 << bit)
                    else:
                        new_val = current_val & ~(1 << bit)
                    
                    self.client.write_register(address=reg_addr, value=new_val, slave=1)
                    
                    # Only update state if write was successful (no exception)
                    self.power_state = new_state
                    self.after(0, self._update_power_ui)
                    
                    if self.power_state:
                        self.after(100, self.on_power_on)
                else:
                    print(f"Read Error in Toggle: {rr}")
                    return

        except Exception as e:
            print(f"Toggle Power Error ({self.config.get('name')}): {e}")

    def _update_power_ui(self):
        if self.power_state:
            self.led_canvas.itemconfig(self.led_id, fill="#ff0000", outline="#ffcccc")
            self.power_btn.configure(fg_color="#550000")
        else:
            self.led_canvas.itemconfig(self.led_id, fill="#330000", outline="#550000")
            self.power_btn.configure(fg_color="#333333")

    def on_power_on(self):
        """Override in subclasses to handle sync logic when turned on"""
        pass
