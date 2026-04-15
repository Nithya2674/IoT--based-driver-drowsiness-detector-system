# 🛡️ DrowsiGuard — Cloud-Integrated IoT-Based Driver Drowsiness Detection System

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.16-orange.svg)](https://tensorflow.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green.svg)](https://mongodb.com/atlas)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A real-time driver drowsiness detection system integrating **IoT**, **Deep Learning**, **Cloud Computing**, and **Software Engineering** principles. The system uses a camera to monitor the driver's face, detects drowsiness/yawning using Eye Aspect Ratio (EAR) and Mouth Aspect Ratio (MAR), triggers alerts, and logs events to a cloud-connected dashboard.

---

## 📋 Table of Contents

- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Setup & Installation](#-setup--installation)
- [Phase 1: Code-Based Demo](#-phase-1-code-based-demo)
- [Phase 2: Simulation](#-phase-2-simulation)
- [Phase 3: Hardware Integration](#-phase-3-hardware-integration)
- [API Documentation](#-api-documentation)
- [Optional Enhancements](#-optional-enhancements)
- [Testing](#-testing)
- [Documentation](#-documentation)

---

## ✨ Features

### Core Detection
- 🧠 **Real-time face detection** using MediaPipe FaceMesh (468 landmarks)
- 👁️ **Eye closure detection** via Eye Aspect Ratio (EAR)
- 🥱 **Yawn detection** via Mouth Aspect Ratio (MAR)
- 🤖 **CNN model** for eye state classification (TensorFlow/Keras)
- 📊 **Evaluation metrics**: Accuracy, Precision, Recall, F1-Score, ROC/PR curves

### IoT Integration
- 📷 Camera module support (USB webcam, Pi Camera, ESP32-CAM)
- 🔔 GPIO buzzer and LED alert system
- 📡 ESP32-CAM MJPEG streaming firmware
- 📶 Offline event queue with auto-retry

### Cloud Computing
- ☁️ MongoDB Atlas cloud database
- 🌐 Flask REST API with JWT authentication
- 📊 ThingSpeak IoT cloud simulation
- 🔄 Real-time data synchronization

### Web Dashboard
- 📊 Real-time monitoring with Chart.js visualizations
- 🔐 Role-based login (Admin/User)
- 🗣️ NLP voice/text query interface (Web Speech API)
- 📱 Mobile-responsive design with glassmorphism UI

### Security
- 🔒 JWT token authentication with expiry
- 🔑 bcrypt password hashing
- 🛡️ API key authentication for IoT devices
- 🚫 Rate limiting and input sanitization

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │  Login   │  │  Dashboard   │  │  Admin Panel       │    │
│  │  Page    │  │  (Charts,    │  │  (User Mgmt,       │    │
│  │          │  │   Events,    │  │   API Keys,        │    │
│  │          │  │   NLP Query) │  │   System Config)   │    │
│  └──────────┘  └──────────────┘  └────────────────────┘    │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API (JSON)
┌───────────────────────▼─────────────────────────────────────┐
│                      API LAYER                               │
│  ┌──────┐  ┌────────┐  ┌───────────┐  ┌──────┐  ┌──────┐  │
│  │ Auth │  │ Events │  │ Dashboard │  │ NLP  │  │Health│  │
│  │Routes│  │ CRUD   │  │ Aggregation│ │Query │  │Check │  │
│  └──────┘  └────────┘  └───────────┘  └──────┘  └──────┘  │
│  ┌─────────────────┐  ┌────────────────────────────┐       │
│  │ JWT Middleware   │  │ Security (bcrypt, API keys)│       │
│  └─────────────────┘  └────────────────────────────┘       │
└───────────────────────┬─────────────────────────────────────┘
                        │ PyMongo
┌───────────────────────▼─────────────────────────────────────┐
│                     DATA LAYER                               │
│  ┌──────────────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │  MongoDB Atlas   │  │  ThingSpeak  │  │ SQLite Queue │   │
│  │  (Cloud DB)      │  │  (IoT Cloud) │  │ (Offline)    │   │
│  └──────────────────┘  └─────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     EDGE LAYER (IoT)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Raspberry Pi│  │ Drowsiness   │  │ Alert System      │  │
│  │ + Camera    │──│ Detector     │──│ (Buzzer + LED)    │  │
│  │             │  │ (MediaPipe)  │  │ GPIO 23, 24, 25   │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
│  ┌─────────────┐                                            │
│  │ ESP32-CAM   │  MJPEG Stream over WiFi                    │
│  │ (Optional)  │                                            │
│  └─────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Deep Learning** | MediaPipe, TensorFlow/Keras, OpenCV | Face detection, EAR/MAR, CNN classification |
| **Backend** | Flask, PyMongo, Flask-JWT-Extended | REST API, authentication, cloud connectivity |
| **Database** | MongoDB Atlas | Cloud event storage |
| **Frontend** | HTML5, CSS3, JavaScript, Chart.js | Dashboard, admin panel, NLP interface |
| **IoT** | Raspberry Pi, ESP32-CAM, GPIO | Edge computing, camera capture, alerts |
| **Simulation** | ThingSpeak, Tinkercad | IoT data flow simulation |
| **Security** | JWT, bcrypt, HTTPS | Authentication, encryption |
| **NLP** | Web Speech API, keyword matching | Voice/text queries |

---

## 📁 Project Structure

```
drowsiness detection/
├── 📄 README.md                    # This file
├── 📄 requirements.txt             # Python dependencies
├── 📄 .env.example                 # Environment variable template
│
├── 🧠 ml/                          # Deep Learning Module
│   ├── detector.py                 # Main drowsiness detector (EAR + MediaPipe)
│   ├── cnn_model.py                # CNN model architecture
│   ├── train_cnn.py                # Training pipeline
│   ├── evaluate.py                 # Model evaluation & metrics
│   └── utils.py                    # ML utility functions
│
├── 🌐 backend/                      # Flask REST API
│   ├── app.py                      # Application factory
│   ├── config.py                   # Configuration management
│   ├── models/                     # Data models
│   │   ├── user.py                 # User model (RBAC)
│   │   └── event.py                # Drowsiness event model
│   ├── routes/                     # API endpoints
│   │   ├── auth.py                 # Authentication routes
│   │   ├── events.py               # Event CRUD routes
│   │   ├── dashboard.py            # Dashboard data routes
│   │   └── nlp.py                  # NLP query routes
│   ├── middleware/                  # Request middleware
│   │   └── auth_middleware.py      # JWT + RBAC decorators
│   └── utils/                      # Utility modules
│       ├── security.py             # Encryption, hashing
│       └── helpers.py              # Helper functions
│
├── 🎨 frontend/                     # Web Dashboard
│   ├── index.html                  # Login / Register page
│   ├── dashboard.html              # Monitoring dashboard
│   ├── admin.html                  # Admin panel
│   ├── css/styles.css              # Design system
│   └── js/
│       ├── app.js                  # Core utilities
│       ├── auth.js                 # Authentication
│       ├── dashboard.js            # Charts & data
│       ├── nlp.js                  # Voice query
│       └── admin.js                # Admin functions
│
├── 📡 iot/                          # IoT Module
│   ├── raspberry_pi/               # Raspberry Pi code
│   │   ├── main.py                 # Main entry point
│   │   ├── camera_module.py        # Camera abstraction
│   │   ├── buzzer_alert.py         # GPIO alert system
│   │   └── cloud_sender.py         # Cloud data sender
│   ├── esp32/
│   │   └── camera_stream.ino       # ESP32-CAM firmware
│   └── simulation/
│       └── thingspeak_sim.py       # ThingSpeak simulation
│
├── 📚 docs/                         # Documentation
│   ├── architecture_diagram.md     # System architecture
│   ├── uml_diagrams.md             # UML diagrams
│   ├── circuit_diagram.md          # Hardware guide
│   └── simulation_guide.md         # Simulation steps
│
└── 🧪 tests/                        # Test Suite
    ├── test_detector.py            # ML tests
    └── test_api.py                 # API tests
```

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)
- Git
- Webcam (for Phase 1 demo)

### Step 1: Clone & Install

```bash
# Navigate to project directory
cd "drowsiness detection"

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy environment template
copy .env.example .env     # Windows
cp .env.example .env        # Linux/Mac

# Edit .env with your settings:
# - MONGO_URI (MongoDB Atlas connection string)
# - JWT_SECRET_KEY (change for production)
# - THINGSPEAK_API_KEY (for simulation)
```

### Step 3: Start Backend Server

```bash
cd backend
python app.py
# Server starts at http://localhost:5000
```

### Step 4: Open Frontend

```bash
# Open in browser
start frontend/index.html   # Windows
open frontend/index.html     # Mac

# Demo login: admin@drowsiguard.com / admin123
```

---

## 🔬 Phase 1: Code-Based Demo

### Run Drowsiness Detector (Webcam)

```bash
cd ml
python detector.py
# Press 'q' to quit, 's' to save stats
```

### Train CNN Model

```bash
# Option A: Train with synthetic data (quick demo)
python train_cnn.py --train --synthetic

# Option B: Collect real eye images
python train_cnn.py --collect --label open --count 200
python train_cnn.py --collect --label closed --count 200
python train_cnn.py --train
```

### Evaluate Model

```bash
python evaluate.py
# Generates: evaluation_results/evaluation_plots.png
```

---

## 🔄 Phase 2: Simulation

### ThingSpeak IoT Simulation

```bash
cd iot/simulation
python thingspeak_sim.py --duration 120
# View results at thingspeak.com on your channel
```

### Tinkercad Circuit Simulation
See [docs/simulation_guide.md](docs/simulation_guide.md) for step-by-step Tinkercad instructions.

---

## 🔧 Phase 3: Hardware Integration

### Raspberry Pi Setup

```bash
# On Raspberry Pi:
cd iot/raspberry_pi
python main.py --camera 0 --device-id RPi-CAM-001
```

### ESP32-CAM Setup
1. Open `iot/esp32/camera_stream.ino` in Arduino IDE
2. Set WiFi credentials and server URL
3. Upload to ESP32-CAM board
4. Stream available at `http://<esp32-ip>:81/stream`

See [docs/circuit_diagram.md](docs/circuit_diagram.md) for full hardware guide.

---

## 📡 API Documentation

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/health` | System health check | None |
| `POST` | `/api/auth/register` | Register new user | None |
| `POST` | `/api/auth/login` | Login & get JWT | None |
| `GET` | `/api/auth/profile` | Get user profile | JWT |
| `GET` | `/api/auth/users` | List all users | Admin |
| `POST` | `/api/events` | Log drowsiness event | Device Key |
| `GET` | `/api/events` | List events (filtered) | JWT |
| `GET` | `/api/events/latest` | Get latest events | JWT |
| `GET` | `/api/events/stats` | Aggregated statistics | JWT |
| `PUT` | `/api/events/<id>/ack` | Acknowledge event | JWT |
| `GET` | `/api/dashboard/summary` | Dashboard summary | JWT |
| `GET` | `/api/dashboard/realtime` | Real-time data | JWT |
| `POST` | `/api/nlp/query` | Natural language query | JWT |

---

## 🌟 Optional Enhancements

### ✅ Option A: NLP Voice Query (Implemented)
- Text and voice queries on the dashboard
- Web Speech API for voice input
- Queries: "Show driver status", "How many alerts today?", "Last alert"

### ✅ Option B: Network Security (Implemented)
- JWT authentication with expiry
- bcrypt password hashing
- API key authentication for IoT devices
- Rate limiting (200 requests/hour)
- CORS configuration
- Input sanitization

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_detector.py -v
python -m pytest tests/test_api.py -v
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Architecture Diagram](docs/architecture_diagram.md) | System architecture & data flow |
| [UML Diagrams](docs/uml_diagrams.md) | Use case, component, class, deployment |
| [Circuit Diagram](docs/circuit_diagram.md) | GPIO connections & hardware guide |
| [Simulation Guide](docs/simulation_guide.md) | ThingSpeak & Tinkercad setup |

---

## 👥 Contributors

Built as an Academic AAT Integrated Project demonstrating:
- ✅ IoT integration (Raspberry Pi, ESP32-CAM, GPIO)
- ✅ Deep Learning (CNN, MediaPipe, EAR/MAR)
- ✅ Cloud Computing (MongoDB Atlas, ThingSpeak, REST API)
- ✅ Software Engineering (Modular architecture, RBAC, testing)

---

## 📄 License

This project is licensed under the MIT License.
