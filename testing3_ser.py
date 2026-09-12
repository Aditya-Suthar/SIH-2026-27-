#!/usr/bin/env python3
"""Testing 3: fixed-sample, audio-only, cross-corpus SER evaluation.

Install in a fresh Python 3.11/3.12 virtual environment (Windows supported):
  python -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu
  python -m pip install speechbrain==1.0.3 transformers==4.57.6 huggingface-hub==0.36.0 librosa==0.11.0 soundfile==0.13.1 numpy==2.2.6 scipy==1.15.3 scikit-learn==1.7.2 matplotlib==3.10.7

Run the predeclared comparison candidate (no optional waveform processing):
  python testing3_ser.py --dataset-dir datasets --device cpu
Re-run SUPERB with its original feature-extractor configuration:
  python testing3_ser.py --dataset-dir datasets --model superb --output-dir testing3_superb
Optional exploratory ablations, EACH in a separate directory:
  python testing3_ser.py --dataset-dir datasets --model superb --preprocess trim --output-dir testing3_trim
  python testing3_ser.py --dataset-dir datasets --model superb --preprocess peak --output-dir testing3_peak
Audio/sample validation without downloading models:
  python testing3_ser.py --dataset-dir datasets --audit-only --output-dir testing3_audit

Selection: explicit --testing2-csv > testing2_results.csv in CWD/script folder
> embedded filenames from the user's attached Testing 2 CSV > seeded sampling
if the embedded list is removed for reuse on another project. --new-sample-set
explicitly requests sorted, seed-42 sampling and disables paired-baseline claims.
An existing invalid CSV or missing selected WAV aborts; it never falls back.

The embedded data contains FILENAMES ONLY, never desired model outputs.
Predictors receive only a float32 mono waveform, never a path or actual label.
Confidence is uncalibrated maximum softmax probability, saved in percent.
No audio is sent to an inference service. Initial model downloads need internet.

Sources checked 2026-09-11:
https://zenodo.org/records/1188976
https://huggingface.co/superb/wav2vec2-base-superb-er
https://huggingface.co/superb/wav2vec2-base-superb-er/raw/main/preprocessor_config.json
https://huggingface.co/speechbrain/emotion-recognition-wav2vec2-IEMOCAP
https://huggingface.co/speechbrain/emotion-recognition-wav2vec2-IEMOCAP/raw/main/custom_interface.py
https://huggingface.co/speechbrain/emotion-recognition-wav2vec2-IEMOCAP/raw/main/hyperparams.yaml

Both checkpoints document IEMOCAP emotion training, not RAVDESS. SpeechBrain is
an independently fine-tuned base-size candidate, not a proven RAVDESS upgrade.
Its model card contains unrelated speaker-verification boilerplate: this script
follows the actual hyperparameters and forward pass instead. Do not transfer
its IEMOCAP accuracy to RAVDESS. Report all ablations; choosing a winner on these
200 cases makes them a development benchmark. Final claims need a new held-out
set, preferably actor-disjoint. These are emotion metrics, not distress accuracy.

Verification: selection, metrics, failure guards and synthetic audio preprocessing
can be tested independently. Actual model accuracy requires the user's WAV files.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import re
import sys
import time
import traceback

RANDOM_SEED = 42
EMOTIONS = ('neutral', 'happy', 'sad', 'angry')
CODES = {'01': 'neutral', '03': 'happy', '04': 'sad', '05': 'angry'}
MODELS = {'superb': 'superb/wav2vec2-base-superb-er',
          'speechbrain': 'speechbrain/emotion-recognition-wav2vec2-IEMOCAP'}
BASE_CM = [[32, 2, 0, 16], [10, 8, 0, 32], [9, 21, 2, 18], [2, 1, 0, 47]]
# Replaced below during creation with the 200 supplied filenames, in CSV order.
EMBEDDED_TESTING2_FILES = tuple("""
03-01-05-01-02-02-07.wav
03-01-04-01-01-01-03.wav
03-01-04-01-02-02-09.wav
03-01-03-02-01-01-09.wav
03-01-01-01-02-02-19.wav
03-01-01-01-02-02-01.wav
03-01-04-01-01-02-24.wav
03-01-05-01-01-02-22.wav
03-01-04-02-01-02-23.wav
03-01-04-02-01-02-21.wav
03-01-04-02-01-01-23.wav
03-01-05-01-02-02-23.wav
03-01-04-01-01-01-08.wav
03-01-05-01-02-01-18.wav
03-01-01-01-01-02-24.wav
03-01-04-02-01-01-14.wav
03-01-01-01-01-01-05.wav
03-01-03-01-02-02-06.wav
03-01-05-02-01-02-08.wav
03-01-01-01-01-02-07.wav
03-01-01-01-02-01-06.wav
03-01-04-01-02-02-05.wav
03-01-03-02-02-01-20.wav
03-01-01-01-01-02-18.wav
03-01-04-01-02-02-21.wav
03-01-01-01-02-01-01.wav
03-01-05-02-01-01-18.wav
03-01-01-01-02-01-10.wav
03-01-04-02-02-01-13.wav
03-01-03-01-01-02-13.wav
03-01-04-01-01-01-17.wav
03-01-04-01-01-01-09.wav
03-01-01-01-02-01-20.wav
03-01-03-01-02-01-12.wav
03-01-04-01-01-01-22.wav
03-01-05-02-01-02-03.wav
03-01-05-02-02-02-08.wav
03-01-03-01-01-02-06.wav
03-01-04-02-02-02-18.wav
03-01-03-01-01-01-22.wav
03-01-01-01-01-01-06.wav
03-01-03-01-02-01-03.wav
03-01-05-02-01-01-14.wav
03-01-03-01-01-01-08.wav
03-01-03-02-02-01-08.wav
03-01-03-02-01-02-18.wav
03-01-01-01-02-02-22.wav
03-01-03-02-01-02-22.wav
03-01-05-01-02-02-21.wav
03-01-01-01-02-02-05.wav
03-01-05-01-02-01-07.wav
03-01-01-01-01-02-16.wav
03-01-05-02-02-02-05.wav
03-01-03-02-02-01-07.wav
03-01-04-02-01-01-02.wav
03-01-01-01-01-01-07.wav
03-01-05-02-02-02-17.wav
03-01-04-01-01-01-21.wav
03-01-01-01-02-02-08.wav
03-01-04-01-01-01-06.wav
03-01-03-02-01-01-23.wav
03-01-03-01-01-01-02.wav
03-01-01-01-02-02-21.wav
03-01-01-01-01-02-02.wav
03-01-05-02-02-01-04.wav
03-01-03-01-01-01-13.wav
03-01-03-02-01-01-15.wav
03-01-04-02-01-02-19.wav
03-01-04-02-01-01-09.wav
03-01-01-01-01-01-24.wav
03-01-05-01-01-01-18.wav
03-01-03-01-01-01-19.wav
03-01-03-01-02-02-08.wav
03-01-03-01-01-01-18.wav
03-01-03-01-02-02-20.wav
03-01-03-01-02-02-10.wav
03-01-04-02-01-01-12.wav
03-01-05-02-01-01-17.wav
03-01-05-02-01-01-10.wav
03-01-03-01-01-01-03.wav
03-01-01-01-01-02-19.wav
03-01-03-02-01-02-12.wav
03-01-04-01-01-01-20.wav
03-01-03-02-01-01-03.wav
03-01-01-01-02-02-11.wav
03-01-03-02-02-01-18.wav
03-01-03-02-01-02-07.wav
03-01-05-01-01-02-16.wav
03-01-04-02-01-02-18.wav
03-01-01-01-02-02-03.wav
03-01-03-02-02-01-24.wav
03-01-03-02-01-01-19.wav
03-01-01-01-02-02-18.wav
03-01-03-01-01-02-04.wav
03-01-03-01-02-01-10.wav
03-01-03-01-02-02-02.wav
03-01-04-02-02-02-15.wav
03-01-01-01-01-02-05.wav
03-01-04-02-02-02-16.wav
03-01-01-01-02-01-15.wav
03-01-03-02-01-01-21.wav
03-01-05-02-02-02-12.wav
03-01-03-02-02-02-09.wav
03-01-03-02-02-01-13.wav
03-01-03-02-02-01-12.wav
03-01-01-01-01-02-04.wav
03-01-05-01-01-01-21.wav
03-01-01-01-02-01-02.wav
03-01-05-01-01-01-01.wav
03-01-05-02-01-02-23.wav
03-01-05-02-01-01-04.wav
03-01-03-01-02-01-23.wav
03-01-05-02-01-01-24.wav
03-01-04-02-02-02-14.wav
03-01-04-02-02-01-16.wav
03-01-03-01-01-01-11.wav
03-01-03-01-02-02-11.wav
03-01-04-01-02-01-13.wav
03-01-01-01-01-02-06.wav
03-01-05-01-02-01-06.wav
03-01-05-02-01-01-01.wav
03-01-04-02-02-02-21.wav
03-01-04-01-02-02-10.wav
03-01-05-02-02-01-02.wav
03-01-05-01-01-02-17.wav
03-01-01-01-01-02-21.wav
03-01-05-02-02-02-10.wav
03-01-04-02-02-02-17.wav
03-01-05-02-02-01-24.wav
03-01-04-02-01-02-13.wav
03-01-05-01-01-02-19.wav
03-01-04-02-01-01-04.wav
03-01-05-02-01-01-03.wav
03-01-05-02-01-02-16.wav
03-01-01-01-02-01-17.wav
03-01-05-01-01-02-03.wav
03-01-01-01-01-02-14.wav
03-01-01-01-02-02-09.wav
03-01-01-01-02-01-14.wav
03-01-05-01-02-02-20.wav
03-01-04-02-01-02-14.wav
03-01-01-01-02-02-24.wav
03-01-05-01-02-02-04.wav
03-01-04-01-01-01-24.wav
03-01-05-02-01-01-16.wav
03-01-01-01-02-01-12.wav
03-01-05-01-02-01-23.wav
03-01-01-01-01-01-13.wav
03-01-04-01-02-02-23.wav
03-01-04-01-02-01-01.wav
03-01-05-01-02-01-11.wav
03-01-01-01-02-02-02.wav
03-01-03-01-02-01-08.wav
03-01-01-01-01-01-01.wav
03-01-05-01-02-02-15.wav
03-01-04-02-01-01-21.wav
03-01-05-01-02-02-09.wav
03-01-01-01-01-02-15.wav
03-01-01-01-01-01-02.wav
03-01-04-01-02-01-17.wav
03-01-04-02-01-01-05.wav
03-01-04-02-02-02-08.wav
03-01-03-02-02-01-02.wav
03-01-04-01-01-02-18.wav
03-01-05-01-01-02-20.wav
03-01-01-01-02-01-23.wav
03-01-01-01-02-01-09.wav
03-01-04-02-01-02-15.wav
03-01-05-02-01-01-12.wav
03-01-03-01-01-02-22.wav
03-01-04-02-02-02-03.wav
03-01-04-01-01-01-01.wav
03-01-04-02-01-01-15.wav
03-01-01-01-01-01-23.wav
03-01-04-02-01-02-04.wav
03-01-03-01-01-01-21.wav
03-01-04-02-02-02-05.wav
03-01-05-02-02-01-10.wav
03-01-03-01-02-01-21.wav
03-01-03-01-01-02-03.wav
03-01-04-01-01-02-13.wav
03-01-05-02-02-01-07.wav
03-01-03-02-02-01-15.wav
03-01-01-01-02-01-22.wav
03-01-01-01-01-02-08.wav
03-01-05-02-02-01-13.wav
03-01-01-01-01-02-22.wav
03-01-05-01-01-02-06.wav
03-01-05-01-01-01-05.wav
03-01-01-01-01-01-17.wav
03-01-01-01-02-01-04.wav
03-01-03-02-01-01-12.wav
03-01-05-01-01-01-15.wav
03-01-03-01-01-02-07.wav
03-01-04-02-02-02-11.wav
03-01-05-02-01-02-06.wav
03-01-01-01-01-01-08.wav
03-01-03-02-01-02-09.wav
03-01-01-01-02-02-07.wav
03-01-03-01-02-02-19.wav
""".split())


def filename_only(value):
    return str(value).strip().replace('\\', '/').rsplit('/', 1)[-1]


def ravdess_label(name):
    match = re.fullmatch(r'03-01-(01|03|04|05)-(01|02)-(01|02)-(01|02)-(\d{2})\.wav', name, re.I)
    if not match:
        raise ValueError(f'Invalid target RAVDESS audio-speech filename: {name}')
    emotion, intensity, _, _, actor = match.groups()
    if not 1 <= int(actor) <= 24 or (emotion == '01' and intensity != '01'):
        raise ValueError(f'Invalid RAVDESS actor/intensity: {name}')
    return CODES[emotion]


def canonical_label(label):
    aliases = {'neu': 'neutral', 'neutral': 'neutral', 'hap': 'happy',
               'happy': 'happy', 'sad': 'sad', 'sadness': 'sad',
               'ang': 'angry', 'anger': 'angry', 'angry': 'angry'}
    try:
        return aliases[str(label).lower().strip()]
    except KeyError:
        raise ValueError(f'Unrecognized model label {label!r}; refusing to guess its meaning.') from None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def json_safe(obj):
    if isinstance(obj, set):
        return sorted(obj)

    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, tuple):
        return list(obj)

    if hasattr(obj, "tolist"):
        return obj.tolist()

    return str(obj)


def write_json(path, obj):
    temporary = path.with_suffix(path.suffix + '.tmp')

    temporary.write_text(
        json.dumps(
            obj,
            indent=2,
            ensure_ascii=False,
            default=json_safe
        ),
        encoding='utf-8'
    )

    temporary.replace(path)


def choose_samples(args):
    root = Path(args.dataset_dir).resolve()
    if not root.is_dir():
        raise ValueError(f'Dataset folder does not exist: {root}')
    index = collections.defaultdict(list)
    for path in sorted(root.rglob('*')):
        if path.is_file() and path.suffix.lower() == '.wav':
            try:
                ravdess_label(path.name)
            except ValueError:
                continue
            index[path.name].append(path)
    available = collections.Counter(ravdess_label(n) for n in index)
    print('Available unique target files:', dict(available), flush=True)
    names = None
    if args.new_sample_set:
        source = 'New sorted seed-42 sample; historical comparison is unpaired.'
    else:
        if args.testing2_csv:
            csv_path = Path(args.testing2_csv)
            if not csv_path.is_file():
                raise ValueError(f'Explicit Testing 2 CSV not found: {csv_path}')
        else:
            csv_path = next((p for p in [Path('testing2_results.csv'),
                             Path(__file__).resolve().parent / 'testing2_results.csv']
                             if p.is_file()), None)
        if csv_path is not None:
            with csv_path.open(newline='', encoding='utf-8-sig') as stream:
                reader = csv.DictReader(stream)
                column = next((c for c in ('filename', 'file', 'filepath')
                               if c in (reader.fieldnames or [])), None)
                if column is None:
                    raise ValueError('CSV requires filename, file, or filepath column.')
                names = []
                for row in reader:
                    name = filename_only(row[column])
                    actual = ravdess_label(name)
                    if row.get('actual') and canonical_label(row['actual']) != actual:
                        raise ValueError(f'CSV actual label disagrees with filename: {name}')
                    names.append(name)
            source = f'Existing CSV: {csv_path.resolve()}'
        elif EMBEDDED_TESTING2_FILES:
            names = list(EMBEDDED_TESTING2_FILES)
            source = 'Exact 200 filenames embedded from supplied Testing 2 results'
        else:
            source = 'No prior manifest available; new sorted seed-42 sample (unpaired).'
    if names is None:
        rng = random.Random(RANDOM_SEED)
        names = []
        for emotion in EMOTIONS:
            pool = sorted(n for n in index if ravdess_label(n) == emotion)
            if len(pool) < 50:
                raise ValueError(f'{emotion}: need 50 unique files, found {len(pool)}.')
            names.extend(rng.sample(pool, 50))
        rng.shuffle(names)
    counts = collections.Counter(ravdess_label(n) for n in names)
    if len(names) != 200 or len(set(names)) != 200 or counts != dict.fromkeys(EMOTIONS, 50):
        raise ValueError(f'Test set must contain 200 unique files and exactly 50/class: {counts}')
    paths = []
    for name in names:
        matches = index.get(name, [])
        if len(matches) != 1:
            raise ValueError(f'{name}: found {len(matches)} matches; need exactly one. '
                             'Use a dataset root containing a single copy of each selected WAV.')
        paths.append(matches[0])
    same = bool(EMBEDDED_TESTING2_FILES) and set(names) == set(EMBEDDED_TESTING2_FILES)
    return paths, source, same


def load_audio(path, preprocess):
    """Audio-only validation/transform. No emotion or filename-dependent operation."""
    import numpy as np
    import soundfile as sf
    import librosa
    audio, sr = sf.read(path, dtype='float32', always_2d=True)
    if not 8000 <= sr <= 192000:
        raise ValueError(f'Unexpected sample rate: {sr}')
    if len(audio) == 0 or not np.isfinite(audio).all():
        raise ValueError('Empty audio or NaN/Inf samples.')
    peak = float(np.max(np.abs(audio)))
    if peak > 1.00001:
        raise ValueError('Source samples exceed [-1,1]; inspect encoding instead of silently clipping.')
    mono = audio.mean(axis=1, dtype=np.float32)
    rms = float(np.sqrt(np.mean(mono.astype(np.float64)**2)))
    notes = []
    if peak == 0 or float(np.std(mono)) < 1e-10:
        raise ValueError('Silent/constant waveform or destructive channel cancellation.')
    if rms < 1e-4:
        notes.append('Very quiet (< -80 dBFS RMS); retained without automatic gain')
    channel_rms = float(np.sqrt(np.mean(audio.astype(np.float64)**2)))
    if audio.shape[1] > 1 and rms < channel_rms * 0.1:
        notes.append('Possible phase cancellation during mono averaging; inspect source')
    clipping_fraction = float(np.mean(np.abs(audio) >= 0.999))
    if clipping_fraction:
        notes.append('Near-full-scale samples; possible clipping (not repaired)')
    if sr != 16000:
        mono = librosa.resample(mono, orig_sr=sr, target_sr=16000, res_type='soxr_hq')
    mono = np.ascontiguousarray(mono, dtype=np.float32)
    if len(mono) < 1600:
        raise ValueError('Audio shorter than 100 ms; cannot evaluate as a speech utterance.')
    # Fixed, exploratory boundary detector: relative RMS, never deletes internal pauses.
    # A 40 dB threshold and 150 ms guard are declared before evaluation, not optimized here.
    _, bounds = librosa.effects.trim(mono, top_db=40, frame_length=400, hop_length=160)
    start = max(0, int(bounds[0]) - 2400)
    stop = min(len(mono), int(bounds[1]) + 2400)
    frame_rms = librosa.feature.rms(y=mono, frame_length=400, hop_length=160)[0]
    quiet_fraction = float(np.mean(frame_rms < float(frame_rms.max()) * 0.01))
    if quiet_fraction > 0.5:
        notes.append('More than 50% low-energy frames; retained unless trim ablation selected')
    resampled_length = len(mono)
    removed = 0
    if preprocess == 'trim':
        if stop - start < 1600:
            raise ValueError('Boundary trimming would leave less than 100 ms.')
        removed = len(mono) - (stop - start)
        mono = mono[start:stop]
    gain = 1.0
    if preprocess == 'peak':
        # Gain capped at 20 dB to avoid extreme amplification of quiet/noisy files.
        gain = min(10.0, 0.95 / float(np.max(np.abs(mono))))
        mono = mono * gain
    if not np.isfinite(mono).all():
        raise ValueError('Non-finite output after preprocessing.')
    # Sinc resampling may slightly overshoot source peaks; do not hard-clip it.
    audit = {'original_sample_rate': int(sr), 'channels': int(audio.shape[1]),
             'original_duration_s': len(audio)/sr, 'source_peak': peak,
             'mono_rms_dbfs': float(20*np.log10(max(rms, 1e-12))),
             'near_full_scale_fraction': clipping_fraction,
             'low_energy_frame_fraction': quiet_fraction,
             'leading_boundary_s': start/16000, 'trailing_boundary_s': (resampled_length-stop)/16000,
             'removed_seconds': removed/16000, 'gain': gain,
             'processed_duration_s': len(mono)/16000,
             'processed_peak': float(np.max(np.abs(mono))), 'warnings': notes}
    return np.ascontiguousarray(mono, dtype=np.float32), audit


def load_predictor(args, out, device):
    """Return an audio-only callable and the fully resolved model metadata."""
    import numpy as np
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
    repo = MODELS[args.model]
    patterns = (['*.json', '*.bin', '*.safetensors'] if args.model == 'superb'
                else ['hyperparams.yaml', 'label_encoder.txt', '*.ckpt'])
    print(f'Loading {repo} (first run downloads weights)...', flush=True)
    snapshot = Path(snapshot_download(repo, revision=args.revision, allow_patterns=patterns))
    metadata = {'model': repo, 'resolved_revision': snapshot.name, 'sample_rate': 16000,
                'training_provenance': 'Documented IEMOCAP SER training; no documented RAVDESS training'}
    if args.model == 'superb':
        extractor = AutoFeatureExtractor.from_pretrained(snapshot, local_files_only=True)
        if extractor.sampling_rate != 16000:
            raise ValueError('Unexpected extractor sample rate; review model revision.')
        model, loading = AutoModelForAudioClassification.from_pretrained(
            snapshot, local_files_only=True, output_loading_info=True)
        if loading.get('missing_keys') or loading.get('mismatched_keys') or loading.get('error_msgs'):
            raise ValueError(f'Incomplete model checkpoint load: {loading}')
        labels = [canonical_label(model.config.id2label[i]) for i in range(model.config.num_labels)]
        model.to(device).eval()
        metadata['feature_extractor'] = extractor.to_dict()
        metadata['loading_info'] = loading
        metadata['parameter_count'] = sum(p.numel() for p in model.parameters())
        def probabilities(waveform):
            inputs = extractor(waveform, sampling_rate=16000, return_tensors='pt',
                               padding=False, truncation=False)
            if tuple(inputs['input_values'].shape) != (1, len(waveform)):
                raise ValueError('Unexpected model input shape or implicit truncation.')
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.inference_mode():
                logits = model(**inputs).logits
                if tuple(logits.shape) != (1, 4):
                    raise ValueError(f'Unexpected logits shape: {logits.shape}')
                return logits.softmax(dim=-1)[0].cpu().numpy()
    else:
        from speechbrain.inference.interfaces import Pretrained
        from speechbrain.utils.fetching import LocalStrategy
        # Local subclass implements the published custom_interface.py computation.
        # It intentionally passes no filenames into the model.
        class SERClassifier(Pretrained):
            HPARAMS_NEEDED = ['label_encoder', 'softmax']
            MODULES_NEEDED = ['wav2vec2', 'avg_pool', 'output_mlp']
            def audio_probabilities(self, waveform):
                features = self.mods.wav2vec2(waveform)
                lengths = torch.ones(waveform.shape[0], device=waveform.device)
                pooled = self.mods.avg_pool(features, lengths).view(waveform.shape[0], -1)
                return self.hparams.softmax(self.mods.output_mlp(pooled))
        base = Path(snapshot_download('facebook/wav2vec2-base', revision=args.base_revision,
                    allow_patterns=['config.json', 'preprocessor_config.json', 'pytorch_model.bin']))
        # COPY avoids Windows symlink privileges. Pretrained source and all loadable
        # paths point at immutable snapshots; no hidden moving-main checkpoint paths.
        model = SERClassifier.from_hparams(source=str(snapshot),
            savedir=str(out / 'speechbrain_cache'),
            overrides={'pretrained_path': str(snapshot), 'wav2vec2_hub': str(base)},
            local_strategy=LocalStrategy.COPY, run_opts={'device': str(device)})
        model.eval()
        labels = [canonical_label(label) for label in
                  model.hparams.label_encoder.decode_torch(torch.arange(4))]
        metadata['base_model_revision'] = base.name
        metadata['input_normalization'] = bool(model.mods.wav2vec2.normalize_wav)
        metadata['output_normalization'] = bool(model.mods.wav2vec2.output_norm)
        metadata['parameter_count'] = sum(p.numel() for p in model.parameters())
        def probabilities(waveform):
            tensor = torch.from_numpy(waveform).unsqueeze(0).to(device)
            with torch.inference_mode():
                result = model.audio_probabilities(tensor)
            if tuple(result.shape) != (1, 4):
                raise ValueError(f'Unexpected SpeechBrain output shape: {result.shape}')
            # Published hparams use probability Softmax, not log-softmax. Validate
            # instead of exponentiating or applying softmax a second time.
            return result[0].cpu().numpy()
    if len(labels) != 4 or set(labels) != set(EMOTIONS):
        raise ValueError(f'Checkpoint must have exactly four unambiguous classes: {labels}')
    metadata['index_to_label'] = dict(enumerate(labels))
    print('Model labels:', metadata['index_to_label'], flush=True)
    def predict(waveform):
        if waveform.ndim != 1 or waveform.dtype != np.float32:
            raise ValueError('Predictor requires a 1-D float32 waveform.')
        values = np.asarray(probabilities(waveform), dtype=np.float64)
        if (values.shape != (4,) or not np.isfinite(values).all() or
                (values < 0).any() or (values > 1).any() or
                not np.isclose(values.sum(), 1.0, atol=1e-5)):
            raise ValueError(f'Malformed model probability vector: {values}')
        winner = int(values.argmax())
        return labels[winner], float(values[winner]) * 100.0
    return predict, metadata


def summarize(rows, same_set, metadata):
    import numpy as np
    from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, accuracy_score
    actual = [r['actual'] for r in rows]
    predicted = [r['predicted'] for r in rows]
    if len(rows) != 200 or collections.Counter(actual) != dict.fromkeys(EMOTIONS, 50):
        raise ValueError('Refusing to report a partial/imbalanced evaluation.')
    p, r, f, support = precision_recall_fscore_support(actual, predicted, labels=EMOTIONS, zero_division=0)
    cm = confusion_matrix(actual, predicted, labels=EMOTIONS)
    acc = accuracy_score(actual, predicted)
    correct = sum(bool(x['correct']) for x in rows)
    def mean_conf(subset):
        return f'{np.mean([x["confidence"] for x in subset]):.4f}%' if subset else 'N/A (no cases)'
    old = np.asarray(BASE_CM)
    old_p = old.diagonal()/old.sum(axis=0)
    old_r = old.diagonal()/old.sum(axis=1)
    exact_old_f1 = float(np.mean(2*old_p*old_r/(old_p+old_r)))
    lines = ['TESTING 3 - CROSS-CORPUS SPEECH EMOTION RECOGNITION',
             f'Model: {metadata["model"]}', f'Preprocessing: {metadata["preprocessing"]}',
             f'Sample source: {metadata["sample_source"]}',
             f'Same filename set as supplied Testing 2: {same_set}',
             'Filename equality does not prove historical byte identity (no old audio hashes supplied).',
             f'Total samples: {len(rows)}', f'Correct predictions: {correct}',
             f'Incorrect predictions: {200-correct}', f'Overall accuracy: {acc*100:.2f}%',
             f'Balanced accuracy (macro recall): {r.mean()*100:.2f}%',
             'Balanced accuracy equals overall accuracy here because each class has 50 cases.',
             '', 'Emotion       Precision      Recall          F1    Support']
    for i, emotion in enumerate(EMOTIONS):
        lines.append(f'{emotion:10} {p[i]:12.6f} {r[i]:11.6f} {f[i]:11.6f} {support[i]:10d}')
    lines += [f'Macro precision: {p.mean():.6f}', f'Macro recall: {r.mean():.6f}',
              f'Macro F1: {f.mean():.6f}', f'Weighted F1: {np.average(f, weights=support):.6f}',
              'Precision for an unpredicted class is undefined and reported as zero.',
              '', 'Per-emotion accuracy = class recall:']
    for i, e in enumerate(EMOTIONS):
        lines.append(f'{e:10}: {cm[i,i]}/50 = {r[i]*100:.2f}%')
    lines += ['', f'Average confidence: {mean_conf(rows)}',
              f'Average confidence, correct: {mean_conf([x for x in rows if x["correct"]])}',
              f'Average confidence, incorrect: {mean_conf([x for x in rows if not x["correct"]])}',
              'Confidence = uncalibrated maximum softmax probability; not probability of being correct.',
              '', 'Prediction distribution:']
    counts = collections.Counter(predicted)
    for e in EMOTIONS:
        lines.append(f'{e:10}: {counts[e]:3d}/200 ({counts[e]/2:.2f}%)')
    lines += ['', 'Confusion matrix: rows actual, columns predicted; neutral, happy, sad, angry', str(cm),
              '', 'BASELINE TESTING 2', 'Accuracy: 44.50%', 'Macro F1: 0.37 (rounded reported value)',
              '', 'NEW TEST', f'Accuracy: {acc*100:.2f}%', f'Macro F1: {f.mean():.6f}',
              f'Accuracy improvement: {acc*100-44.5:+.2f} percentage points',
              f'Macro F1 improvement: {f.mean()-0.37:+.6f} (versus rounded 0.37)',
              f'Exact baseline macro F1 from supplied matrix: {exact_old_f1:.6f}',
              f'Macro F1 improvement versus exact baseline: {f.mean()-exact_old_f1:+.6f}',
              'Comparison: paired by filename.' if same_set else
              'Comparison is UNPAIRED/descriptive; the test filenames differ.',
              '', 'Emotion       Old Recall     New Recall']
    for i, e in enumerate(EMOTIONS):
        lines.append(f'{e:10} {old_r[i]*100:11.2f}% {r[i]*100:13.2f}%')
    errors = sorted((x for x in rows if not x['correct'] and x['confidence'] >= 90),
                    key=lambda x: -x['confidence'])
    lines += ['', f'High-confidence errors (>=90%): {len(errors)}']
    for x in errors:
        lines.append(f'Case {x["case_number"]:03d}: {x["filename"]} | '
                     f'{x["actual"]} -> {x["predicted"]} | {x["confidence"]:.6f}%')
    lines += ['', 'INTERPRETATION',
              'No prediction correction, class-prior adjustment, calibration or sample exclusion was used.',
              'Domain shift is a plausible explanation, not a demonstrated sole cause.',
              'Report all attempted models/ablations; do not select a final accuracy on this same set.',
              'A fresh actor-disjoint evaluation is needed after model/preprocessing selection.',
              'This experiment does not validate clinical distress prediction.',
              '', 'RUN METADATA', json.dumps(metadata, indent=2)]
    return '\n'.join(lines) + '\n', cm, r, counts


def save_plots(out, cm, recall, counts):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from sklearn.metrics import ConfusionMatrixDisplay
    fig, ax = plt.subplots(figsize=(7, 6))
    ConfusionMatrixDisplay(cm, display_labels=EMOTIONS).plot(ax=ax, values_format='d', cmap='Blues')
    ax.set_title('Testing 3 - Confusion matrix')
    fig.tight_layout()
    fig.savefig(out / 'testing3_confusion_matrix.png', dpi=200)
    plt.close(fig)
    for filename, values, title, ylabel, limit in [
        ('testing3_per_emotion_accuracy.png', recall*100, 'Testing 3 - Recall per emotion', 'Recall (%)', 100),
        ('testing3_prediction_distribution.png', [counts[e] for e in EMOTIONS],
         'Testing 3 - Prediction distribution', 'Number of predictions', 200)]:
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(EMOTIONS, values, color=['#4677ac', '#d8a92d', '#6b69a7', '#c15d54'])
        ax.bar_label(bars, fmt='%.1f', padding=3)
        ax.set(title=title, ylabel=ylabel, ylim=(0, limit*1.1))
        if 'distribution' in filename:
            ax.axhline(50, color='gray', linestyle='--', label='Actual support per class = 50')
            ax.legend()
        fig.tight_layout()
        fig.savefig(out / filename, dpi=200)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dataset-dir', default='datasets')
    parser.add_argument('--testing2-csv', help='Existing CSV, including the supplied .txt CSV if desired')
    parser.add_argument('--new-sample-set', action='store_true')
    parser.add_argument('--model', choices=MODELS, default='speechbrain')
    parser.add_argument('--preprocess', choices=['none', 'trim', 'peak'], default='none')
    parser.add_argument('--device', choices=['auto', 'cpu', 'cuda'], default='auto')
    parser.add_argument('--threads', type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument('--revision', default='main', help='Model SHA from previous run for exact reuse')
    parser.add_argument('--base-revision', default='main', help='SpeechBrain base-model SHA for exact reuse')
    parser.add_argument('--output-dir', default='testing3_output', help='Must be new or empty; protects previous runs')
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args()
    if args.threads < 1:
        parser.error('--threads must be positive')
    if args.new_sample_set and args.testing2_csv:
        parser.error('--new-sample-set and --testing2-csv are mutually exclusive')
    out = Path(args.output_dir).resolve()
    if out.exists() and any(out.iterdir()):
        parser.error(f'Output directory is not empty: {out}. Choose another directory.')
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    try:
        paths, source, same_set = choose_samples(args)
        import numpy as np
        random.seed(RANDOM_SEED)
        np.random.seed(RANDOM_SEED)
        metadata = {'model': MODELS[args.model], 'preprocessing': args.preprocess,
                    'seed': RANDOM_SEED, 'sample_source': source, 'same_testing2_filenames': same_set,
                    'python': sys.version, 'platform': platform.platform(),
                    'script_sha256': sha256_file(Path(__file__)), 'arguments': vars(args),
                    'confidence_unit': 'percent (0-100)', 'software_versions': {}}
        for name in ['torch', 'torchaudio', 'speechbrain', 'transformers', 'huggingface-hub',
                     'librosa', 'soundfile', 'numpy', 'scipy', 'scikit-learn', 'matplotlib', 'soxr']:
            try:
                metadata['software_versions'][name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                metadata['software_versions'][name] = 'not installed'
        print('Validating all 200 recordings before inference...', flush=True)
        manifest, audits, waveforms, seen_hashes = [], [], [], set()
        for i, path in enumerate(paths, 1):
            digest = sha256_file(path)
            if digest in seen_hashes:
                raise ValueError(f'Duplicate selected audio bytes: {path.name}; inspect dataset.')
            seen_hashes.add(digest)
            try:
                waveform, audit = load_audio(path, args.preprocess)
            except Exception as exc:
                raise RuntimeError(f"Audio validation failed for {path.name}: {exc}") from exc
            waveforms.append(waveform)
            manifest.append({'case_number': i, 'filename': path.name,
                             'actual': ravdess_label(path.name), 'sha256': digest})
            audits.append({'filename': path.name, **audit})
            if i % 20 == 0:
                print(f'Audio validation: {i}/200', flush=True)
        metadata['manifest_sha256'] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        write_json(out / 'testing3_manifest.json', manifest)
        write_json(out / 'testing3_audio_audit.json', audits)
        write_json(out / 'testing3_run_metadata.json', metadata)
        if args.audit_only:
            print(f'Validated 200 files, 50/class. Audio audit and manifest: {out}', flush=True)
            return
        import torch
        os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
        torch.manual_seed(RANDOM_SEED)
        torch.set_num_threads(args.threads)
        torch.use_deterministic_algorithms(True)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(RANDOM_SEED)
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
            torch.backends.cuda.matmul.allow_tf32 = False
        if args.device == 'cuda' and not torch.cuda.is_available():
            print('CUDA unavailable; using CPU.', flush=True)
        device = torch.device('cuda' if args.device != 'cpu' and torch.cuda.is_available() else 'cpu')
        metadata['device'] = str(device)
        metadata['threads'] = args.threads
        print('Using device:', device, flush=True)
        predictor, model_metadata = load_predictor(args, out, device)
        metadata.update(model_metadata)
        write_json(out / 'testing3_run_metadata.json', metadata)
        rows = []
        partial = out / 'testing3_results.partial.csv'
        fields = ['case_number', 'filename', 'actual', 'predicted', 'confidence', 'correct']
        with partial.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for i, (entry, waveform) in enumerate(zip(manifest, waveforms), 1):
                print(f'\n[{i:03d}/200] Running inference...', flush=True)
                try:
                    predicted, confidence = predictor(waveform)
                except Exception as exc:
                    raise RuntimeError(f"Inference failed on case {i}: {entry['filename']}: {exc}") from exc
                # Ground truth is accessed only after the audio-only prediction returns.
                actual = entry['actual']
                row = {'case_number': i, 'filename': entry['filename'], 'actual': actual,
                       'predicted': predicted, 'confidence': confidence, 'correct': actual == predicted}
                writer.writerow(row)
                stream.flush()
                rows.append(row)
                print(f'Actual: {actual}\nPredicted: {predicted}\nConfidence: {confidence:.4f}%\n'
                      f'Correct/Incorrect: {"Correct" if row["correct"] else "Incorrect"}\n'
                      f'Filename: {entry["filename"]}', flush=True)
        metadata['elapsed_seconds'] = time.perf_counter() - started
        summary, cm, recall, counts = summarize(rows, same_set, metadata)
        save_plots(out, cm, recall, counts)
        (out / 'testing3_summary.txt').write_text(summary, encoding='utf-8')
        write_json(out / 'testing3_run_metadata.json', metadata)
        partial.replace(out / 'testing3_results.csv')
        print('\n' + summary, flush=True)
        print(f'All 200 cases completed. Outputs: {out}', flush=True)
    except BaseException:
        (out / 'testing3_FAILED.txt').write_text(
            'INCOMPLETE RUN: do not report partial results as Testing 3. No sample was skipped.\n\n'
            + traceback.format_exc(), encoding='utf-8')
        raise


if __name__ == '__main__':
    main()
