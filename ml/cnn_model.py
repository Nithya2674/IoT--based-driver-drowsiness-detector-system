"""
CNN Model for Eye State Classification
=======================================
Convolutional Neural Network for classifying eye state as
Open or Closed. Used as a secondary classifier alongside
the EAR-based geometric approach.

Architecture:
    Input (24x24x1) → Conv2D(32) → MaxPool → Conv2D(64) → MaxPool →
    Flatten → Dense(128) → Dropout(0.5) → Dense(1, sigmoid)
"""

import numpy as np

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers, models, callbacks
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("[WARNING] TensorFlow not installed. CNN features disabled.")


def create_cnn_model(input_shape=(24, 24, 1)):
    """
    Create a CNN model for eye state classification.

    Architecture optimized for small eye region images (24x24 grayscale).

    Args:
        input_shape: Tuple (height, width, channels). Default (24, 24, 1).

    Returns:
        Compiled Keras model.
    """
    if not TF_AVAILABLE:
        raise ImportError("TensorFlow is required for CNN model.")

    model = models.Sequential([
        # First Convolutional Block
        layers.Conv2D(32, (3, 3), activation='relu', padding='same',
                      input_shape=input_shape, name='conv1'),
        layers.BatchNormalization(name='bn1'),
        layers.MaxPooling2D((2, 2), name='pool1'),

        # Second Convolutional Block
        layers.Conv2D(64, (3, 3), activation='relu', padding='same',
                      name='conv2'),
        layers.BatchNormalization(name='bn2'),
        layers.MaxPooling2D((2, 2), name='pool2'),

        # Third Convolutional Block
        layers.Conv2D(128, (3, 3), activation='relu', padding='same',
                      name='conv3'),
        layers.BatchNormalization(name='bn3'),
        layers.MaxPooling2D((2, 2), name='pool3'),

        # Fully Connected Layers
        layers.Flatten(name='flatten'),
        layers.Dense(128, activation='relu', name='fc1'),
        layers.Dropout(0.5, name='dropout1'),
        layers.Dense(64, activation='relu', name='fc2'),
        layers.Dropout(0.3, name='dropout2'),

        # Output Layer
        layers.Dense(1, activation='sigmoid', name='output')
    ], name='eye_state_cnn')

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy', keras.metrics.Precision(), keras.metrics.Recall()]
    )

    return model


def create_advanced_cnn(input_shape=(24, 24, 1)):
    """
    Create an advanced CNN model with residual-like connections.

    Args:
        input_shape: Input image shape.

    Returns:
        Compiled Keras model.
    """
    if not TF_AVAILABLE:
        raise ImportError("TensorFlow is required for CNN model.")

    inputs = keras.Input(shape=input_shape, name='input')

    # Block 1
    x = layers.Conv2D(32, (3, 3), padding='same', activation='relu')(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2D(32, (3, 3), padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.25)(x)

    # Block 2
    x = layers.Conv2D(64, (3, 3), padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Conv2D(64, (3, 3), padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(0.25)(x)

    # Classifier
    x = layers.Flatten()(x)
    x = layers.Dense(256, activation='relu')(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(128, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(1, activation='sigmoid', name='output')(x)

    model = keras.Model(inputs=inputs, outputs=outputs,
                        name='eye_state_cnn_advanced')

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.0005),
        loss='binary_crossentropy',
        metrics=['accuracy', keras.metrics.Precision(), keras.metrics.Recall()]
    )

    return model


def load_model(model_path):
    """
    Load a saved CNN model from disk.

    Args:
        model_path: Path to the saved model (.h5 or SavedModel directory).

    Returns:
        Loaded Keras model.
    """
    if not TF_AVAILABLE:
        raise ImportError("TensorFlow is required.")
    return keras.models.load_model(model_path)


def predict_eye_state(model, eye_image):
    """
    Predict eye state (open/closed) for a single eye image.

    Args:
        model: Trained Keras CNN model.
        eye_image: Grayscale eye image (24x24).

    Returns:
        tuple: (prediction_label, confidence)
            prediction_label: 'open' or 'closed'
            confidence: float [0, 1]
    """
    if eye_image.shape != (24, 24):
        import cv2
        eye_image = cv2.resize(eye_image, (24, 24))

    # Normalize and reshape
    img = eye_image.astype('float32') / 255.0
    img = np.expand_dims(img, axis=(0, -1))  # (1, 24, 24, 1)

    prediction = model.predict(img, verbose=0)[0][0]

    if prediction >= 0.5:
        return 'open', float(prediction)
    else:
        return 'closed', float(1 - prediction)


if __name__ == "__main__":
    if TF_AVAILABLE:
        print("Creating CNN model...")
        model = create_cnn_model()
        model.summary()

        print(f"\nTotal Parameters: {model.count_params():,}")
        print("Model created successfully!")

        # Test with random data
        test_input = np.random.rand(1, 24, 24, 1).astype('float32')
        output = model.predict(test_input, verbose=0)
        print(f"Test prediction: {output[0][0]:.4f}")
    else:
        print("TensorFlow not available. Install with: pip install tensorflow")
