# Simulation Guide

## Phase 2: ThingSpeak & Tinkercad Simulation

This guide covers the simulation phase, demonstrating the sensor-to-cloud-to-dashboard data flow without requiring physical hardware.

---

## Part A: ThingSpeak Cloud Simulation

### Step 1: Create ThingSpeak Account
1. Go to [thingspeak.com](https://thingspeak.com) and sign up (free)
2. Click **"New Channel"**
3. Fill in:
   - **Name**: DrowsiGuard IoT Channel
   - **Description**: Driver Drowsiness Detection Sensor Data
   - **Field 1**: EAR (Eye Aspect Ratio)
   - **Field 2**: MAR (Mouth Aspect Ratio)
   - **Field 3**: Drowsiness Status
   - **Field 4**: Blink Count
   - **Field 5**: Yawn Count
   - **Field 6**: Session Duration
4. Click **Save Channel**

### Step 2: Get API Keys
1. Go to your channel → **API Keys** tab
2. Copy the **Write API Key**
3. Copy the **Read API Key**
4. Note the **Channel ID** from the URL

### Step 3: Configure Environment
```bash
# Edit .env file
THINGSPEAK_API_KEY=YOUR_WRITE_API_KEY
THINGSPEAK_CHANNEL_ID=YOUR_CHANNEL_ID
THINGSPEAK_READ_API_KEY=YOUR_READ_API_KEY
```

### Step 4: Run Simulation
```bash
# Run simulation for 5 minutes
cd iot/simulation
python thingspeak_sim.py --duration 300

# Or run without cloud (console output only)
python thingspeak_sim.py --duration 60
```

### Step 5: View Data on ThingSpeak
1. Go to your ThingSpeak channel page
2. You'll see real-time charts updating for each field
3. ThingSpeak automatically generates:
   - Line charts for EAR/MAR values
   - Status indicators for drowsiness state
   - Historical data visualization

### Step 6: Read Data Back
```bash
# Read latest 10 entries from channel
python thingspeak_sim.py --read
```

### Expected Output
```
  DROWSINESS IoT SIMULATION
  Duration: 300s | Interval: 16s
  Cloud: ThingSpeak

    # |     Time |    EAR |    MAR |   Status | Blinks | Yawns |  Cloud
  ---+----------+--------+--------+----------+--------+-------+-------
    1 |    16.0s |  0.312 |  0.345 |    ALERT |      1 |     0 |    #1
    2 |    32.0s |  0.285 |  0.401 |    ALERT |      1 |     0 |    #2
    3 |    48.0s |  0.156 |  0.812 |   DROWSY |      2 |     1 |    #3
    4 |    64.0s |  0.298 |  0.289 |    ALERT |      3 |     1 |    #4
    ...
```

---

## Part B: Tinkercad Circuit Simulation

### Step 1: Open Tinkercad
1. Go to [tinkercad.com](https://www.tinkercad.com) and sign in
2. Click **Circuits** → **Create new Circuit**

### Step 2: Build the Circuit
1. Add components from the right panel:
   - **Arduino Uno** (simulating Raspberry Pi)
   - **Piezo Buzzer**
   - **Red LED**
   - **Green LED**
   - **2x 220Ω Resistors**
   - **Breadboard**

2. Wire connections:
   | Component | Arduino Pin |
   |-----------|-------------|
   | Buzzer (+) | Digital Pin 8 |
   | Buzzer (-) | GND |
   | Red LED (anode) | Digital Pin 9 (via 220Ω) |
   | Red LED (cathode) | GND |
   | Green LED (anode) | Digital Pin 10 (via 220Ω) |
   | Green LED (cathode) | GND |

### Step 3: Arduino Code for Tinkercad
```cpp
// DrowsiGuard Tinkercad Simulation
// Simulates drowsiness detection alert system

const int BUZZER_PIN = 8;
const int RED_LED = 9;
const int GREEN_LED = 10;

int drowsinessLevel = 0;
bool isDrowsy = false;

void setup() {
    Serial.begin(9600);
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(RED_LED, OUTPUT);
    pinMode(GREEN_LED, OUTPUT);

    // Start with green LED (driver alert)
    digitalWrite(GREEN_LED, HIGH);
    Serial.println("DrowsiGuard System Started");
}

void loop() {
    // Simulate EAR values (random for demo)
    float ear = random(10, 40) / 100.0;

    if (ear < 0.22) {
        drowsinessLevel++;
    } else {
        drowsinessLevel = 0;
        isDrowsy = false;
    }

    // Trigger alert after sustained low EAR
    if (drowsinessLevel > 5) {
        isDrowsy = true;
        triggerAlert();
    } else {
        normalState();
    }

    Serial.print("EAR: ");
    Serial.print(ear);
    Serial.print(" | Status: ");
    Serial.println(isDrowsy ? "DROWSY!" : "Alert");

    delay(1000);
}

void triggerAlert() {
    digitalWrite(GREEN_LED, LOW);
    digitalWrite(RED_LED, HIGH);
    tone(BUZZER_PIN, 1000, 500);
    delay(500);
    digitalWrite(RED_LED, LOW);
    delay(500);
}

void normalState() {
    digitalWrite(GREEN_LED, HIGH);
    digitalWrite(RED_LED, LOW);
    noTone(BUZZER_PIN);
}
```

### Step 4: Run Simulation
1. Paste the code in Tinkercad's code editor
2. Click **Start Simulation**
3. Observe:
   - Green LED stays ON when driver is alert
   - Red LED blinks and buzzer sounds when drowsiness detected
   - Serial Monitor shows EAR values and status

---

## Simulation Flow Summary

```
┌──────────────┐    ┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│  Simulated   │───▶│  ThingSpeak  │───▶│  Cloud Data  │───▶│  Dashboard   │
│  Sensor Data │    │  REST API    │    │  Storage     │    │  Visualization│
└──────────────┘    └─────────────┘    └──────────────┘    └──────────────┘
       ↑                                                          │
       │              ┌─────────────┐                            │
       └──────────────│  Tinkercad  │◀───────────────────────────┘
                      │  Circuit    │   (Visual hardware simulation)
                      └─────────────┘
```
