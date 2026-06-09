# Label-noise preference trace

Purpose: keep the workload preference stationary while adding decoy objects that pollute object-level future-distance labels.

- Stable useful rule: candidates always return after the short scan gap.
- Noise rule: poison objects share the same local size/frequency signature but are injected only after useful returns finish.
- Expected hard target for LRB/3LCache: training sees many same-feature no-return examples even though they do not affect the useful keep/evict window.
- Expected easy target for LOH-like recency preference: the poison stream arrives after the hits, so it mainly pollutes labels rather than evicting useful candidates before reuse.

Trace: `tmp/20260529-post-return-poison-A/label_noise_preference.csv`

Metadata: `tmp/20260529-post-return-poison-A/label_noise_metadata.csv`

Requests: 2,649,600

Working-set objects: 163,840

Default object size: 4,096 bytes

Candidate object size: 4,096 bytes

Poison object size: 4,096 bytes

Scan object size: 4,096 bytes

## Request mix

| component | requests |
|---|---:|
| candidate_burst | 138,240 |
| candidate_return | 92,160 |
| poison_burst | 2,211,840 |
| short_gap_scan | 23,040 |
| tail_gap_scan | 184,320 |

## Label mix for local training bins

| class | short_reuse=1 | short_reuse=0 | p(short reuse) |
|---|---:|---:|---:|
| candidate | 46,080 | 0 | 1.0000 |
| poison | 0 | 737,280 | 0.0000 |
| all | 46,080 | 737,280 | 0.0588 |
