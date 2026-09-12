"""Read-only waveform audit; writes derived measurements to validation/actor_audio_analysis."""
from pathlib import Path
import csv, hashlib, json
from collections import Counter
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, find_peaks

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'validation' / 'actor_audio_analysis'
OUT.mkdir(exist_ok=True)
EMOTIONS = dict(zip(range(1,9), ['neutral','calm','happy','sad','angry','fearful','disgust','surprised']))
rows, errors = [], []
for p in sorted((ROOT/'datasets').rglob('*.wav')):
    try:
        codes = list(map(int,p.stem.split('-')))
        x, sr = sf.read(p, always_2d=True)
        info = sf.info(p)
        mono = x.mean(axis=1)
        y = resample_poly(mono, 8000, sr)
        frames = np.lib.stride_tricks.sliding_window_view(y, 320)[::160].copy()
        rms = np.sqrt(np.mean(frames**2, axis=1))
        active = rms > max(rms.max()*0.1, 1e-5)
        pitches = []
        for frame in frames[active]:
            frame = (frame-frame.mean())*np.hanning(320)
            ac = np.fft.irfft(np.abs(np.fft.rfft(frame, n=1024))**2,n=1024)[:320]
            if ac[0] <= 0: continue
            ac /= ac[0]
            peaks, _ = find_peaks(ac[16:134])
            if len(peaks):
                lag = peaks[np.argmax(ac[peaks+16])]+16
                if ac[lag] >= 0.5: pitches.append(8000/lag)
        rows.append(dict(file=str(p.relative_to(ROOT)),actor=codes[6],emotion=EMOTIONS[codes[2]],intensity=codes[3],statement=codes[4],repetition=codes[5],seconds=len(x)/sr,sample_rate=sr,channels=x.shape[1],subtype=info.subtype,rms_dbfs=20*np.log10(max(np.sqrt(np.mean(mono**2)),1e-12)),active_rms_dbfs=20*np.log10(max(np.sqrt(np.mean(frames[active]**2)),1e-12)) if active.any() else -240,peak=float(np.max(np.abs(x))),clipped_samples=int(np.sum(np.abs(x)>=0.999)),low_energy_fraction=float(1-active.mean()),pitch_hz=float(np.median(pitches)) if pitches else None,pitch_frames=len(pitches),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    except Exception as e: errors.append({'file':str(p),'error':str(e)})

def write_csv(name, data):
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
write_csv('clips.csv',rows)
actors=[]
for a in sorted(set(r['actor'] for r in rows)):
    subset=[r for r in rows if r['actor']==a]
    actors.append(dict(actor=a,clips=len(subset),mean_seconds=float(np.mean([r['seconds'] for r in subset])),median_pitch_hz=float(np.median([r['pitch_hz'] for r in subset if r['pitch_hz']])),median_active_dbfs=float(np.median([r['active_rms_dbfs'] for r in subset])),mean_low_energy_fraction=float(np.mean([r['low_energy_fraction'] for r in subset])),emotion_counts=dict(Counter(r['emotion'] for r in subset))))
write_csv('actors.csv',actors)
emotions=[]
for emotion in EMOTIONS.values():
    subset=[r for r in rows if r['emotion']==emotion]
    emotions.append(dict(emotion=emotion,clips=len(subset),median_pitch_hz=float(np.median([r['pitch_hz'] for r in subset if r['pitch_hz']])),median_active_dbfs=float(np.median([r['active_rms_dbfs'] for r in subset])),mean_seconds=float(np.mean([r['seconds'] for r in subset]))))
write_csv('emotions.csv',emotions)
expected={f'Actor_{a:02d}/03-01-{e:02d}-{i:02d}-{s:02d}-{r:02d}-{a:02d}.wav' for a in range(1,25) for e in range(1,9) for i in ([1] if e==1 else [1,2]) for s in [1,2] for r in [1,2]}
actual={p.relative_to(ROOT/'datasets').as_posix() for p in (ROOT/'datasets').rglob('*.wav')}
summary=dict(total_files=len(rows),total_minutes=sum(r['seconds'] for r in rows)/60,duration_range=[min(r['seconds'] for r in rows),max(r['seconds'] for r in rows)],formats=dict(Counter(f"{r['sample_rate']} Hz / {r['channels']} ch / {r['subtype']}" for r in rows)),clipped_files=[r['file'] for r in rows if r['clipped_samples']],duplicates=len(rows)-len(set(r['sha256'] for r in rows)),missing=sorted(expected-actual),unexpected=sorted(actual-expected),errors=errors,actors=actors,emotions=emotions)
(OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
