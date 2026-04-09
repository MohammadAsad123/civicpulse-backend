"""
CivicPulse — Phase 1: Model Inference Utility
Used by the FastAPI backend to classify uploaded complaint images.
Loads the model ONCE at startup and reuses it for all requests.
"""

import json
import numpy as np
from pathlib import Path
import tensorflow as tf
import cv2

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
MODEL_PATH = "app/ml/saved_model/civicpulse_model"
LABELS_PATH = "app/ml/saved_model/class_labels.json"
SEVERITY_PATH = "app/ml/saved_model/severity_weights.json"
IMG_SIZE      = 224
CONFIDENCE_THRESHOLD = 0.60   # below this → manual review queue

# ─────────────────────────────────────────────
# Severity score derived from model confidence
# Confidence 0.60–0.75 → severity 4–6
# Confidence 0.75–0.90 → severity 6–8
# Confidence 0.90–1.00 → severity 8–10
# ─────────────────────────────────────────────
def confidence_to_severity(confidence: float) -> float:
    """Maps model confidence (0–1) to a severity score (1–10)."""
    if confidence < 0.60:
        return 1.0
    # Linear map from [0.60, 1.00] → [4.0, 10.0]
    return round(4.0 + (confidence - 0.60) / 0.40 * 6.0, 2)


# ─────────────────────────────────────────────
# CLASSIFIER CLASS
# Instantiate once and call .predict() per request
# ─────────────────────────────────────────────
class CivicIssueClassifier:
    def __init__(self):
        print("[Classifier] Loading model...")
        self.model = tf.saved_model.load(MODEL_PATH)
        self.infer = self.model.signatures["serving_default"]

        with open(LABELS_PATH) as f:
            self.labels = json.load(f)   # {"0": "garbage_issues", ...}

        with open(SEVERITY_PATH) as f:
            self.severity_base = json.load(f)

        self.class_names = [self.labels[str(i)] for i in range(len(self.labels))]
        print(f"[Classifier] Ready. Classes: {self.class_names}")

    def preprocess(self, image_bytes: bytes) -> np.ndarray:
        """
        Accepts raw image bytes (from file upload).
        Returns preprocessed numpy array ready for inference.
        """
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image. Ensure it is a valid JPEG/PNG.")
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
        img = img.astype(np.float32) / 255.0
        img = np.expand_dims(img, axis=0)   # shape: (1, 224, 224, 3)
        return img

    def predict(self, image_bytes: bytes) -> dict:
        """
        Main inference function. Returns a structured result dict.

        Returns:
        {
            "predicted_class": "water_issues",
            "confidence": 0.87,
            "severity_score": 8.2,
            "all_probabilities": {"road_issues": 0.05, ...},
            "needs_manual_review": False,
            "base_severity_weight": 9
        }
        """
        img_tensor = tf.constant(self.preprocess(image_bytes))

        # Run inference
        output = self.infer(img_tensor)

        # Get probabilities — key name may vary; handle both
        probs_tensor = list(output.values())[0]
        probs = probs_tensor.numpy()[0]   # shape: (num_classes,)

        top_idx   = int(np.argmax(probs))
        confidence = float(probs[top_idx])
        predicted_class = self.class_names[top_idx]

        severity = confidence_to_severity(confidence)
        needs_review = confidence < CONFIDENCE_THRESHOLD or predicted_class == "no_issues"

        all_probs = {
            self.class_names[i]: round(float(probs[i]), 4)
            for i in range(len(self.class_names))
        }

        return {
            "predicted_class":      predicted_class,
            "confidence":           round(confidence, 4),
            "severity_score":       severity,
            "all_probabilities":    all_probs,
            "needs_manual_review":  needs_review,
            "base_severity_weight": self.severity_base.get(predicted_class, 5),
        }


# ─────────────────────────────────────────────
# QUICK TEST — run directly with a test image
# Usage: python classifier.py path/to/image.jpg
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python classifier.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    classifier = CivicIssueClassifier()
    result = classifier.predict(image_bytes)

    print("\n── CivicPulse Classifier Result ──")
    print(f"  Predicted Class    : {result['predicted_class']}")
    print(f"  Confidence         : {result['confidence'] * 100:.1f}%")
    print(f"  Severity Score     : {result['severity_score']} / 10")
    print(f"  Needs Manual Review: {result['needs_manual_review']}")
    print(f"\n  All Probabilities:")
    for cls, prob in sorted(result["all_probabilities"].items(), key=lambda x: -x[1]):
        bar = "█" * int(prob * 30)
        print(f"    {cls:<25} {prob * 100:5.1f}%  {bar}")
