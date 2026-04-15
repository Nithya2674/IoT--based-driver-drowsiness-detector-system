"""
Camera Capture Module
======================
Abstraction layer for camera input supporting USB webcam,
Pi Camera module, and ESP32-CAM network streams.
"""

import cv2
import logging

logger = logging.getLogger(__name__)


class CameraCapture:
    """
    Camera capture abstraction supporting multiple input sources.

    Supported sources:
        - Integer (0, 1): USB webcam index
        - 'picamera': Raspberry Pi Camera Module
        - URL string: Network camera (ESP32-CAM MJPEG stream)
    """

    def __init__(self, source=0, width=640, height=480):
        """
        Initialize camera capture.

        Args:
            source: Camera source (int, 'picamera', or URL string).
            width: Desired frame width.
            height: Desired frame height.
        """
        self.source = source
        self.width = width
        self.height = height
        self.cap = None
        self.picam = None
        self.use_picamera = False

        if source == 'picamera':
            self._init_picamera()
        elif isinstance(source, str) and source.startswith('http'):
            self._init_network_camera(source)
        else:
            self._init_usb_camera(int(source) if isinstance(source, str) else source)

    def _init_usb_camera(self, index):
        """Initialize USB webcam."""
        logger.info(f"Opening USB camera at index {index}")
        self.cap = cv2.VideoCapture(index)
        if not self.cap.isOpened():
            logger.error(f"Failed to open camera at index {index}")
            raise RuntimeError(f"Cannot open camera {index}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        logger.info(f"USB camera opened: {self.width}x{self.height}")

    def _init_network_camera(self, url):
        """Initialize network camera (ESP32-CAM MJPEG stream)."""
        logger.info(f"Opening network camera at {url}")
        self.cap = cv2.VideoCapture(url)
        if not self.cap.isOpened():
            logger.error(f"Failed to connect to network camera: {url}")
            raise RuntimeError(f"Cannot connect to {url}")
        logger.info("Network camera connected")

    def _init_picamera(self):
        """Initialize Raspberry Pi Camera Module."""
        try:
            from picamera2 import Picamera2
            logger.info("Opening Pi Camera Module...")
            self.picam = Picamera2()
            config = self.picam.create_still_configuration(
                main={"size": (self.width, self.height)}
            )
            self.picam.configure(config)
            self.picam.start()
            self.use_picamera = True
            logger.info("Pi Camera initialized")
        except ImportError:
            logger.warning("picamera2 not available. Falling back to USB camera.")
            self._init_usb_camera(0)

    def read_frame(self):
        """
        Read a single frame from the camera.

        Returns:
            numpy array: BGR frame, or None on failure.
        """
        if self.use_picamera and self.picam:
            frame = self.picam.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            frame = cv2.resize(frame, (self.width, self.height))
            return frame
        elif self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.resize(frame, (self.width, self.height))
                return frame
        return None

    def release(self):
        """Release camera resources."""
        if self.cap:
            self.cap.release()
            logger.info("Camera released")
        if self.picam:
            self.picam.stop()
            logger.info("Pi Camera stopped")
