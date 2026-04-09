import random


def classify_image(image_bytes):

    labels = ["road_issue", "garbage_issue"]

    label = random.choice(labels)
    confidence = round(random.uniform(0.6, 0.95), 2)

    severity_score = round(confidence, 2)

    manual_review = confidence < 0.6

    return {
        "label": label,
        "confidence": confidence,
        "severity_score": severity_score,
        "manual_review": manual_review
    }