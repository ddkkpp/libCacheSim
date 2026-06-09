# Phase-flip preference trace

Purpose: make object-level future-value labels phase-dependent while keeping the workload-level preference simple.

- `freq_preference`: `small_freq3` has short reuse, `large_freq1` is far/no reuse.
- `size_preference`: `large_freq1` has short reuse, `small_freq3` is far/no reuse.
- Expected easy target for RSD/LOH: switch global preference between frequency and size/byte value by phase.
- Expected hard target for LRB/3LCache: the same feature bin has opposite future labels across phases unless phase/context is learned.

Trace: `tmp/20260528-phase-flip-preference-trace/phase_flip_preference.csv`

Metadata: `tmp/20260528-phase-flip-preference-trace/phase_flip_metadata.csv`

Requests: 307,200

## Request mix by phase

| phase | kind | component | requests |
|---:|---|---|---:|
| 0 | freq_preference | filler_scan | 30720 |
| 0 | freq_preference | hot_return | 2560 |
| 0 | freq_preference | hot_warmup | 3840 |
| 0 | freq_preference | large_warmup | 1280 |
| 1 | size_preference | filler_scan | 30720 |
| 1 | size_preference | hot_warmup | 3840 |
| 1 | size_preference | large_return | 2560 |
| 1 | size_preference | large_warmup | 1280 |
| 2 | freq_preference | filler_scan | 30720 |
| 2 | freq_preference | hot_return | 2560 |
| 2 | freq_preference | hot_warmup | 3840 |
| 2 | freq_preference | large_warmup | 1280 |
| 3 | size_preference | filler_scan | 30720 |
| 3 | size_preference | hot_warmup | 3840 |
| 3 | size_preference | large_return | 2560 |
| 3 | size_preference | large_warmup | 1280 |
| 4 | freq_preference | filler_scan | 30720 |
| 4 | freq_preference | hot_return | 2560 |
| 4 | freq_preference | hot_warmup | 3840 |
| 4 | freq_preference | large_warmup | 1280 |
| 5 | size_preference | filler_scan | 30720 |
| 5 | size_preference | hot_warmup | 3840 |
| 5 | size_preference | large_return | 2560 |
| 5 | size_preference | large_warmup | 1280 |
| 6 | freq_preference | filler_scan | 30720 |
| 6 | freq_preference | hot_return | 2560 |
| 6 | freq_preference | hot_warmup | 3840 |
| 6 | freq_preference | large_warmup | 1280 |
| 7 | size_preference | filler_scan | 30720 |
| 7 | size_preference | hot_warmup | 3840 |
| 7 | size_preference | large_return | 2560 |
| 7 | size_preference | large_warmup | 1280 |
