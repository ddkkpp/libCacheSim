# Label-noise preference trace

Purpose: keep the workload preference stationary while adding decoy objects that pollute object-level future-distance labels.

- Stable useful rule: recently requested candidates are worth keeping only probabilistically; the workload has no phase flip.
- Noise rule: every candidate has the same local `size4k_freq3` signature, but its short-reuse label is sampled independently.
- Expected hard target for LRB/3LCache: object-level future labels have high aleatoric noise and cannot be reliably separated from local history.
- Expected easy target for LOH-like recency preference: the useful returns occur immediately after the short scan gap, so recency remains a reasonable low-variance rule.

Trace: `tmp/20260529-random-label-noise/label_noise_preference.csv`

Metadata: `tmp/20260529-random-label-noise/label_noise_metadata.csv`

Requests: 1,013,894

Working-set objects: 131,072

Object size: 4,096 bytes

## Request mix

| component | requests |
|---|---:|
| candidate_burst | 368,640 |
| candidate_return | 30,854 |
| short_gap_scan | 491,520 |
| tail_gap_scan | 122,880 |

## Label mix for identical local feature bin

| class | short_reuse=1 | short_reuse=0 | p(short reuse) |
|---|---:|---:|---:|
| hot | 0 | 0 | 0.0000 |
| decoy | 0 | 0 | 0.0000 |
| all | 15,427 | 107,453 | 0.1255 |
