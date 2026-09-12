import os
import random
import numpy as np
import torch
import soundfile as sf

from transformers import (
    Wav2Vec2ForSequenceClassification,
    Wav2Vec2FeatureExtractor,
)

# ============================================================
# CONFIG
# ============================================================

DATASET_PATH = "datasets"
MODEL_NAME = "superb/wav2vec2-base-superb-er"

SAMPLE_RATE = 16000
TESTS_PER_EMOTION = 10

emotion_map = {
    "01": "neutral",
    "03": "happy",
    "04": "sad",
    "05": "angry",
}

label_map = {
    "neu": "neutral",
    "hap": "happy",
    "sad": "sad",
    "ang": "angry",

    "neutral": "neutral",
    "happy": "happy",
    "sad": "sad",
    "angry": "angry",
}


# ============================================================
# LOAD MODEL
# ============================================================

print("Loading model...")

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

model = Wav2Vec2ForSequenceClassification.from_pretrained(
    MODEL_NAME
)

feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(
    MODEL_NAME
)

model.to(device)
model.eval()

print("Model loaded.")
print("Using:", device)


# ============================================================
# COLLECT FILES
# ============================================================

files_by_emotion = {
    "neutral": [],
    "happy": [],
    "sad": [],
    "angry": [],
}

for actor in os.listdir(DATASET_PATH):

    actor_path = os.path.join(
        DATASET_PATH,
        actor
    )

    if not os.path.isdir(actor_path):
        continue

    for file in os.listdir(actor_path):

        if not file.endswith(".wav"):
            continue

        parts = file.split("-")

        if len(parts) < 3:
            continue

        emotion_code = parts[2]

        if emotion_code not in emotion_map:
            continue

        emotion = emotion_map[
            emotion_code
        ]

        files_by_emotion[
            emotion
        ].append(
            os.path.join(
                actor_path,
                file
            )
        )


# ============================================================
# PREDICTION
# ============================================================

def predict_file(path):

    audio, sr = sf.read(path)

    # Stereo -> mono
    if len(audio.shape) > 1:
        audio = np.mean(
            audio,
            axis=1
        )

    audio = audio.astype(
        np.float32
    )

    # RAVDESS normally uses 48 kHz,
    # so resample if required
    if sr != SAMPLE_RATE:

        from scipy.signal import resample_poly

        audio = resample_poly(
            audio,
            SAMPLE_RATE,
            sr
        )

    inputs = feature_extractor(
        audio,
        sampling_rate=SAMPLE_RATE,
        return_tensors="pt",
        padding=True
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.inference_mode():

        output = model(**inputs)

        probabilities = torch.softmax(
            output.logits,
            dim=-1
        )[0]

    prediction_id = int(
        torch.argmax(
            probabilities
        )
    )

    confidence = float(
        probabilities[
            prediction_id
        ]
    )

    raw_label = model.config.id2label[
        prediction_id
    ]

    predicted = label_map.get(
        raw_label.lower(),
        raw_label.lower()
    )

    return predicted, confidence


# ============================================================
# TEST
# ============================================================

total = 0
correct = 0

class_correct = {
    "neutral": 0,
    "happy": 0,
    "sad": 0,
    "angry": 0,
}

class_total = {
    "neutral": 0,
    "happy": 0,
    "sad": 0,
    "angry": 0,
}


print("\nTESTING\n")

for emotion, files in files_by_emotion.items():

    selected = random.sample(
        files,
        min(
            TESTS_PER_EMOTION,
            len(files)
        )
    )

    print(
        "\n=============================="
    )

    print(
        emotion.upper()
    )

    print(
        "=============================="
    )

    for path in selected:

        predicted, confidence = predict_file(
            path
        )

        total += 1
        class_total[emotion] += 1

        match = predicted == emotion

        if match:

            correct += 1
            class_correct[emotion] += 1

        symbol = "✓" if match else "✗"

        print(
            f"{symbol} "
            f"Actual: {emotion:8s} "
            f"Predicted: {predicted:8s} "
            f"Confidence: "
            f"{confidence * 100:.1f}%"
        )


# ============================================================
# RESULTS
# ============================================================

print(
    "\n\n================================"
)

print(
    "RESULTS"
)

print(
    "================================"
)

overall_accuracy = (
    correct / total
) * 100

print(
    f"\nOverall accuracy: "
    f"{overall_accuracy:.2f}%"
)

print(
    f"Correct: {correct}/{total}"
)

print(
    "\nPer-emotion accuracy:"
)

for emotion in class_total:

    if class_total[emotion] == 0:
        continue

    accuracy = (
        class_correct[emotion]
        / class_total[emotion]
    ) * 100

    print(
        f"{emotion:8s}: "
        f"{accuracy:.2f}% "
        f"({class_correct[emotion]}/"
        f"{class_total[emotion]})"
    )