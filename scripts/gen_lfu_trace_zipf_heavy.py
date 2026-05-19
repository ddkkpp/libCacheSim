#!/usr/bin/env python3
"""
Generate an LFU-favoring trace: heavy Zipf bursts + periodic cold scans.

Why this hurts LRU/Size more than LFU:
- Zipf burst creates stable high-frequency objects (LFU keeps them).
- Cold scan injects >cache-size unique objects, which flushes LRU recency state.

CSV format: time,obj-id,obj-size,ttl
"""

import sys

import numpy as np


N_REQUESTS = 10_000_000
N_OBJECTS = 100_000
SEED = 42

# 1 cycle = hot-set rotation + cold scan.
HOT_PASS_LEN = 9_000
SCAN_LEN = 10_001

# Hot set reused every cycle.
HOT_OBJECTS = 9_000

OBJ_SIZE = 10_000

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "lfutest_zipf_heavy_10m.csv"
ZIPF_ALPHA = float(sys.argv[2]) if len(sys.argv) > 2 else 1.30


def zipf_pmf(n_objects: int, alpha: float) -> np.ndarray:
    ranks = np.arange(1, n_objects + 1, dtype=np.float64)
    weights = 1.0 / np.power(ranks, alpha)
    weights /= weights.sum()
    return weights


def main() -> None:
    rng = np.random.RandomState(SEED)
    hot_pmf = zipf_pmf(HOT_OBJECTS, ZIPF_ALPHA)
    hot_ids = np.arange(0, HOT_OBJECTS, dtype=np.int32)
    cold_ids = np.arange(HOT_OBJECTS, N_OBJECTS, dtype=np.int32)

    print(
        f"n_objects={N_OBJECTS}, hot_objects={HOT_OBJECTS}, zipf_alpha={ZIPF_ALPHA}, "
        f"hot_pass_len={HOT_PASS_LEN}, scan_len={SCAN_LEN}, obj_size={OBJ_SIZE}, "
        f"top1={hot_pmf[0] * 100:.2f}%, top10={hot_pmf[:10].sum() * 100:.2f}%",
        flush=True,
    )

    t = 1
    cycle = 0
    with open(OUTPUT, "w", encoding="utf-8") as output_file:
        while t <= N_REQUESTS:
            cycle += 1

            # Phase A: one hot pass with low short-term locality but persistent frequency.
            n_hot = min(HOT_PASS_LEN, N_REQUESTS - t + 1)
            pass_ids = rng.choice(hot_ids, size=n_hot, replace=False if n_hot <= hot_ids.size else True, p=hot_pmf)
            for oid in pass_ids:
                output_file.write(f"{t},{int(oid)},{OBJ_SIZE},0\n")
                t += 1
                if t > N_REQUESTS:
                    break

            if t > N_REQUESTS:
                break

            # Phase B: unique cold scan (anti-recency disturbance)
            n_scan = min(SCAN_LEN, N_REQUESTS - t + 1, cold_ids.size)
            scan_ids = rng.choice(cold_ids, size=n_scan, replace=False)
            for oid in scan_ids:
                output_file.write(f"{t},{int(oid)},{OBJ_SIZE},0\n")
                t += 1
                if t > N_REQUESTS:
                    break

            if cycle % 5 == 0 or t > N_REQUESTS:
                done = t - 1
                print(f"  cycle={cycle} {done / 1e6:.1f}M / {N_REQUESTS / 1e6:.0f}M", flush=True)

    print(f"Done: {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
