import sys
import joblib
import opensmile
import pandas as pd


def predict_voice(audio_path):
    smile = opensmile.Smile(
        feature_set=opensmile.FeatureSet.eGeMAPSv02,
        feature_level=opensmile.FeatureLevel.Functionals,
    )

    # Extract 88 acoustic features
    features = smile.process_file(audio_path)

    # The trained model expects columns named "0"..."87"
    X = pd.DataFrame(
        [features.iloc[0].values],
        columns=[str(i) for i in range(88)]
    )

    model = joblib.load("backend/xgboost_model.pkl")

    prediction = int(model.predict(X)[0])

    probabilities = model.predict_proba(X)[0]

    label = "Depression-like voice pattern" if prediction == 1 else "No depression-like voice pattern"

    print("\nPrediction:", label)
    print(f"No-depression probability: {probabilities[0]:.3f}")
    print(f"Depression probability: {probabilities[1]:.3f}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_voice.py <audio.wav>")
        sys.exit(1)

    predict_voice(sys.argv[1])