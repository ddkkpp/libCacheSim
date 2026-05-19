#!/usr/bin/env python3
"""
Generate a size-dominant synthetic trace with an extreme three-tier size split.

CSV format: time,obj-id,obj-size,ttl
"""

import sys

import numpy as np


N_REQUESTS = 10_000_000
SEED = 42
BATCH = 1_000_000

N_TINY = 80_000
N_SMALL = 19_000
N_HUGE = 1_000

SIZE_TINY = 64
SIZE_SMALL = 4_096
SIZE_HUGE = 16_777_216

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "sizetest_threetier_extreme_10m.csv"


def main() -> None:
    rng = np.random.RandomState(SEED)
    n_objects = N_TINY + N_SMALL + N_HUGE
    sizes = np.concatenate(
        [
            np.full(N_TINY, SIZE_TINY, dtype=np.int32),
            np.full(N_SMALL, SIZE_SMALL, dtype=np.int32),
            np.full(N_HUGE, SIZE_HUGE, dtype=np.int32),
        ]
    )

    print(
        f"objects={n_objects}, tiny={N_TINY}x{SIZE_TINY}B, "
        f"small={N_SMALL}x{SIZE_SMALL}B, huge={N_HUGE}x{SIZE_HUGE}B",
        flush=True,
    )

    with open(OUTPUT, "wb") as output_file:
        for batch_start in range(0, N_REQUESTS, BATCH):
            batch_size = min(BATCH, N_REQUESTS - batch_start)
            obj_ids = rng.randint(0, n_objects, batch_size, dtype=np.int32)
            times = np.arange(batch_start + 1, batch_start + batch_size + 1, dtype=np.int32)
            obj_sizes = sizes[obj_ids]
            ttls = np.zeros(batch_size, dtype=np.int32)
            data = np.column_stack([times, obj_ids, obj_sizes, ttls])
            lines = [f"{row[0]},{row[1]},{row[2]},{row[3]}\n" for row in data]
            output_file.write("".join(lines).encode())

            done = batch_start + batch_size
            print(f"  {done / 1e6:.1f}M / {N_REQUESTS / 1e6:.0f}M", flush=True)

    print(f"Done: {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
