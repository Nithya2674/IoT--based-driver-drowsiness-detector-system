"""
Flask Application Factory
===========================
Main entry point for the Drowsiness Detection REST API.

Endpoints:
    /api/auth/*       — Authentication (login, register, profile)
    /api/events/*     — Drowsiness event CRUD
    /api/dashboard/*  — Dashboard aggregation data
    /api/nlp/*        — Natural language query interface

Usage:
    python app.py                   # Run on default port 5000
    FLASK_PORT=8000 python app.py   # Run on custom port
"""

import os
import sys
from datetime import datetime
import cv2
from flask import Flask, jsonify, Response, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Import ML modules for video streaming
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ml')))
try:
    from detector import DrowsinessDetector
    from ml_helper import preprocess_frame
except ImportError as e:
    print(f"[Warning] ML module failed to load: {e}")
    DrowsinessDetector = None
    preprocess_frame = None

from config import get_config


# ─── Global Instances ─────────────────────────────────────────────────────
db = None
jwt = JWTManager()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"]
)


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    config = get_config()
    app.config.from_object(config)

    # ─── Initialize Extensions ────────────────────────────────────
    CORS(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}})
    jwt.init_app(app)
    limiter.init_app(app)

    # ─── Database Connection ──────────────────────────────────────
    global db
    try:
        from models.user import UserModel
        client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        client.admin.command('ping')
        db = client[config.MONGO_DB_NAME]
        app.mongo_db = db
        print(f"[✓] Connected to MongoDB: {config.MONGO_DB_NAME}")
        
        # Seed admin user if the database is completely empty
        if db.users.count_documents({}) == 0:
            print("[INFO] Database empty. Seeding default admin user...")
            admin_doc = UserModel.create_user("admin", "admin@drowsiguard.com", "admin123", "admin")
            db.users.insert_one(admin_doc)
            
    except ConnectionFailure:
        print("[✗] MongoDB connection failed. Using in-memory fallback.")
        print("    Set MONGO_URI in .env file for cloud database.")
        db = None
    except Exception as e:
        print(f"[✗] MongoDB error: {e}")
        db = None
        app.mongo_db = None

    # ─── Register Blueprints ─────────────────────────────────────
    from routes.auth import auth_bp
    from routes.events import events_bp
    from routes.dashboard import dashboard_bp
    from routes.nlp import nlp_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(events_bp, url_prefix='/api/events')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(nlp_bp, url_prefix='/api/nlp')

    # ─── Health Check ─────────────────────────────────────────────
    @app.route('/api/health', methods=['GET'])
    def health_check():
        db_status = "connected" if db is not None else "disconnected"
        return jsonify({
            "status": "healthy",
            "database": db_status,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        })

    # ─── Video Streaming ──────────────────────────────────────────
    def generate_frames():
        """Generator function that yields MJPEG AI-processed camera frames."""
        if not DrowsinessDetector:
            return

        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Initialize detector
        detector = DrowsinessDetector(ear_threshold=0.22, mar_threshold=0.75, consec_frames=30)
        
        while True:
            success, frame = cap.read()
            if not success:
                break
            else:
                frame = preprocess_frame(frame, (640, 480))
                
                # Process frame with AI
                result = detector.process_frame(frame)
                processed_frame = result["frame"]

                # Encode to JPEG
                ret, buffer = cv2.imencode('.jpg', processed_frame)
                frame_bytes = buffer.tobytes()

                # Yield in multipart format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        cap.release()
        detector.release()

    @app.route('/api/video_feed')
    def video_feed():
        """MJPEG Streaming route, put this in the src of an image tag."""
        return Response(generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

    # ─── Error Handlers ───────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({
            "error": "Rate limit exceeded. Try again later."
        }), 429

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500

    # ─── JWT Error Handlers ───────────────────────────────────────
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "error": "Token has expired",
            "code": "token_expired"
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            "error": "Invalid token",
            "code": "invalid_token"
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            "error": "Authorization token required",
            "code": "token_missing"
        }), 401

    return app


def get_db():
    """Get the database instance. Falls back to in-memory store."""
    global db
    return db


# ─── In-memory fallback store ────────────────────────────────────────────
_memory_store = {
    "users": [],
    "events": []
}


def get_memory_store():
    """Get in-memory store for when MongoDB is unavailable."""
    return _memory_store


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv('FLASK_PORT', 5000))
    print(f"\n{'='*60}")
    print(f"  Drowsiness Detection API Server")
    print(f"  Running on http://localhost:{port}")
    print(f"  API Docs: http://localhost:{port}/api/health")
    print(f"{'='*60}\n")
    app.run(host='0.0.0.0', port=port, debug=True)
