"""
CNN Training Script for Eye State Classification
==================================================
Generates training data from webcam using MediaPipe eye extraction,
augments the dataset, trains the CNN model, and saves results.

Usage:
    # Step 1: Collect eye images
    python train_cnn.py --collect --label open --count 500
    python train_cnn.py --collect --label closed --count 500

    # Step 2: Train the model
    python train_cnn.py --train

    # Step 3: Quick test
    python train_cnn.py --test
"""

import os
import cv2
import json
import argparse
import numpy as np
from datetime import datetime

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

import mediapipe as mp
from utils import extract_eye_region, LEFT_EYE_IDX, RIGHT_EYE_IDX
from cnn_model import create_cnn_model, create_advanced_cnn


# ─── Configuration ────────────────────────────────────────────────────────
DATASET_DIR = os.path.join(os.path.dirname(__file__), "dataset")
OPEN_DIR = os.path.join(DATASET_DIR, "open")
CLOSED_DIR = os.path.join(DATASET_DIR, "closed")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "eye_state_cnn.h5")
HISTORY_PATH = os.path.join(MODEL_DIR, "training_history.json")

IMG_SIZE = (24, 24)
BATCH_SIZE = 32
EPOCHS = 30


def collect_eye_images(label, count=500, camera=0):
    """
    Collect eye images from webcam using MediaPipe face detection.

    The user looks at the camera with eyes open or closed depending
    on the label. Both left and right eye images are captured.

    Args:
        label: 'open' or 'closed'
        count: Number of images to collect per eye.
        camera: Camera device index.
    """
    save_dir = OPEN_DIR if label == "open" else CLOSED_DIR
    os.makedirs(save_dir, exist_ok=True)

    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    cap = cv2.VideoCapture(camera)
    if not cap.isOpened():
        print("[ERROR] Cannot open camera.")
        return

    print(f"\n{'='*50}")
    print(f"  Collecting '{label}' eye images")
    print(f"  Target: {count} images")
    print(f"  Press 'c' to start capturing, 'q' to quit")
    print(f"{'='*50}\n")

    collected = 0
    capturing = False

    while collected < count:
        ret, frame = cap.read()
        if not ret:
            continue

        frame = cv2.resize(frame, (640, 480))
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        display = frame.copy()

        if results.multi_face_landmarks:
            face_lm = results.multi_face_landmarks[0]

            left_eye = extract_eye_region(frame, face_lm, LEFT_EYE_IDX)
            right_eye = extract_eye_region(frame, face_lm, RIGHT_EYE_IDX)

            # Preview eye regions
            left_preview = cv2.resize(left_eye, (96, 96), interpolation=cv2.INTER_NEAREST)
            right_preview = cv2.resize(right_eye, (96, 96), interpolation=cv2.INTER_NEAREST)

            display[10:106, 10:106] = cv2.cvtColor(left_preview, cv2.COLOR_GRAY2BGR)
            display[10:106, 120:216] = cv2.cvtColor(right_preview, cv2.COLOR_GRAY2BGR)

            if capturing:
                # Save both eyes
                ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                cv2.imwrite(os.path.join(save_dir, f"left_{ts}.png"), left_eye)
                cv2.imwrite(os.path.join(save_dir, f"right_{ts}.png"), right_eye)
                collected += 2

        status = "CAPTURING" if capturing else "READY (press 'c')"
        color = (0, 0, 255) if capturing else (0, 255, 0)
        cv2.putText(display, f"Label: {label} | {status}", (10, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(display, f"Collected: {collected}/{count}", (10, 160),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("Eye Data Collection", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('c'):
            capturing = not capturing
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    face_mesh.close()
    print(f"\n[INFO] Collected {collected} '{label}' eye images to {save_dir}")


def load_dataset():
    """
    Load the collected eye image dataset.

    Returns:
        tuple: (X_train, X_test, y_train, y_test)
    """
    images = []
    labels = []

    # Load open eyes (label = 1)
    if os.path.exists(OPEN_DIR):
        for fname in os.listdir(OPEN_DIR):
            if fname.endswith('.png'):
                img = cv2.imread(os.path.join(OPEN_DIR, fname), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    img = cv2.resize(img, IMG_SIZE)
                    images.append(img)
                    labels.append(1)  # open

    # Load closed eyes (label = 0)
    if os.path.exists(CLOSED_DIR):
        for fname in os.listdir(CLOSED_DIR):
            if fname.endswith('.png'):
                img = cv2.imread(os.path.join(CLOSED_DIR, fname), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    img = cv2.resize(img, IMG_SIZE)
                    images.append(img)
                    labels.append(0)  # closed

    if len(images) == 0:
        print("[ERROR] No images found. Run --collect first.")
        return None, None, None, None

    X = np.array(images, dtype='float32') / 255.0
    X = np.expand_dims(X, axis=-1)
    y = np.array(labels, dtype='float32')

    print(f"\n[INFO] Dataset loaded: {len(X)} images")
    print(f"  Open: {np.sum(y == 1):.0f} | Closed: {np.sum(y == 0):.0f}")

    # Shuffle and split
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    return X_train, X_test, y_train, y_test


def create_synthetic_dataset(n_samples=2000):
    """
    Create a synthetic dataset for demonstration when no real data is available.
    Generates synthetic eye images with open/closed patterns.

    Args:
        n_samples: Total number of samples to generate.

    Returns:
        tuple: (X_train, X_test, y_train, y_test)
    """
    print("[INFO] Generating synthetic dataset for demonstration...")

    images = []
    labels = []

    for i in range(n_samples):
        img = np.zeros((24, 24), dtype='float32')

        if i < n_samples // 2:
            # Open eye pattern — elliptical bright region
            cv2.ellipse(img, (12, 12), (8, 5), 0, 0, 360, 1.0, -1)
            cv2.circle(img, (12, 12), 3, 0.3, -1)  # pupil
            noise = np.random.normal(0, 0.1, (24, 24)).astype('float32')
            img = np.clip(img + noise, 0, 1)
            labels.append(1)  # open
        else:
            # Closed eye pattern — thin horizontal line
            cv2.line(img, (4, 12), (20, 12), 0.8, 2)
            noise = np.random.normal(0, 0.15, (24, 24)).astype('float32')
            img = np.clip(img + noise, 0, 1)
            labels.append(0)  # closed

        images.append(img)

    X = np.array(images, dtype='float32')
    X = np.expand_dims(X, axis=-1)
    y = np.array(labels, dtype='float32')

    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"  Training: {len(X_train)} | Testing: {len(X_test)}")
    return X_train, X_test, y_train, y_test


def train_model(use_synthetic=False):
    """
    Train the CNN model on collected or synthetic data.

    Args:
        use_synthetic: If True, use synthetic data for demonstration.
    """
    if not TF_AVAILABLE:
        print("[ERROR] TensorFlow is required for training.")
        return

    # Load data
    if use_synthetic:
        X_train, X_test, y_train, y_test = create_synthetic_dataset()
    else:
        X_train, X_test, y_train, y_test = load_dataset()
        if X_train is None:
            print("[INFO] No real data found. Using synthetic data instead.")
            X_train, X_test, y_train, y_test = create_synthetic_dataset()

    # Data augmentation
    datagen = ImageDataGenerator(
        rotation_range=10,
        width_shift_range=0.1,
        height_shift_range=0.1,
        zoom_range=0.1,
        horizontal_flip=True,
        brightness_range=[0.8, 1.2]
    )
    datagen.fit(X_train)

    # Create model
    model = create_cnn_model(input_shape=(24, 24, 1))
    model.summary()

    # Callbacks
    os.makedirs(MODEL_DIR, exist_ok=True)
    cb = [
        callbacks.ModelCheckpoint(
            MODEL_PATH, monitor='val_accuracy',
            save_best_only=True, verbose=1
        ),
        callbacks.EarlyStopping(
            monitor='val_loss', patience=8, restore_best_weights=True
        ),
        callbacks.ReduceLROnPlateau(
            monitor='val_loss', factor=0.5, patience=4, min_lr=1e-6
        )
    ]

    # Train
    print("\n[INFO] Training started...")
    history = model.fit(
        datagen.flow(X_train, y_train, batch_size=BATCH_SIZE),
        epochs=EPOCHS,
        validation_data=(X_test, y_test),
        callbacks=cb,
        verbose=1
    )

    # Save training history
    hist = {k: [float(v) for v in vals] for k, vals in history.history.items()}
    with open(HISTORY_PATH, 'w') as f:
        json.dump(hist, f, indent=2)

    # Final evaluation
    print("\n[INFO] Final Evaluation:")
    results = model.evaluate(X_test, y_test, verbose=0)
    metric_names = model.metrics_names
    for name, value in zip(metric_names, results):
        print(f"  {name}: {value:.4f}")

    print(f"\n[INFO] Model saved to: {MODEL_PATH}")
    print(f"[INFO] History saved to: {HISTORY_PATH}")
    return model, history


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CNN Eye State Training")
    parser.add_argument("--collect", action="store_true",
                        help="Collect eye images from webcam")
    parser.add_argument("--label", type=str, choices=["open", "closed"],
                        help="Label for collected images")
    parser.add_argument("--count", type=int, default=500,
                        help="Number of images to collect")
    parser.add_argument("--train", action="store_true",
                        help="Train the CNN model")
    parser.add_argument("--synthetic", action="store_true",
                        help="Use synthetic data for training")
    parser.add_argument("--test", action="store_true",
                        help="Quick test of the model")
    parser.add_argument("--camera", type=int, default=0,
                        help="Camera device index")
    args = parser.parse_args()

    if args.collect:
        if not args.label:
            print("[ERROR] --label required with --collect (open or closed)")
        else:
            collect_eye_images(args.label, args.count, args.camera)
    elif args.train:
        train_model(use_synthetic=args.synthetic)
    elif args.test:
        if TF_AVAILABLE and os.path.exists(MODEL_PATH):
            model = keras.models.load_model(MODEL_PATH)
            test_img = np.random.rand(1, 24, 24, 1).astype('float32')
            pred = model.predict(test_img, verbose=0)
            print(f"Test prediction: {pred[0][0]:.4f}")
            print("Model loaded and working!")
        else:
            print("No trained model found. Run --train first.")
    else:
        parser.print_help()
