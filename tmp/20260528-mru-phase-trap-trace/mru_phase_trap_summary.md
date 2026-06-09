# MRU Phase-Trap Synthetic Trace

Trace: `tmp/20260528-mru-phase-trap-trace/mru_phase_trap.csv`

Requests: 280,000
Unique objects: 20,000
Object size: 4,096 bytes

## Design

- `large_mru_scan`: one full cyclic scan over the total working set; at cache=0.1, MRU-style eviction can keep the early cache slice while LRU churns.
- `small_mru_scan`: cyclic scan over a 1% sub-working-set; at cache=0.001, the same MRU trap appears at the smaller scale.
- `burst_immediate_reuse`: the same first-touch local feature bin is followed by immediate reuse, creating a phase-dependent object-label flip.

## Request Mix

| phase | kind | requests |
|---:|---|---:|
| 0 | large_mru_scan | 160,000 |
| 1 | small_mru_scan | 100,000 |
| 2 | burst_immediate_reuse | 20,000 |
