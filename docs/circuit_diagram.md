# Circuit Diagram & Hardware Guide

## GPIO Connection Diagram

```
Raspberry Pi 4 GPIO Header
═══════════════════════════════════════════════════

                    3V3  (1) (2)  5V ←──── Buzzer VCC
                  GPIO2  (3) (4)  5V
                  GPIO3  (5) (6)  GND ←─── Common GND
                  GPIO4  (7) (8)  GPIO14
                    GND  (9) (10) GPIO15
                 GPIO17 (11) (12) GPIO18
                 GPIO27 (13) (14) GND ←─── Buzzer GND
                 GPIO22 (15) (16) GPIO23 ←── Buzzer Signal
                    3V3 (17) (18) GPIO24 ←── Red LED (+)
                 GPIO10 (19) (20) GND ←──── Red LED (-)
                  GPIO9 (21) (22) GPIO25 ←── Green LED (+)
                 GPIO11 (23) (24) GPIO8
                    GND (25) (26) GPIO7
                  GPIO0 (27) (28) GPIO1
                  GPIO5 (29) (30) GND
                  GPIO6 (31) (32) GPIO12
                 GPIO13 (33) (34) GND
                 GPIO19 (35) (36) GPIO16
                 GPIO26 (37) (38) GPIO20
                    GND (39) (40) GPIO21

═══════════════════════════════════════════════════
```

## Component Connections

### 1. Active Buzzer Module
```
┌─────────────────┐
│  Active Buzzer   │
│    Module        │
│                  │
│  VCC ──────────── Pi Pin 2 (5V)
│  GND ──────────── Pi Pin 6 (GND)
│  SIG ──────────── Pi Pin 16 (GPIO 23)
│                  │
└─────────────────┘

Note: Active buzzer sounds when GPIO 23 is HIGH
```

### 2. Red LED (Danger Indicator)
```
┌──────────────┐
│   Red LED    │
│              │
│  Anode (+) ──── 220Ω Resistor ──── Pi Pin 18 (GPIO 24)
│  Cathode(-) ── Pi Pin 20 (GND)
│              │
└──────────────┘
```

### 3. Green LED (Status Indicator)
```
┌──────────────┐
│  Green LED   │
│              │
│  Anode (+) ──── 220Ω Resistor ──── Pi Pin 22 (GPIO 25)
│  Cathode(-) ── Pi Pin 20 (GND)
│              │
└──────────────┘
```

### 4. Camera Module
```
Option A: USB Webcam
    Simply plug into any USB port on the Pi

Option B: Pi Camera Module v2
    Connect ribbon cable to the CSI port on the Pi
    Enable camera: sudo raspi-config → Interface Options → Camera

Option C: ESP32-CAM (Network Camera)
    ESP32-CAM connects via WiFi
    Streams MJPEG to http://<esp32-ip>:81/stream
    Pi pulls stream over network
```

## Bill of Materials

| Component | Qty | Estimated Cost |
|-----------|-----|----------------|
| Raspberry Pi 4 (4GB) | 1 | $55 |
| USB Webcam / Pi Camera v2 | 1 | $10-25 |
| Active Buzzer Module | 1 | $2 |
| Red LED (5mm) | 1 | $0.10 |
| Green LED (5mm) | 1 | $0.10 |
| 220Ω Resistors | 2 | $0.10 |
| Breadboard | 1 | $3 |
| Jumper Wires (M-F) | 10 | $2 |
| MicroSD Card (32GB) | 1 | $8 |
| USB-C Power Supply (5V 3A) | 1 | $10 |
| **Total** | | **~$90-110** |

### Optional: ESP32-CAM Setup

| Component | Qty | Estimated Cost |
|-----------|-----|----------------|
| ESP32-CAM (AI-Thinker) | 1 | $8 |
| FTDI USB-to-Serial Adapter | 1 | $5 |
| 5V 2A Power Supply | 1 | $5 |
| **Total** | | **~$18** |

## ESP32-CAM Wiring (for programming)

```
ESP32-CAM          FTDI Adapter
═══════════        ═══════════
  5V      ────────── VCC (5V)
  GND     ────────── GND
  U0R     ────────── TX
  U0T     ────────── RX
  IO0     ────────── GND (during upload only!)

After upload, disconnect IO0 from GND and reset.
```

## Software Setup on Raspberry Pi

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install system dependencies
sudo apt install -y python3-pip python3-venv cmake
sudo apt install -y libatlas-base-dev libhdf5-dev
sudo apt install -y libopencv-dev python3-opencv

# 3. Enable camera (if using Pi Camera)
sudo raspi-config  # → Interface Options → Camera → Enable

# 4. Clone project and setup
cd /home/pi
git clone <repository-url> drowsiness-detection
cd drowsiness-detection

# 5. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 6. Install dependencies
pip install -r requirements.txt

# 7. Configure environment
cp .env.example .env
nano .env  # Edit with your MongoDB URI and API keys

# 8. Run the system
cd iot/raspberry_pi
python main.py --camera 0 --device-id RPi-CAM-001
```
