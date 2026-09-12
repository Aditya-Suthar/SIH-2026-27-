# Actor voice analysis

Analyzed all 1,440 WAV files using waveform measurements. This is an acoustic audit, not a listening review or an emotion-classifier evaluation. Original audio was not modified.

## Dataset

24 actors, 60 files each; 88.82 minutes total. Clips range from 2.94 to 5.27 seconds. All files decode; every expected filename is present. All are 48 kHz, 16-bit PCM. There are 1,435 mono and 5 stereo files.

The filenames match the RAVDESS audio-only speech convention. Each actor has 4 neutral clips and 8 each for calm, happy, sad, angry, fearful, disgust, and surprised. Neutral has only normal intensity; other categories have normal and strong intensity. Dataset documentation specifies two repeated sentences, so this is a narrow acted-speech benchmark.

Source: https://zenodo.org/records/1188976

## All actors

Pitch is the median of per-clip estimated voiced pitch across all emotions, not a neutral speaking baseline. Level is median active-frame RMS in dBFS; less negative means louder recorded audio. Recording gain and performance both affect it.

| Actor | Approx. pitch (Hz) | Active level (dBFS) | Mean clip (s) |
|---|---:|---:|---:|
| 01 | 145 | -37.6 | 3.75 |
| 02 | 246 | -34.3 | 3.79 |
| 03 | 167 | -33.9 | 3.76 |
| 04 | 296 | -31.2 | 3.63 |
| 05 | 150 | -41.0 | 3.74 |
| 06 | 260 | -41.8 | 3.79 |
| 07 | 164 | -39.1 | 3.75 |
| 08 | 216 | -38.3 | 3.73 |
| 09 | 109 | -49.0 | 3.49 |
| 10 | 235 | -30.9 | 3.75 |
| 11 | 158 | -35.7 | 3.44 |
| 12 | 230 | -35.3 | 3.75 |
| 13 | 140 | -40.4 | 3.33 |
| 14 | 267 | -39.1 | 3.68 |
| 15 | 143 | -35.1 | 3.50 |
| 16 | 229 | -34.4 | 3.73 |
| 17 | 155 | -31.4 | 3.67 |
| 18 | 250 | -34.8 | 3.75 |
| 19 | 164 | -40.0 | 3.87 |
| 20 | 254 | -40.4 | 3.73 |
| 21 | 138 | -32.4 | 3.92 |
| 22 | 211 | -35.5 | 3.72 |
| 23 | 176 | -34.4 | 3.61 |
| 24 | 254 | -33.8 | 3.95 |

Actor 09 has the lowest estimated pitch (109 Hz) and lowest recorded active level (-49.0 dBFS). Actor 04 has the highest estimated pitch (296 Hz). Actor 10 has the highest median active level (-30.9 dBFS), about 18 dB above Actor 09. Actor 13 has the shortest mean clip; Actor 24 the longest. Clip duration includes pauses and does not directly measure speaking rate.

## Emotion-label patterns

| Label | Clips | Approx. pitch (Hz) | Active level (dBFS) |
|---|---:|---:|---:|
| neutral | 96 | 172 | -43.0 |
| calm | 192 | 160 | -45.0 |
| happy | 192 | 235 | -31.8 |
| sad | 192 | 195 | -40.3 |
| angry | 192 | 250 | -25.1 |
| fearful | 192 | 258 | -29.9 |
| disgust | 192 | 195 | -37.0 |
| surprised | 192 | 242 | -33.8 |

Angry-labelled recordings have the highest median active level; calm-labelled recordings the lowest, a difference of about 20 dB. Fearful-labelled recordings have the highest estimated median pitch. These summaries overlap across individual clips and do not show that pitch or volume alone can classify emotions.

## Files to review

One byte-identical duplicate pair (same SHA-256), both labelled happy, normal intensity, statement 2, actor 07, with different repetition identifiers:

- `datasets\Actor_07\03-01-03-01-02-01-07.wav`
- `datasets\Actor_07\03-01-03-01-02-02-07.wav`

Five stereo files were checked and have identical left/right channels:

- `datasets\Actor_01\03-01-02-01-01-02-01.wav`
- `datasets\Actor_01\03-01-08-01-02-02-01.wav`
- `datasets\Actor_05\03-01-02-01-02-02-05.wav`
- `datasets\Actor_20\03-01-03-01-02-01-20.wav`
- `datasets\Actor_20\03-01-06-01-01-02-20.wav`

`datasets/Actor_10/03-01-03-02-02-01-10.wav` has one sample at 0.9991455 full scale. This is a near-full-scale flag, not proof of clipping. The CSV field `clipped_samples` and JSON field `clipped_files` count the threshold abs(sample) >= 0.999; interpret them as near-full-scale flags.

On average, 63.6% of 40 ms frames fall below a threshold 20 dB under the clip maximum frame RMS. This includes pauses and quiet speech, not just silence. Do not blindly remove all such frames.

## Implications for the project

- Split training and evaluation by actor to measure generalization to unfamiliar voices. Keep exact duplicates in the same split or exclude one.
- Handle stereo consistently and resample to the sample rate required by the model. Preserve original recordings.
- Neutral has half as many examples as each other category; report per-class results and macro averages.
- Recorded levels vary substantially. Check preprocessing consistency, but remember loudness carries emotion-related information.
- This dataset alone cannot establish performance on spontaneous speech, other languages, background noise, or real emergencies.

## Method and limits

Pitch uses 8 kHz resampling, 40 ms Hann-windowed frames every 20 ms, autocorrelation peaks within approximately 60?500 Hz, and a correlation threshold of 0.5. Active frames exceed max(0.1 * maximum frame RMS, 1e-5). Pitch estimates are approximate and can contain octave errors, especially for breathy or irregular phonation. No perceptual timbre, accent, personality, or health conclusions were made. File hashes check byte-identical duplicates, not all acoustically similar recordings.

Reproduce with `python validation/analyze_actor_audio.py`. Detailed measurements: `clips.csv`, `actors.csv`, `emotions.csv`, and `summary.json`.
