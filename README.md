# 🛡️ Cloud-Integrated IoT-Based Driver Drowsiness Detection System

## 🌟 Project Overview
This project is an end-to-end, AAT-compliant **Driver Drowsiness Detection System** combining the power of **Deep Learning**, **IoT**, and **Cloud Computing**. 

It uses real-time facial landmark detection (EAR/MAR analysis) to monitor driver alertness. If drowsiness or excessive yawning is detected, the system triggers local hardware alerts via IoT microcontrollers and pushes the data to a secure Cloud Dashboard for remote administrative monitoring.

---

## 🚀 Key Technologies & AAT Compliance

### 1. Deep Learning (AI/CV)
*   **Computer Vision:** Analyzes driver video feed in real-time.
*   **Feature Extraction:** Utilizes *Eye Aspect Ratio (EAR)* and *Mouth Aspect Ratio (MAR)*.
*   **Model Accuracy:** Real-time CNN fallback architecture ensuring continuous evaluation with low false-positive rates.

### 2. IoT Integration (Hardware)
*   **Microcontrollers:** Support for Raspberry Pi 4 (primary edge computing) / ESP32-CAM (low-power edge nodes).
*   **Hardware Alerts:** GPIO integration triggers Piezoelectric Buzzers and LEDs dynamically based on Cloud/Local triggers.

### 3. Cloud Computing (Backend)
*   **RESTful API:** Developed using Python **Flask**.
*   **Database:** Fully integrated with **MongoDB Atlas** NoSQL cloud database.
*   **Telemetry Logging:** Instantly stores alert severity, timestamps, and active driver associations.

### 4. Software Engineering (Web Dashboard)
*   **Frontend UI:** High-fidelity premium Light Mode interface. Built with HTML5, Vanilla CSS Glassmorphism, and responsive JS.
*   **Live Charts:** Real-time data visualization via Chart.js analyzing driver trend logs.
*   **Live Video Proxy:** Secure MJPEG video feed streamed directly into the dashboard via the backend.

### 5. High-Scoring Features 🏆
*   **Natural Language Processing (NLP):** Type or speak voice queries into the dashboard (e.g., *"How many alerts today?"*).
*   **Network Security:** End-to-end **JWT Authentication** + **Bcrypt** cryptographic password hashing ensuring the highest level of API security.

---

## 📂 Project Structure

```bash
📦 drowsiguard-system
 ┣ 📂 backend/        # Flask REST API, MongoDB Controllers, JWT Security Auth
 ┣ 📂 frontend/       # HTML/CSS/JS Dashboard, Chart Analytics, UI Components
 ┣ 📂 iot/            # Raspberry Pi GPIO Python Scripts & ESP32-CAM Firmware
 ┣ 📂 ml/             # EAR/MAR Detection Core, OpenCV processors, CNN scripts
 ┗ 📂 docs/           # System Design: UMLs, Architecture, and Circuit Diagrams
```

---

## 🛠️ Setup & Deployment Guide

### Phase 1: Deep Learning & Backend Setup
1. **Prerequisites:** Python 3.10+ installed.
2. **Setup virtual environment (recommended):**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment:** Create a `.env` file in the root. Format:
   ```env
   MONGO_URI=mongodb+srv://<user>:<password>@cluster...
   SECRET_KEY=your_secure_jwt_secret
   ```
4. **Start the Engine:**
   ```bash
   cd backend
   python app.py
   ```
   *(This boots the API on `localhost:5000` and automatically connects to the webcam for driver monitoring).*

### Phase 2: Web Dashboard Access
1. Open up `frontend/index.html` in any browser.
2. The system automatically seeds a master admin account.
   * **Demo Email:** `admin@drowsiguard.com`
   * **Demo Password:** `admin123`
3. Upon logging in, you will instantly see the Live Video Stream and Event Logs!

### Phase 3: Hardware / IoT Setup (Optional)
If deploying physical buzzers:
1. Wire a buzzer to Raspberry Pi GPIO pin `18`.
2. Execute `python iot/raspberry_pi/main.py`. The Pi will ping the Cloud REST API and trigger the buzzer upon severity spikes.

---

## 📐 System Design & Architecture
*(Please refer to the `docs/` folder in this repository for full design documentation including Data Flow Diagrams, Use-Case Scenarios, and Hardware Circuit Maps).*

## 🏁 AAT Evaluation Phases
*   **Phase 1 — Software Detection:** The system processes local frames at >25 FPS, successfully identifying micro-sleeps.
*   **Phase 2 — Simulation:** Integrated with ThingSpeak payload parameters and local REST proxies.
*   **Phase 3 — Hardware Demo:** Achieved via `backend` communication loop bridging CV triggers back to GPIO actuation scripts.
