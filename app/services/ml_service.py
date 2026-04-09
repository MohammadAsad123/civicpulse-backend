from app.ml.classifier import CivicIssueClassifier

# Load model once when backend starts
classifier = CivicIssueClassifier()

def classify_image(image_bytes: bytes):
    return classifier.predict(image_bytes)