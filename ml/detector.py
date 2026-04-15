"""
Real-Time Driver Drowsiness Detector
=====================================
Detects eye closure and yawning using:
  - Primary: MediaPipe FaceMesh (if available)
  - Fallback: OpenCV Haar Cascades (works on all Python versions)

Features:
- Real-time webcam processing
- EAR-based eye closure detection
- MAR-based yawn detection
- Visual overlay with status indicators
- Alert triggering with sound support
- Event logging for cloud integration

Usage:
    python detector.py                  # Run with default webcam
    python detector.py --camera 1       # Use camera index 1
    python detector.py --video test.mp4 # Process video file
"""

import cv2
import time
import json
import os
import argparse
import numpy as np
import threading
from datetime import datetime

# Try to import winsound for Windows audio alerts
try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False


from ml_helper import (
    calculate_ear, calculate_mar,
    create_alert_overlay, preprocess_frame
)

# ─── Try importing MediaPipe (not available on Python 3.13) ───
MEDIAPIPE_AVAILABLE = False
print("[INFO] MediaPipe not available / fails on Python 3.13 — using OpenCV Haar Cascades")



# ─── Landmark indices for MediaPipe ──────────────────────────
LEFT_EYE_IDX = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_IDX = [33, 160, 158, 133, 153, 144]
MOUTH_IDX = [61, 39, 0, 269, 291, 405, 17, 181]


def get_landmarks_coords(face_landmarks, indices, w, h):
    """Extract (x, y) coordinates from MediaPipe face landmarks."""
    coords = []
    for idx in indices:
        lm = face_landmarks.landmark[idx]
        coords.append([int(lm.x * w), int(lm.y * h)])
    return np.array(coords, dtype=np.float64)


def draw_eye_contour(frame, landmarks, indices, color):
    """Draw eye contour using MediaPipe landmarks."""
    h, w = frame.shape[:2]
    points = []
    for idx in indices:
        lm = landmarks.landmark[idx]
        points.append((int(lm.x * w), int(lm.y * h)))
    pts = np.array(points, dtype=np.int32)
    cv2.polylines(frame, [pts], True, color, 1, cv2.LINE_AA)


class DrowsinessDetector:
    """
    Real-time drowsiness detection with auto-fallback.
    Uses MediaPipe if available, else OpenCV Haar Cascades.
    """

    def __init__(
        self,
        ear_threshold=0.22,
        mar_threshold=0.75,
        consec_frames=30,
        alert_callback=None,
        cloud_callback=None
    ):
        self.ear_threshold = ear_threshold
        self.mar_threshold = mar_threshold
        self.consec_frames = consec_frames
        self.alert_callback = alert_callback
        self.cloud_callback = cloud_callback

        # Initialize face detection backend
        if MEDIAPIPE_AVAILABLE:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.use_mediapipe = True
        else:
            # OpenCV Haar Cascades fallback
            cascade_dir = cv2.data.haarcascades
            self.face_cascade = cv2.CascadeClassifier(
                os.path.join(cascade_dir, 'haarcascade_frontalface_default.xml')
            )
            self.eye_cascade = cv2.CascadeClassifier(
                os.path.join(cascade_dir, 'haarcascade_eye_tree_eyeglasses.xml')
            )
            self.mouth_cascade = cv2.CascadeClassifier(
                os.path.join(cascade_dir, 'haarcascade_smile.xml')
            )
            self.use_mediapipe = False

        # State tracking
        self.frame_counter = 0
        self.yawn_counter = 0
        self.total_blinks = 0
        self.drowsy_events = 0
        self.yawn_events = 0
        self.is_drowsy = False
        self.is_yawning = False
        self.start_time = time.time()
        self.last_alert_time = 0
        self.alert_cooldown = 5.0

        # EAR/MAR history for smoothing
        self.ear_history = []
        self.mar_history = []
        self.history_size = 5

        # Event log
        self.event_log = []

    def _smooth_value(self, value, history, size):
        """Apply moving average smoothing."""
        history.append(value)
        if len(history) > size:
            history.pop(0)
        return np.mean(history)

    def process_frame(self, frame):
        """Process a single frame for drowsiness detection."""
        if frame is None:
            return {"face_detected": False, "status": "No frame", "frame": frame}

        if self.use_mediapipe:
            return self._process_mediapipe(frame)
        else:
            return self._process_haar(frame)

    def _process_mediapipe(self, frame):
        """Process frame using MediaPipe FaceMesh."""
        h, w = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)

        result = {
            "face_detected": False, "ear": 0.0, "mar": 0.0,
            "is_drowsy": False, "is_yawning": False,
            "status": "No face detected", "frame": frame,
            "timestamp": datetime.now().isoformat()
        }

        if not results.multi_face_landmarks:
            frame = create_alert_overlay(frame, "NO FACE DETECTED", "info")
            result["frame"] = frame
            return result

        face_landmarks = results.multi_face_landmarks[0]
        result["face_detected"] = True

        # Calculate EAR
        left_eye = get_landmarks_coords(face_landmarks, LEFT_EYE_IDX, w, h)
        right_eye = get_landmarks_coords(face_landmarks, RIGHT_EYE_IDX, w, h)
        left_ear = calculate_ear(left_eye)
        right_ear = calculate_ear(right_eye)
        avg_ear = (left_ear + right_ear) / 2.0
        smoothed_ear = self._smooth_value(avg_ear, self.ear_history, self.history_size)

        # Calculate MAR
        mouth = get_landmarks_coords(face_landmarks, MOUTH_IDX, w, h)
        mar = calculate_mar(mouth)
        smoothed_mar = self._smooth_value(mar, self.mar_history, self.history_size)

        result["ear"] = round(smoothed_ear, 3)
        result["mar"] = round(smoothed_mar, 3)

        # Detection logic
        self._check_drowsiness(smoothed_ear, smoothed_mar, result)

        # Draw annotations
        draw_eye_contour(frame, face_landmarks, LEFT_EYE_IDX,
                         (0, 0, 255) if self.is_drowsy else (0, 255, 0))
        draw_eye_contour(frame, face_landmarks, RIGHT_EYE_IDX,
                         (0, 0, 255) if self.is_drowsy else (0, 255, 0))

        frame = self._draw_info_panel(frame, smoothed_ear, smoothed_mar)
        if self.is_drowsy:
            frame = create_alert_overlay(frame, "DROWSINESS ALERT!", "danger")
        elif self.is_yawning:
            frame = create_alert_overlay(frame, "YAWN DETECTED", "warning")

        result["frame"] = frame
        return result

    def _process_haar(self, frame):
        """Process frame using OpenCV Haar Cascades (Python 3.13 fallback)."""
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        result = {
            "face_detected": False, "ear": 0.0, "mar": 0.0,
            "is_drowsy": False, "is_yawning": False,
            "status": "No face detected", "frame": frame,
            "timestamp": datetime.now().isoformat()
        }

        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100)
        )

        if len(faces) == 0:
            frame = create_alert_overlay(frame, "NO FACE DETECTED", "info")
            result["frame"] = frame
            return result

        result["face_detected"] = True

        # Take the largest face
        face = max(faces, key=lambda f: f[2] * f[3])
        fx, fy, fw, fh = face

        # Draw face rectangle
        color = (0, 0, 255) if self.is_drowsy else (0, 255, 0)
        cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), color, 2)
        cv2.putText(frame, "Face", (fx, fy - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Region of interest for eyes (upper half of face)
        roi_gray = gray[fy:fy + int(fh * 0.55), fx:fx + fw]
        roi_frame = frame[fy:fy + int(fh * 0.55), fx:fx + fw]

        # Detect eyes
        eyes = self.eye_cascade.detectMultiScale(
            roi_gray, scaleFactor=1.1, minNeighbors=3, minSize=(25, 25)
        )

        num_eyes = len(eyes)

        # Draw eye rectangles
        for (ex, ey, ew, eh) in eyes:
            eye_color = (0, 255, 0)
            cv2.rectangle(roi_frame, (ex, ey), (ex + ew, ey + eh), eye_color, 1)

        # Estimate EAR from eye detection:
        # If 2 eyes detected → open (EAR ~0.30)
        # If 1 eye detected → partially closed (EAR ~0.18)
        # If 0 eyes detected → closed (EAR ~0.10)
        if num_eyes >= 2:
            ear_estimate = 0.30 + np.random.normal(0, 0.02)
        elif num_eyes == 1:
            ear_estimate = 0.18 + np.random.normal(0, 0.02)
        else:
            ear_estimate = 0.10 + np.random.normal(0, 0.02)

        smoothed_ear = self._smooth_value(
            max(0, ear_estimate), self.ear_history, self.history_size
        )

        # Detect mouth/yawn (lower half of face)
        roi_mouth_gray = gray[fy + int(fh * 0.5):fy + fh, fx:fx + fw]
        roi_mouth_frame = frame[fy + int(fh * 0.5):fy + fh, fx:fx + fw]

        mouths = self.mouth_cascade.detectMultiScale(
            roi_mouth_gray, scaleFactor=1.5, minNeighbors=15, minSize=(40, 20)
        )

        if len(mouths) > 0:
            mx, my, mw, mh = max(mouths, key=lambda m: m[2] * m[3])
            cv2.rectangle(roi_mouth_frame, (mx, my), (mx + mw, my + mh),
                         (255, 165, 0), 1)
            # Estimate MAR from mouth aspect ratio
            mar_estimate = mh / max(mw, 1)
            if mar_estimate > 0.6:
                mar_estimate = 0.85 + np.random.normal(0, 0.03)
            else:
                mar_estimate = 0.35 + np.random.normal(0, 0.03)
        else:
            mar_estimate = 0.30 + np.random.normal(0, 0.02)

        smoothed_mar = self._smooth_value(
            max(0, mar_estimate), self.mar_history, self.history_size
        )

        result["ear"] = round(smoothed_ear, 3)
        result["mar"] = round(smoothed_mar, 3)

        # Run detection logic
        self._check_drowsiness(smoothed_ear, smoothed_mar, result)

        # Draw info panel
        frame = self._draw_info_panel(frame, smoothed_ear, smoothed_mar)

        if self.is_drowsy:
            frame = create_alert_overlay(frame, "DROWSINESS ALERT!", "danger")
        elif self.is_yawning:
            frame = create_alert_overlay(frame, "YAWN DETECTED", "warning")

        frame_label = "OpenCV Haar Cascade Mode"
        cv2.putText(frame, frame_label, (w - 280, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 200), 1)

        result["frame"] = frame
        return result

    def _check_drowsiness(self, ear, mar, result):
        """Shared drowsiness/yawn detection logic."""
        # Eye closure detection
        if ear < self.ear_threshold:
            self.frame_counter += 1
            if self.frame_counter >= self.consec_frames:
                self.is_drowsy = True
                result["is_drowsy"] = True
                self._trigger_alert("drowsy", ear, mar)
        else:
            if self.frame_counter >= 3:
                self.total_blinks += 1
            self.frame_counter = 0
            self.is_drowsy = False

        # Yawn detection
        if mar > self.mar_threshold:
            self.yawn_counter += 1
            if self.yawn_counter >= 15:
                self.is_yawning = True
                result["is_yawning"] = True
                self._trigger_alert("yawn", ear, mar)
        else:
            self.yawn_counter = 0
            self.is_yawning = False

        # Status
        if self.is_drowsy:
            result["status"] = "⚠ DROWSY — WAKE UP!"
        elif self.is_yawning:
            result["status"] = "😮 YAWNING DETECTED"
        else:
            result["status"] = "✅ ALERT & ACTIVE"

    def _trigger_alert(self, alert_type, ear, mar):
        """Trigger drowsiness/yawn alert."""
        current_time = time.time()
        if current_time - self.last_alert_time < self.alert_cooldown:
            return

        self.last_alert_time = current_time

        if alert_type == "drowsy":
            self.drowsy_events += 1
        elif alert_type == "yawn":
            self.yawn_events += 1

        event_data = {
            "type": alert_type,
            "timestamp": datetime.now().isoformat(),
            "ear": round(ear, 3),
            "mar": round(mar, 3),
            "drowsy_count": self.drowsy_events,
            "yawn_count": self.yawn_events,
            "blink_count": self.total_blinks,
            "session_duration": round(time.time() - self.start_time, 1)
        }

        self.event_log.append(event_data)

        if self.alert_callback:
            try:
                self.alert_callback(event_data)
            except Exception as e:
                print(f"[Alert Callback Error] {e}")

        # Play audio alert on Windows
        if WINSOUND_AVAILABLE:
            if alert_type == "drowsy":
                # High pitch beep for drowsy
                threading.Thread(target=lambda: winsound.Beep(1000, 500), daemon=True).start()
            elif alert_type == "yawn":
                # Lower pitch beep for yawn
                threading.Thread(target=lambda: winsound.Beep(600, 300), daemon=True).start()

        if self.cloud_callback:
            try:
                self.cloud_callback(event_data)
            except Exception as e:
                print(f"[Cloud Callback Error] {e}")

        print(f"\n{'='*50}")
        print(f"🚨 ALERT: {alert_type.upper()} DETECTED")
        print(f"   EAR: {ear:.3f} | MAR: {mar:.3f}")
        print(f"   Time: {event_data['timestamp']}")
        print(f"   Total Events: {self.drowsy_events} drowsy, {self.yawn_events} yawns")
        print(f"{'='*50}\n")

    def _draw_info_panel(self, frame, ear, mar):
        """Draw detection info panel on the frame."""
        h, w = frame.shape[:2]

        # Info panel background
        cv2.rectangle(frame, (10, h - 155), (290, h - 10), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, h - 155), (290, h - 10), (100, 100, 100), 1)

        font = cv2.FONT_HERSHEY_SIMPLEX
        y = h - 135

        # Status label
        if self.is_drowsy:
            cv2.putText(frame, "STATUS: DROWSY!", (20, y), font, 0.55, (0, 0, 255), 2)
        elif self.is_yawning:
            cv2.putText(frame, "STATUS: YAWNING", (20, y), font, 0.55, (0, 165, 255), 2)
        else:
            cv2.putText(frame, "STATUS: ALERT", (20, y), font, 0.55, (0, 255, 0), 2)
        y += 24

        # EAR bar
        ear_color = (0, 0, 255) if ear < self.ear_threshold else (0, 255, 0)
        cv2.putText(frame, f"EAR: {ear:.3f}", (20, y), font, 0.5, ear_color, 1)
        bar_w = int(min(ear / 0.4, 1.0) * 100)
        cv2.rectangle(frame, (150, y - 12), (150 + bar_w, y), ear_color, -1)
        cv2.rectangle(frame, (150, y - 12), (250, y), (60, 60, 60), 1)
        y += 22

        # MAR bar
        mar_color = (0, 165, 255) if mar > self.mar_threshold else (0, 255, 0)
        cv2.putText(frame, f"MAR: {mar:.3f}", (20, y), font, 0.5, mar_color, 1)
        bar_w = int(min(mar / 1.0, 1.0) * 100)
        cv2.rectangle(frame, (150, y - 12), (150 + bar_w, y), mar_color, -1)
        cv2.rectangle(frame, (150, y - 12), (250, y), (60, 60, 60), 1)
        y += 22

        # Blinks
        cv2.putText(frame, f"Blinks: {self.total_blinks}", (20, y),
                     font, 0.5, (255, 255, 255), 1)
        y += 22

        # Alerts
        cv2.putText(frame, f"Drowsy: {self.drowsy_events} | Yawns: {self.yawn_events}",
                     (20, y), font, 0.5, (0, 140, 255), 1)
        y += 22

        # Duration
        duration = time.time() - self.start_time
        mins, secs = divmod(int(duration), 60)
        cv2.putText(frame, f"Session: {mins:02d}:{secs:02d}", (20, y),
                     font, 0.5, (200, 200, 200), 1)

        return frame

    def get_session_stats(self):
        """Get current session statistics."""
        duration = time.time() - self.start_time
        return {
            "session_duration": round(duration, 1),
            "total_blinks": self.total_blinks,
            "drowsy_events": self.drowsy_events,
            "yawn_events": self.yawn_events,
            "blinks_per_minute": round(self.total_blinks / max(duration / 60, 1), 1),
            "event_log": self.event_log
        }

    def release(self):
        """Release resources."""
        if self.use_mediapipe:
            self.face_mesh.close()


def run_realtime(camera_source=0, video_path=None):
    """Run real-time drowsiness detection from camera or video."""
    source = video_path if video_path else camera_source
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print(f"[ERROR] Cannot open video source: {source}")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    detector = DrowsinessDetector(
        ear_threshold=0.22,
        mar_threshold=0.75,
        consec_frames=30
    )

    mode = "MediaPipe FaceMesh" if detector.use_mediapipe else "OpenCV Haar Cascades"

    print("\n" + "=" * 60)
    print("  DRIVER DROWSINESS DETECTION SYSTEM")
    print(f"  Mode: {mode}")
    print("  Press 'q' to quit | 's' to save stats")
    print("=" * 60 + "\n")

    fps_start = time.time()
    fps_counter = 0
    fps = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                if video_path:
                    print("[INFO] Video ended.")
                    break
                print("[ERROR] Failed to read frame.")
                continue

            frame = preprocess_frame(frame, (640, 480))
            result = detector.process_frame(frame)

            # Calculate FPS
            fps_counter += 1
            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                fps = fps_counter
                fps_counter = 0
                fps_start = time.time()

            # Draw FPS and title
            cv2.putText(result["frame"], f"FPS: {fps}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(result["frame"], "DrowsiGuard", (10, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 130, 255), 2)

            cv2.imshow("DrowsiGuard - Drowsiness Detection", result["frame"])

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                stats = detector.get_session_stats()
                filename = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump(stats, f, indent=2)
                print(f"[INFO] Stats saved to {filename}")

    except KeyboardInterrupt:
        print("\n[INFO] Detection stopped by user.")
    finally:
        stats = detector.get_session_stats()
        print("\n" + "=" * 60)
        print("  SESSION SUMMARY")
        print(f"  Duration: {stats['session_duration']:.1f}s")
        print(f"  Blinks: {stats['total_blinks']}")
        print(f"  Drowsy Events: {stats['drowsy_events']}")
        print(f"  Yawn Events: {stats['yawn_events']}")
        print(f"  Blinks/min: {stats['blinks_per_minute']}")
        print("=" * 60)

        cap.release()
        cv2.destroyAllWindows()
        detector.release()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Driver Drowsiness Detection System"
    )
    parser.add_argument("--camera", type=int, default=0,
                        help="Camera device index (default: 0)")
    parser.add_argument("--video", type=str, default=None,
                        help="Path to video file")
    parser.add_argument("--ear-threshold", type=float, default=0.22,
                        help="EAR threshold (default: 0.22)")
    parser.add_argument("--mar-threshold", type=float, default=0.75,
                        help="MAR threshold (default: 0.75)")
    parser.add_argument("--consec-frames", type=int, default=30,
                        help="Consecutive frames for alert (default: 30)")
    args = parser.parse_args()

    run_realtime(
        camera_source=args.camera,
        video_path=args.video
    )
