"""
Utility functions for the Deep Learning drowsiness detection module.
Provides helper functions for image processing, landmark extraction,
and metric calculations.
"""

import cv2
import numpy as np
from scipy.spatial import distance as dist


# ─── MediaPipe FaceMesh Landmark Indices ────────────────────────────────────
# Right eye landmark indices (MediaPipe 468-point mesh)
RIGHT_EYE_IDX = [33, 160, 158, 133, 153, 144]
# Left eye landmark indices
LEFT_EYE_IDX = [362, 385, 387, 263, 373, 380]
# Mouth (lips) landmark indices for yawn detection
MOUTH_IDX = [61, 291, 39, 181, 0, 17, 269, 405]
# Upper lip: 13, Lower lip: 14 (vertical)
MOUTH_VERTICAL = [13, 14]
# Left corner: 61, Right corner: 291 (horizontal)
MOUTH_HORIZONTAL = [61, 291]


def calculate_ear(eye_landmarks):
    """
    Calculate the Eye Aspect Ratio (EAR) for a single eye.

    EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)

    Args:
        eye_landmarks: numpy array of shape (6, 2) containing
                       the (x, y) coordinates of the 6 eye landmarks.

    Returns:
        float: The Eye Aspect Ratio value.
    """
    # Compute euclidean distances between vertical eye landmarks
    A = dist.euclidean(eye_landmarks[1], eye_landmarks[5])
    B = dist.euclidean(eye_landmarks[2], eye_landmarks[4])

    # Compute euclidean distance between horizontal eye landmarks
    C = dist.euclidean(eye_landmarks[0], eye_landmarks[3])

    # Calculate EAR
    if C == 0:
        return 0.0
    ear = (A + B) / (2.0 * C)
    return ear


def calculate_mar(mouth_landmarks):
    """
    Calculate the Mouth Aspect Ratio (MAR) for yawn detection.

    MAR = (||p2 - p8|| + ||p3 - p7|| + ||p4 - p6||) / (2 * ||p1 - p5||)

    Args:
        mouth_landmarks: numpy array of shape (8, 2) containing
                         the (x, y) coordinates of the 8 mouth landmarks.

    Returns:
        float: The Mouth Aspect Ratio value.
    """
    # Vertical distances
    A = dist.euclidean(mouth_landmarks[1], mouth_landmarks[7])
    B = dist.euclidean(mouth_landmarks[2], mouth_landmarks[6])
    C = dist.euclidean(mouth_landmarks[3], mouth_landmarks[5])

    # Horizontal distance
    D = dist.euclidean(mouth_landmarks[0], mouth_landmarks[4])

    if D == 0:
        return 0.0
    mar = (A + B + C) / (2.0 * D)
    return mar


def extract_eye_region(frame, landmarks, eye_indices, padding=5):
    """
    Extract the eye region from a frame using facial landmarks.

    Args:
        frame: The input video frame (BGR).
        landmarks: MediaPipe face landmarks.
        eye_indices: List of landmark indices for the eye.
        padding: Pixel padding around the eye region.

    Returns:
        numpy array: Cropped eye region (grayscale, resized to 24x24).
    """
    h, w = frame.shape[:2]
    points = []
    for idx in eye_indices:
        lm = landmarks.landmark[idx]
        x = int(lm.x * w)
        y = int(lm.y * h)
        points.append((x, y))

    points = np.array(points)
    x_min = max(0, np.min(points[:, 0]) - padding)
    x_max = min(w, np.max(points[:, 0]) + padding)
    y_min = max(0, np.min(points[:, 1]) - padding)
    y_max = min(h, np.max(points[:, 1]) + padding)

    eye_region = frame[y_min:y_max, x_min:x_max]

    if eye_region.size == 0:
        return np.zeros((24, 24), dtype=np.uint8)

    eye_gray = cv2.cvtColor(eye_region, cv2.COLOR_BGR2GRAY)
    eye_resized = cv2.resize(eye_gray, (24, 24))
    return eye_resized


def get_landmarks_coords(landmarks, indices, frame_w, frame_h):
    """
    Extract (x, y) coordinates for specific landmark indices.

    Args:
        landmarks: MediaPipe face landmarks object.
        indices: List of landmark indices to extract.
        frame_w: Frame width in pixels.
        frame_h: Frame height in pixels.

    Returns:
        numpy array of shape (len(indices), 2) with pixel coordinates.
    """
    coords = []
    for idx in indices:
        lm = landmarks.landmark[idx]
        coords.append([int(lm.x * frame_w), int(lm.y * frame_h)])
    return np.array(coords)


def draw_eye_contour(frame, landmarks, eye_indices, color=(0, 255, 0)):
    """
    Draw eye contour on the frame for visualization.

    Args:
        frame: The input video frame (BGR).
        landmarks: MediaPipe face landmarks.
        eye_indices: List of landmark indices for the eye.
        color: BGR color tuple for the contour.
    """
    h, w = frame.shape[:2]
    points = []
    for idx in eye_indices:
        lm = landmarks.landmark[idx]
        x = int(lm.x * w)
        y = int(lm.y * h)
        points.append((x, y))

    points = np.array(points, dtype=np.int32)
    cv2.polylines(frame, [points], True, color, 1)


def preprocess_frame(frame, target_size=(640, 480)):
    """
    Preprocess a video frame for detection.

    Args:
        frame: Raw video frame from camera.
        target_size: Tuple (width, height) to resize to.

    Returns:
        Preprocessed frame.
    """
    if frame is None:
        return None
    resized = cv2.resize(frame, target_size)
    return resized


def create_alert_overlay(frame, message, level="warning"):
    """
    Create a visual alert overlay on the frame.

    Args:
        frame: The input video frame.
        message: Alert message text.
        level: Alert level ('warning', 'danger', 'info').

    Returns:
        Frame with alert overlay.
    """
    overlay = frame.copy()
    h, w = frame.shape[:2]

    colors = {
        "warning": (0, 165, 255),   # Orange
        "danger": (0, 0, 255),      # Red
        "info": (255, 200, 0),      # Cyan
    }
    color = colors.get(level, (0, 165, 255))

    # Draw semi-transparent rectangle at top
    cv2.rectangle(overlay, (0, 0), (w, 60), color, -1)
    alpha = 0.6
    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    # Add text
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(message, font, 0.8, 2)[0]
    text_x = (w - text_size[0]) // 2
    cv2.putText(frame, message, (text_x, 40), font, 0.8, (255, 255, 255), 2)

    # Draw border
    cv2.rectangle(frame, (0, 0), (w - 1, h - 1), color, 3)

    return frame
