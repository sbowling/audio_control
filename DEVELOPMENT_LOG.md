# Audio Control Project - Development Log

## Project Overview
A Python GUI application for controlling audio effects via Modbus RTU. Designed to look like professional audio equipment (Graphic EQ, Parametric EQ, Chorus, etc.) and communicate with hardware over a USB COM port.

## Features
- **Modbus RTU Communication:** 115200,N,8,1 baud rate.
- **Multi-Effect System:** Main hub launches individual effect control panels.
- **Shared Power Control:** Effects share a common power register (125) with unique bits.
- **Synchronization:** Effect GUIs sync with hardware state on connection/power-on.
- **Thread Safety:** Uses locking mechanism to prevent serial port conflicts.

## File Structure
```
audio_control/
├── main.py                 # Main application hub
├── requirements.txt        # Dependencies
├── configs/                # JSON Configuration files
│   ├── graphic_eq.json
│   ├── parametric_eq.json
│   ├── chorus.json
│   ├── phaser.json
│   ├── wah.json
│   ├── echo.json
│   ├── flanger.json
│   └── reverb.json
└── effects/                # Effect modules
    ├── base_effect.py      # Parent class for all effects
    ├── graphic_eq.py       # Full Graphic EQ implementation
    ├── parametric_eq.py    # Stereo Parametric EQ with knobs
    ├── chorus.py           # Stompbox style Chorus
    ├── utils.py            # Shared UI utilities (Knobs)
    └── other_effects.py    # Placeholders for other effects
```

## Dependencies
- customtkinter
- pymodbus
- pyserial

## Configuration Format
Each effect has a JSON config file defining:
- `name`: Display name
- `power_register`: Register for power (usually 125)
- `power_bit`: Unique bit for this effect (0-7)
- Effect-specific registers (e.g., `left_channel_registers`, `rate_register`, etc.)

## Usage
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python main.py
   ```
3. Select COM port and click **CONNECT**.
4. Click effect buttons to launch control panels.

## Hardware Mapping (Example)
- **Register 125, Bit 0:** Graphic EQ Power
- **Register 125, Bit 1:** Parametric EQ Power
- **Register 125, Bit 2:** Phaser Power
- **Register 125, Bit 3:** Wah Power
- **Register 125, Bit 4:** Echo Power
- **Register 125, Bit 5:** Chorus Power
- **Register 125, Bit 6:** Flanger Power
- **Register 125, Bit 7:** Reverb Power

## Known Implementations
1. **Graphic EQ:**
   - 10-band stereo (31.5Hz - 16kHz).
   - Sliders output 0-65535 (mapped -1.00 to +1.00 display).
   - EQ Reset button centers all bands.

2. **Parametric EQ:**
   - Stereo (Left/Right).
   - 3-band per channel (High, Mid, Low).
   - Knobs for Gain, Frequency, Q.
   - Custom rotary knob UI.

3. **Chorus:**
   - Stompbox design.
   - Knobs: Rate, Depth.
   - Large foot-switch button for power.
   - Custom rotary knob UI.
