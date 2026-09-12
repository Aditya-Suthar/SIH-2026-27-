import os
import random
import csv

import numpy as np
import torch
import librosa
import matplotlib.pyplot as plt

from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay
)


# ============================================================
# CONFIGURATION
# ============================================================

# Put the SAME RAVDESS folder path you used in Testing 1 here
DATASET_DIR = r"datasets"

MODEL_NAME = "superb/wav2vec2-base-superb-er"

SAMPLES_PER_EMOTION = 50

RANDOM_SEED = 42

TARGET_EMOTIONS = [
    "neutral",
    "happy",
    "sad",
    "angry"
]


# RAVDESS filename emotion codes
RAVDESS_EMOTION_CODES = {
    "01": "neutral",
    "03": "happy",
    "04": "sad",
    "05": "angry"
}


# ============================================================
# SET RANDOM SEED
# ============================================================

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
torch.manual_seed(RANDOM_SEED)


# ============================================================
# DEVICE
# ============================================================

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("Using device:", device)


# ============================================================
# LOAD MODEL
# ============================================================

print("\nLoading model...")

feature_extractor = AutoFeatureExtractor.from_pretrained(
    MODEL_NAME
)

model = AutoModelForAudioClassification.from_pretrained(
    MODEL_NAME
)

model.to(device)
model.eval()

print("Model loaded successfully.")

print("\nModel labels:")
print(model.config.id2label)


# ============================================================
# NORMALIZE MODEL LABELS
# ============================================================

def normalize_label(label):

    label = label.lower().strip()

    mapping = {
        "neu": "neutral",
        "neutral": "neutral",

        "hap": "happy",
        "happy": "happy",

        "ang": "angry",
        "anger": "angry",
        "angry": "angry",

        "sad": "sad",
        "sadness": "sad"
    }

    return mapping.get(label, label)


# ============================================================
# FIND RAVDESS AUDIO FILES
# ============================================================

emotion_files = {
    "neutral": [],
    "happy": [],
    "sad": [],
    "angry": []
}


print("\nScanning dataset...")


for root, dirs, files in os.walk(DATASET_DIR):

    for filename in files:

        if not filename.lower().endswith(".wav"):
            continue

        name = os.path.splitext(filename)[0]

        parts = name.split("-")

        if len(parts) < 3:
            continue

        # Standard RAVDESS:
        #
        # 03 = audio only
        # 01 = speech
        #
        # We specifically want SPEECH samples.
        if parts[0] != "03":
            continue

        if parts[1] != "01":
            continue

        emotion_code = parts[2]

        if emotion_code not in RAVDESS_EMOTION_CODES:
            continue

        emotion = RAVDESS_EMOTION_CODES[emotion_code]

        filepath = os.path.join(root, filename)

        emotion_files[emotion].append(filepath)


print("\nAvailable samples:")

for emotion in TARGET_EMOTIONS:
    print(
        f"{emotion.capitalize():8s}: "
        f"{len(emotion_files[emotion])}"
    )


# ============================================================
# SELECT RANDOM SAMPLES
# ============================================================

selected_files = []

for emotion in TARGET_EMOTIONS:

    files = emotion_files[emotion]

    sample_count = min(
        SAMPLES_PER_EMOTION,
        len(files)
    )

    selected = random.sample(
        files,
        sample_count
    )

    for filepath in selected:

        selected_files.append(
            (emotion, filepath)
        )


# Shuffle the complete test set
random.shuffle(selected_files)


print(
    "\nTotal Testing 2 samples:",
    len(selected_files)
)


# ============================================================
# MODEL PREDICTION FUNCTION
# ============================================================

def predict_emotion(filepath):

    audio, sr = librosa.load(
        filepath,
        sr=16000,
        mono=True
    )

    inputs = feature_extractor(
        audio,
        sampling_rate=16000,
        return_tensors="pt",
        padding=True
    )

    input_values = inputs["input_values"].to(device)

    attention_mask = inputs.get("attention_mask")

    if attention_mask is not None:
        attention_mask = attention_mask.to(device)

    with torch.no_grad():

        if attention_mask is not None:

            outputs = model(
                input_values,
                attention_mask=attention_mask
            )

        else:

            outputs = model(
                input_values
            )

    probabilities = torch.softmax(
        outputs.logits,
        dim=-1
    )

    confidence, predicted_id = torch.max(
        probabilities,
        dim=-1
    )

    predicted_id = predicted_id.item()

    confidence = confidence.item()

    raw_label = model.config.id2label[predicted_id]

    predicted_emotion = normalize_label(
        raw_label
    )

    return predicted_emotion, confidence


# ============================================================
# RUN TESTING
# ============================================================

actual_labels = []
predicted_labels = []

results = []


print("\n")
print("=" * 70)
print("TESTING 2 — LARGE-SAMPLE SER EVALUATION")
print("=" * 70)


for index, (actual, filepath) in enumerate(
    selected_files,
    start=1
):

    try:

        predicted, confidence = predict_emotion(
            filepath
        )

        correct = actual == predicted

        symbol = "✓" if correct else "✗"

        print(
            f"[{index:03d}/{len(selected_files)}] "
            f"{symbol} "
            f"Actual: {actual:7s} | "
            f"Predicted: {predicted:7s} | "
            f"Confidence: {confidence * 100:.1f}%"
        )

        actual_labels.append(actual)

        predicted_labels.append(predicted)

        results.append({
            "file": os.path.basename(filepath),
            "actual": actual,
            "predicted": predicted,
            "confidence": round(
                confidence * 100,
                2
            ),
            "correct": correct
        })

    except Exception as e:

        print(
            f"ERROR processing {filepath}: {e}"
        )


# ============================================================
# OVERALL ACCURACY
# ============================================================

accuracy = accuracy_score(
    actual_labels,
    predicted_labels
)


print("\n")
print("=" * 70)
print("TESTING 2 RESULTS")
print("=" * 70)

print(
    f"\nOverall Accuracy: "
    f"{accuracy * 100:.2f}%"
)


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

report = classification_report(
    actual_labels,
    predicted_labels,
    labels=TARGET_EMOTIONS,
    zero_division=0
)

print("\nClassification Report:\n")

print(report)


# ============================================================
# CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(
    actual_labels,
    predicted_labels,
    labels=TARGET_EMOTIONS
)


print("\nConfusion Matrix:\n")

print(cm)


# ============================================================
# PER-EMOTION ACCURACY
# ============================================================

print("\nPer-Emotion Accuracy:\n")

per_emotion_accuracy = {}

for i, emotion in enumerate(TARGET_EMOTIONS):

    total = cm[i].sum()

    correct = cm[i][i]

    emotion_accuracy = (
        correct / total
        if total > 0
        else 0
    )

    per_emotion_accuracy[emotion] = emotion_accuracy

    print(
        f"{emotion.capitalize():8s}: "
        f"{correct}/{total} "
        f"({emotion_accuracy * 100:.2f}%)"
    )


# ============================================================
# AVERAGE CONFIDENCE
# ============================================================

average_confidence = np.mean(
    [
        result["confidence"]
        for result in results
    ]
)

print(
    f"\nAverage Model Confidence: "
    f"{average_confidence:.2f}%"
)


# ============================================================
# SAVE CSV RESULTS
# ============================================================

csv_filename = "testing2_results.csv"

with open(
    csv_filename,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=[
            "file",
            "actual",
            "predicted",
            "confidence",
            "correct"
        ]
    )

    writer.writeheader()

    writer.writerows(results)


print(
    f"\nDetailed predictions saved to "
    f"{csv_filename}"
)


# ============================================================
# SAVE CONFUSION MATRIX IMAGE
# ============================================================

display = ConfusionMatrixDisplay(
    confusion_matrix=cm,
    display_labels=[
        "Neutral",
        "Happy",
        "Sad",
        "Angry"
    ]
)

fig, ax = plt.subplots(
    figsize=(8, 6)
)

display.plot(
    ax=ax,
    values_format="d"
)

plt.title(
    "Testing 2 — Speech Emotion Recognition Confusion Matrix"
)

plt.tight_layout()

matrix_filename = (
    "testing2_confusion_matrix.png"
)

plt.savefig(
    matrix_filename,
    dpi=300
)

plt.close()


print(
    f"Confusion matrix saved to "
    f"{matrix_filename}"
)


# ============================================================
# SAVE SUMMARY TEXT FILE
# ============================================================

summary_filename = "testing2_summary.txt"

with open(
    summary_filename,
    "w",
    encoding="utf-8"
) as file:

    file.write(
        "TESTING 2 — LARGE-SAMPLE SPEECH EMOTION "
        "RECOGNITION EVALUATION\n\n"
    )

    file.write(
        f"Model: {MODEL_NAME}\n"
    )

    file.write(
        f"Total Samples: "
        f"{len(actual_labels)}\n"
    )

    file.write(
        f"Samples per emotion: "
        f"{SAMPLES_PER_EMOTION}\n\n"
    )

    file.write(
        f"Overall Accuracy: "
        f"{accuracy * 100:.2f}%\n"
    )

    file.write(
        f"Average Confidence: "
        f"{average_confidence:.2f}%\n\n"
    )

    file.write(
        "Per-Emotion Accuracy:\n"
    )

    for emotion, value in per_emotion_accuracy.items():

        file.write(
            f"{emotion.capitalize()}: "
            f"{value * 100:.2f}%\n"
        )

    file.write(
        "\nClassification Report:\n\n"
    )

    file.write(report)


print(
    f"Summary saved to "
    f"{summary_filename}"
)


print("\n")
print("=" * 70)
print("TESTING 2 COMPLETE")
print("=" * 70)