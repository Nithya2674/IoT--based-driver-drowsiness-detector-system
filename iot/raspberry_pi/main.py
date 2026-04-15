"""
Raspberry Pi Main Script
=========================
Main entry point for the Drowsiness Detection IoT device.
Integrates camera capture, drowsiness detection, buzzer/LED alerts,
and cloud data transmission.

Usage on Raspberry Pi:
    python main.py                      # Default config
    python main.py --camera 0           # USB webcam
    python main.py --camera picamera    # Pi Camera module
    python main.py --no-alert           # Disable buzzer
"""

import os
import sys
import time
import signal
import argparse
import logging
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ml'))

from ml.detector import DrowsinessDetector
from camera_module import CameraCapture
from buzzer_alert import AlertSystem
from cloud_sender import CloudSender

# ─── Logging Setup ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('drowsiness_iot.log')
    ]
)
logger = logging.getLogger(__name__)


class IoTDrowsinessSystem:
    """
    Main IoT Drowsiness Detection System.
    Integrates all components: camera, detection, alerts, and cloud.
    """

    def __init__(self, config):
        """
        Initialize the IoT system.

        Args:
            config: Configuration dictionary with:
                - camera_source: Camera index or 'picamera'
                - backend_url: Cloud API URL
                - device_id: Unique device identifier
                - device_api_key: API key for authentication
                - enable_alert: Whether to enable buzzer/LED
                - ear_threshold: EAR threshold for detection
                - mar_threshold: MAR threshold for detection
        """
        self.config = config
        self.running = False

        logger.info("=" * 60)
        logger.info("  DROWSIGUARD IoT System Initializing...")
        logger.info("=" * 60)

        # Initialize Camera
        logger.info("[1/4] Initializing camera...")
        self.camera = CameraCapture(source=config.get('camera_source', 0))

        # Initialize Detector
        logger.info("[2/4] Initializing drowsiness detector...")
        self.detector = DrowsinessDetector(
            ear_threshold=config.get('ear_threshold', 0.22),
            mar_threshold=config.get('mar_threshold', 0.75),
            consec_frames=config.get('consec_frames', 30),
            alert_callback=self._on_alert,
            cloud_callback=self._on_cloud_event
        )

        # Initialize Alert System
        logger.info("[3/4] Initializing alert system...")
        self.alert = AlertSystem(enabled=config.get('enable_alert', True))

        # Initialize Cloud Sender
        logger.info("[4/4] Initializing cloud connection...")
        self.cloud = CloudSender(
            backend_url=config.get('backend_url', 'http://localhost:5000'),
            device_id=config.get('device_id', 'RPi-CAM-001'),
            api_key=config.get('device_api_key', '')
        )

        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        logger.info("[✓] All systems initialized!")

    def _on_alert(self, event_data):
        """Callback when drowsiness is detected."""
        alert_type = event_data.get('type', 'drowsy')

        if alert_type == 'drowsy':
            self.alert.trigger_alert('danger')
            logger.warning(f"🚨 DROWSINESS ALERT! EAR: {event_data['ear']}")
        elif alert_type == 'yawn':
            self.alert.trigger_alert('warning')
            logger.warning(f"🥱 YAWN DETECTED! MAR: {event_data['mar']}")

    def _on_cloud_event(self, event_data):
        """Callback to send event to cloud."""
        event_data['device_id'] = self.config.get('device_id', 'RPi-CAM-001')
        self.cloud.send_event(event_data)

    def _shutdown(self, signum=None, frame=None):
        """Graceful shutdown handler."""
        logger.info("\n[INFO] Shutting down...")
        self.running = False

    def run(self):
        """Main processing loop."""
        self.running = True

        logger.info("\n" + "=" * 60)
        logger.info("  DROWSIGUARD IoT System RUNNING")
        logger.info(f"  Device: {self.config.get('device_id', 'RPi-CAM-001')}")
        logger.info(f"  Camera: {self.config.get('camera_source', 0)}")
        logger.info(f"  Alerts: {'Enabled' if self.config.get('enable_alert') else 'Disabled'}")
        logger.info("  Press Ctrl+C to stop")
        logger.info("=" * 60 + "\n")

        frame_count = 0
        fps_start = time.time()

        try:
            while self.running:
                # Capture frame
                frame = self.camera.read_frame()
                if frame is None:
                    logger.error("Failed to capture frame")
                    time.sleep(0.1)
                    continue

                # Process frame for drowsiness
                result = self.detector.process_frame(frame)
                frame_count += 1

                # Log periodic status
                if frame_count % 300 == 0:  # Every ~10 seconds at 30fps
                    elapsed = time.time() - fps_start
                    fps = frame_count / max(elapsed, 1)
                    stats = self.detector.get_session_stats()
                    logger.info(
                        f"Status: FPS={fps:.1f} | "
                        f"EAR={result.get('ear', 0):.3f} | "
                        f"Blinks={stats['total_blinks']} | "
                        f"Alerts={stats['drowsy_events']}"
                    )

                # Small delay to control CPU usage
                time.sleep(0.01)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self._cleanup()

    def _cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up resources...")

        # Print session summary
        stats = self.detector.get_session_stats()
        logger.info("\n" + "=" * 60)
        logger.info("  SESSION SUMMARY")
        logger.info(f"  Duration: {stats['session_duration']:.1f}s")
        logger.info(f"  Blinks: {stats['total_blinks']}")
        logger.info(f"  Drowsy Events: {stats['drowsy_events']}")
        logger.info(f"  Yawn Events: {stats['yawn_events']}")
        logger.info("=" * 60)

        # Send final stats to cloud
        self.cloud.send_session_end(stats)

        # Release resources
        self.camera.release()
        self.detector.release()
        self.alert.cleanup()
        self.cloud.flush()

        logger.info("[✓] Shutdown complete.")


def main():
    parser = argparse.ArgumentParser(
        description="DrowsiGuard IoT Drowsiness Detection System"
    )
    parser.add_argument('--camera', default='0',
                        help='Camera source (0, 1, picamera, or URL)')
    parser.add_argument('--backend-url', default='http://localhost:5000',
                        help='Backend API URL')
    parser.add_argument('--device-id', default='RPi-CAM-001',
                        help='Unique device identifier')
    parser.add_argument('--api-key', default='',
                        help='Device API key for authentication')
    parser.add_argument('--no-alert', action='store_true',
                        help='Disable buzzer/LED alerts')
    parser.add_argument('--ear-threshold', type=float, default=0.22,
                        help='EAR threshold (default: 0.22)')
    parser.add_argument('--mar-threshold', type=float, default=0.75,
                        help='MAR threshold (default: 0.75)')
    args = parser.parse_args()

    # Parse camera source
    camera_source = args.camera
    if camera_source.isdigit():
        camera_source = int(camera_source)

    config = {
        'camera_source': camera_source,
        'backend_url': args.backend_url,
        'device_id': args.device_id,
        'device_api_key': args.api_key or os.getenv('DEVICE_API_KEY', ''),
        'enable_alert': not args.no_alert,
        'ear_threshold': args.ear_threshold,
        'mar_threshold': args.mar_threshold,
        'consec_frames': 30
    }

    system = IoTDrowsinessSystem(config)
    system.run()


if __name__ == "__main__":
    main()
