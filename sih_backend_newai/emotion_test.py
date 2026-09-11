from transformers import pipeline
import librosa

MODEL = "superb/wav2vec2-base-superb-er"
AUDIO = "test.wav"

print("Loading emotion model...")

classifier = pipeline(
    "audio-classification",
    model=MODEL
)

audio, _ = librosa.load(
    AUDIO,
    sr=16000,
    mono=True
)

results = classifier(
    {"array": audio, "sampling_rate": 16000},
    top_k=None
)

print("\nEMOTION RESULTS:")

for result in results:
    print(
        result["label"],
        round(result["score"] * 100, 2),
        "%"
    )