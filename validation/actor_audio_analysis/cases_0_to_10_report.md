Cases 0?10 (first 11 recordings; original report cases 1?11).
Actual = dataset intended emotion verified from filename, not an independent listening judgment. Predicted and confidence = saved SpeechBrain run in testing3_output/testing3_results.csv; no new inference performed. Confidence is a model score, not a guarantee of correctness.

| Case | Actual | Predicted | Confidence | Result |
|---|---|---|---:|---|
| 0 | angry | angry | 100.00% | correct |
| 1 | sad | angry | 99.59% | incorrect |
| 2 | sad | neutral | 100.00% | incorrect |
| 3 | happy | happy | 100.00% | correct |
| 4 | neutral | angry | 97.23% | incorrect |
| 5 | neutral | neutral | 73.08% | correct |
| 6 | sad | angry | 99.95% | incorrect |
| 7 | angry | angry | 100.00% | correct |
| 8 | sad | neutral | 99.44% | incorrect |
| 9 | sad | happy | 100.00% | incorrect |
| 10 | sad | neutral | 100.00% | incorrect |

Accuracy: 4/11 = 36.36%.

Recording mapping:
- Case 0: 03-01-05-01-02-02-07.wav (original case 1)
- Case 1: 03-01-04-01-01-01-03.wav (original case 2)
- Case 2: 03-01-04-01-02-02-09.wav (original case 3)
- Case 3: 03-01-03-02-01-01-09.wav (original case 4)
- Case 4: 03-01-01-01-02-02-19.wav (original case 5)
- Case 5: 03-01-01-01-02-02-01.wav (original case 6)
- Case 6: 03-01-04-01-01-02-24.wav (original case 7)
- Case 7: 03-01-05-01-01-02-22.wav (original case 8)
- Case 8: 03-01-04-02-01-02-23.wav (original case 9)
- Case 9: 03-01-04-02-01-02-21.wav (original case 10)
- Case 10: 03-01-04-02-01-01-23.wav (original case 11)
