MODEL_ID = "sbh013/wav2vec2-ser-ravdess-optimized"

import torch
import librosa
import numpy as np

from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
