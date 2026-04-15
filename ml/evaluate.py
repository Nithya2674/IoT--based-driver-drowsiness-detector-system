"""
Model Evaluation Module
========================
Provides comprehensive evaluation metrics, visualizations,
and reports for the drowsiness detection CNN model.

Usage:
    python evaluate.py                  # Evaluate with synthetic data
    python evaluate.py --model-path models/eye_state_cnn.h5
"""

import os
import json
import argparse
import numpy as np

try:
    import tensorflow as tf
    from tensorflow import keras
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    PLT_AVAILABLE = True
except ImportError:
    PLT_AVAILABLE = False

from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_curve, auc, precision_recall_curve
)

from cnn_model import create_cnn_model
from train_cnn import create_synthetic_dataset


RESULTS_DIR = os.path.join(os.path.dirname(__file__), "evaluation_results")


def evaluate_model(model_path=None, X_test=None, y_test=None):
    """
    Comprehensive model evaluation with metrics and visualizations.

    Args:
        model_path: Path to saved model. If None, trains a fresh model on synthetic data.
        X_test: Test images. If None, generates synthetic data.
        y_test: Test labels.

    Returns:
        dict: Evaluation metrics.
    """
    if not TF_AVAILABLE:
        print("[ERROR] TensorFlow is required.")
        return None

    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Load or create model
    if model_path and os.path.exists(model_path):
        print(f"[INFO] Loading model from {model_path}")
        model = keras.models.load_model(model_path)
    else:
        print("[INFO] No model found. Training on synthetic data for evaluation demo...")
        model = create_cnn_model()
        X_train, X_test_gen, y_train, y_test_gen = create_synthetic_dataset(2000)
        model.fit(X_train, y_train, epochs=15, batch_size=32,
                  validation_split=0.2, verbose=1)
        if X_test is None:
            X_test = X_test_gen
            y_test = y_test_gen

    # Generate test data if not provided
    if X_test is None:
        _, X_test, _, y_test = create_synthetic_dataset(1000)

    # ─── Predictions ──────────────────────────────────────────────
    y_pred_prob = model.predict(X_test, verbose=0).flatten()
    y_pred = (y_pred_prob >= 0.5).astype(int)
    y_true = y_test.astype(int)

    # ─── Classification Report ────────────────────────────────────
    report = classification_report(
        y_true, y_pred,
        target_names=['Closed', 'Open'],
        output_dict=True
    )
    report_text = classification_report(
        y_true, y_pred,
        target_names=['Closed', 'Open']
    )

    print("\n" + "=" * 60)
    print("  MODEL EVALUATION RESULTS")
    print("=" * 60)
    print("\nClassification Report:")
    print(report_text)

    # ─── Confusion Matrix ─────────────────────────────────────────
    cm = confusion_matrix(y_true, y_pred)
    print("Confusion Matrix:")
    print(f"  TN={cm[0][0]:4d}  FP={cm[0][1]:4d}")
    print(f"  FN={cm[1][0]:4d}  TP={cm[1][1]:4d}")

    # ─── Key Metrics ──────────────────────────────────────────────
    accuracy = report['accuracy']
    precision = report['Open']['precision']
    recall = report['Open']['recall']
    f1 = report['Open']['f1-score']

    metrics = {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
        "total_test_samples": len(y_test),
    }

    print(f"\n  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1-Score:  {f1:.4f}")

    # ─── Visualizations ──────────────────────────────────────────
    if PLT_AVAILABLE:
        # 1. Confusion Matrix Heatmap
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        im = axes[0].imshow(cm, interpolation='nearest', cmap='Blues')
        axes[0].set_title('Confusion Matrix', fontsize=14, fontweight='bold')
        axes[0].set_ylabel('True Label')
        axes[0].set_xlabel('Predicted Label')
        axes[0].set_xticks([0, 1])
        axes[0].set_yticks([0, 1])
        axes[0].set_xticklabels(['Closed', 'Open'])
        axes[0].set_yticklabels(['Closed', 'Open'])
        for i in range(2):
            for j in range(2):
                axes[0].text(j, i, str(cm[i][j]),
                           ha='center', va='center', fontsize=16,
                           color='white' if cm[i][j] > cm.max()/2 else 'black')
        plt.colorbar(im, ax=axes[0])

        # 2. ROC Curve
        fpr, tpr, _ = roc_curve(y_true, y_pred_prob)
        roc_auc = auc(fpr, tpr)
        axes[1].plot(fpr, tpr, color='#FF6B6B', lw=2,
                     label=f'ROC (AUC = {roc_auc:.3f})')
        axes[1].plot([0, 1], [0, 1], 'k--', lw=1)
        axes[1].set_xlabel('False Positive Rate')
        axes[1].set_ylabel('True Positive Rate')
        axes[1].set_title('ROC Curve', fontsize=14, fontweight='bold')
        axes[1].legend(loc='lower right')
        axes[1].grid(True, alpha=0.3)
        metrics['auc_roc'] = round(roc_auc, 4)

        # 3. Precision-Recall Curve
        prec, rec, _ = precision_recall_curve(y_true, y_pred_prob)
        pr_auc = auc(rec, prec)
        axes[2].plot(rec, prec, color='#4ECDC4', lw=2,
                     label=f'PR (AUC = {pr_auc:.3f})')
        axes[2].set_xlabel('Recall')
        axes[2].set_ylabel('Precision')
        axes[2].set_title('Precision-Recall Curve', fontsize=14, fontweight='bold')
        axes[2].legend(loc='lower left')
        axes[2].grid(True, alpha=0.3)
        metrics['auc_pr'] = round(pr_auc, 4)

        plt.tight_layout()
        fig_path = os.path.join(RESULTS_DIR, "evaluation_plots.png")
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n[INFO] Plots saved to: {fig_path}")

    # ─── Training History Plot ────────────────────────────────────
    history_path = os.path.join(os.path.dirname(__file__),
                                "models", "training_history.json")
    if PLT_AVAILABLE and os.path.exists(history_path):
        with open(history_path, 'r') as f:
            history = json.load(f)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Accuracy plot
        ax1.plot(history['accuracy'], label='Train Accuracy', color='#FF6B6B')
        ax1.plot(history['val_accuracy'], label='Val Accuracy', color='#4ECDC4')
        ax1.set_title('Model Accuracy Over Epochs', fontweight='bold')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Accuracy')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Loss plot
        ax2.plot(history['loss'], label='Train Loss', color='#FF6B6B')
        ax2.plot(history['val_loss'], label='Val Loss', color='#4ECDC4')
        ax2.set_title('Model Loss Over Epochs', fontweight='bold')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Loss')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        hist_fig_path = os.path.join(RESULTS_DIR, "training_history.png")
        plt.savefig(hist_fig_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[INFO] Training history plot saved to: {hist_fig_path}")

    # ─── Sample Predictions ───────────────────────────────────────
    if PLT_AVAILABLE and len(X_test) >= 16:
        fig, axes = plt.subplots(2, 8, figsize=(16, 4))
        indices = np.random.choice(len(X_test), 16, replace=False)

        for i, idx in enumerate(indices):
            ax = axes[i // 8][i % 8]
            img = X_test[idx].squeeze()
            pred = y_pred[idx]
            true = y_true[idx]
            prob = y_pred_prob[idx]

            ax.imshow(img, cmap='gray')
            label = 'O' if pred == 1 else 'C'
            color = 'green' if pred == true else 'red'
            ax.set_title(f'{label} ({prob:.2f})', fontsize=8, color=color)
            ax.axis('off')

        plt.suptitle('Sample Predictions (Green=Correct, Red=Wrong)',
                     fontweight='bold')
        plt.tight_layout()
        samples_path = os.path.join(RESULTS_DIR, "sample_predictions.png")
        plt.savefig(samples_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[INFO] Sample predictions saved to: {samples_path}")

    # ─── Save Metrics ─────────────────────────────────────────────
    metrics_path = os.path.join(RESULTS_DIR, "metrics.json")
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"[INFO] Metrics saved to: {metrics_path}")

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Model Evaluation")
    parser.add_argument("--model-path", type=str,
                        default=os.path.join(os.path.dirname(__file__),
                                             "models", "eye_state_cnn.h5"),
                        help="Path to the trained model")
    args = parser.parse_args()

    evaluate_model(model_path=args.model_path)
