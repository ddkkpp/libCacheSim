#!/usr/bin/env python3
"""
Offline Belady/BeladySize simulator: computes what the oracle algorithms
WOULD have done on a given CSV trace.

Belady (MIN): evict cached object with LARGEST next_access_vtime (reuse distance).
  This is optimal for OBJECT miss ratio.

BeladySize: evict cached object with LARGEST score = size * (next_access_vtime - current).
  This is a heuristic for byte-aware eviction.

Usage: python3 sim_oracle.py trace.csv cache_size_bytes [--algo belady|beladysize]
"""

from __future__ import annotations
import argparse, csv, sys
from collections import defaultdict
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Offline Belady/BeladySize simulator")
    p.add_argument("trace", type=Path)
    p.add_argument("cache_size", type=float, help="Cache size fraction or bytes")
    p.add_argument("--algo", default="both", choices=["belady", "beladysize", "both"])
    p.add_argument("--working-set-bytes", type=int, default=0,
                   help="If cache_size < 1, use this as total working set bytes")
    p.add_argument("--n-sample", type=int, default=0,
                   help="BeladySize samples per eviction (0=exact scan all)")
    return p.parse_args()


def load_trace(trace_path):
    """Load trace and compute next_access for each request."""
    requests = []
    with trace_path.open() as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue
            ts = int(row[0]) if row[0].strip() else 0
            oid = int(row[1])
            size = int(row[2])
            requests.append((ts, oid, size))

    # Compute next_access_vtime for each position
    n = len(requests)
    next_access = [None] * n
    last_seen = {}
    # Scan backwards to find next access
    for i in range(n - 1, -1, -1):
        oid = requests[i][1]
        if oid in last_seen:
            next_access[i] = last_seen[oid]
        else:
            next_access[i] = None  # no future access
        last_seen[oid] = i
    return requests, next_access


def simulate_belady(requests, next_access, cache_size):
    """Simulate Belady MIN algorithm. Returns miss count."""
    cache = {}  # obj_id -> (size, next_access_idx)
    cache_bytes = 0
    misses = 0

    for i, (ts, oid, size) in enumerate(requests):
        if oid in cache:
            # Hit: update next_access
            cache[oid] = (size, next_access[i])
            continue

        # Miss
        misses += 1
        if size > cache_size:
            continue  # object too large

        # Evict if needed
        while cache_bytes + size > cache_size and cache:
            # Find object with furthest next access (or None = never)
            victim = None
            victim_next = -1
            for vid, (vsz, vnext) in cache.items():
                vn = vnext if vnext is not None else float('inf')
                if vn > victim_next:
                    victim_next = vn
                    victim = vid
            if victim is None:
                break
            cache_bytes -= cache[victim][0]
            del cache[victim]

        if cache_bytes + size <= cache_size:
            cache[oid] = (size, next_access[i])
            cache_bytes += size

    return misses


def simulate_beladysize(requests, next_access, cache_size, n_sample=0):
    """Simulate BeladySize algorithm (size * reuse_distance scoring)."""
    import random
    rng = random.Random(20260602)

    cache = {}  # obj_id -> (size, next_access_idx)
    cache_list = []  # for sampling
    cache_bytes = 0
    misses = 0

    for i, (ts, oid, size) in enumerate(requests):
        if oid in cache:
            cache[oid] = (size, next_access[i])
            continue

        misses += 1
        if size > cache_size:
            continue

        while cache_bytes + size > cache_size and cache:
            if n_sample > 0 and len(cache) > n_sample:
                # Sample-based
                victim = None
                victim_score = -1
                samples = rng.sample(list(cache.keys()), min(n_sample, len(cache)))
                for vid in samples:
                    vsz, vnext = cache[vid]
                    if vnext is None:
                        score = float('inf')
                    else:
                        dt = requests[vnext][0] - ts if requests[vnext][0] > ts else 1
                        score = vsz * dt
                    if score > victim_score:
                        victim_score = score
                        victim = vid
            else:
                # Exact scan
                victim = None
                victim_score = -1
                for vid, (vsz, vnext) in cache.items():
                    if vnext is None:
                        score = float('inf')
                    else:
                        dt = requests[vnext][0] - ts if requests[vnext][0] > ts else 1
                        score = vsz * dt
                    if score > victim_score:
                        victim_score = score
                        victim = vid

            if victim is None:
                break
            cache_bytes -= cache[victim][0]
            del cache[victim]

        if cache_bytes + size <= cache_size:
            cache[oid] = (size, next_access[i])
            cache_bytes += size

    return misses


def main():
    args = parse_args()
    requests, next_access = load_trace(args.trace)
    n = len(requests)
    print(f"Loaded {n} requests")

    # Compute cache size
    if args.cache_size < 1:
        if args.working_set_bytes > 0:
            wss = args.working_set_bytes
        else:
            # Compute from unique objects
            unique_sizes = {}
            for _, oid, size in requests:
                unique_sizes[oid] = size
            wss = sum(unique_sizes.values())
        cache_size = int(wss * args.cache_size)
    else:
        cache_size = int(args.cache_size)
    print(f"Cache: {cache_size} bytes ({cache_size/1024/1024:.1f} MB)")

    if args.algo in ("belady", "both"):
        misses = simulate_belady(requests, next_access, cache_size)
        mr = misses / n
        print(f"Belady (MIN):        misses={misses}/{n}  MR={mr:.6f}")

    if args.algo in ("beladysize", "both"):
        if args.n_sample > 0:
            misses_bs = simulate_beladysize(requests, next_access, cache_size, args.n_sample)
        else:
            misses_bs = simulate_beladysize(requests, next_access, cache_size)
        mr_bs = misses_bs / n
        print(f"BeladySize (exact):  misses={misses_bs}/{n}  MR={mr_bs:.6f}")


if __name__ == "__main__":
    main()
