# Label-noise preference trace

Purpose: keep the workload preference stationary while adding decoy objects that pollute object-level future-distance labels.

- Stable useful rule: hot objects have short reuse after a small scan gap.
- Noise rule: decoy objects have the same local `size4k_freq3` signature but no short useful return.
- Expected hard target for LRB/3LCache: the dominant label for `size4k_freq3` is noisy because decoys outnumber hot objects.
- Expected easy target for LOH-like recency preference: decoys arrive after hot returns, so they mainly train labels rather than disrupting the short hot reuse.

Trace: `tmp/20260529-label-noise-preference-trace/label_noise_preference.csv`

Metadata: `tmp/20260529-label-noise-preference-trace/label_noise_metadata.csv`

Requests: 798,720

Working-set objects: 73,728

Object size: 4,096 bytes

## Request mix

| component | requests |
|---|---:|
| decoy_burst | 491,520 |
| hot_burst | 61,440 |
| hot_return | 40,960 |
| short_gap_scan | 40,960 |
| tail_gap_scan | 163,840 |

## Label mix for identical local feature bin

| class | short_reuse=1 | short_reuse=0 | p(short reuse) |
|---|---:|---:|---:|
| hot | 20,480 | 0 | 1.0000 |
| decoy | 0 | 163,840 | 0.0000 |
| all | 20,480 | 163,840 | 0.1111 |
