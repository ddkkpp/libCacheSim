#!/usr/bin/env python3
"""
Generate a size-dominant synthetic trace with an extreme two-tier size split.

CSV format: time,obj-id,obj-size,ttl
"""

import argparse

import numpy as np


DEFAULT_REQUESTS = 10_000_000
DEFAULT_SEED = 42
DEFAULT_BATCH = 1_000_000

DEFAULT_N_SMALL = 99_000
DEFAULT_N_LARGE = 1_000
DEFAULT_SIZE_SMALL = 64
DEFAULT_SIZE_LARGE = 16_777_216
DEFAULT_OUTPUT = "sizetest_twotier_extreme_10m.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate two-tier size synthetic trace")
    parser.add_argument("output", nargs="?", default=DEFAULT_OUTPUT, help="output CSV path")
    parser.add_argument("--n-requests", type=int, default=DEFAULT_REQUESTS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH)
    parser.add_argument("--n-small", type=int, default=DEFAULT_N_SMALL)
    parser.add_argument("--n-large", type=int, default=DEFAULT_N_LARGE)
    parser.add_argument("--size-small", type=int, default=DEFAULT_SIZE_SMALL)
    parser.add_argument("--size-large", type=int, default=DEFAULT_SIZE_LARGE)
    parser.add_argument(
        "--req-dist",
        choices=["uniform", "zipf", "twostage"],
        default="uniform",
        help="request distribution over object IDs",
    )
    parser.add_argument(
        "--zipf-alpha",
        type=float,
        default=1.5,
        help="Zipf alpha when --req-dist=zipf",
    )
    parser.add_argument(
        "--small-req-prob",
        type=float,
        default=0.9,
        help="probability to pick small-object tier when --req-dist=twostage",
    )
    return parser.parse_args()


def sample_obj_ids(rng: np.random.RandomState, batch_size: int, args: argparse.Namespace) -> np.ndarray:
    n_objects = args.n_small + args.n_large
    if args.req_dist == "uniform":
        return rng.randint(0, n_objects, batch_size, dtype=np.int32)

    if args.req_dist == "zipf":
        ranks = rng.zipf(args.zipf_alpha, size=batch_size)
        ranks = np.minimum(ranks, n_objects)
        return (ranks - 1).astype(np.int32)

    choose_small = rng.rand(batch_size) < args.small_req_prob
    obj_ids = np.empty(batch_size, dtype=np.int32)
    n_small_req = int(choose_small.sum())
    obj_ids[choose_small] = rng.randint(0, args.n_small, n_small_req, dtype=np.int32)
    obj_ids[~choose_small] = rng.randint(
        args.n_small, args.n_small + args.n_large, batch_size - n_small_req, dtype=np.int32
    )
    return obj_ids


def main() -> None:
    args = parse_args()
    if args.n_small <= 0 or args.n_large <= 0:
        raise ValueError("--n-small and --n-large must both be positive")
    if not (0.0 <= args.small_req_prob <= 1.0):
        raise ValueError("--small-req-prob must be in [0, 1]")
    if args.req_dist == "zipf" and args.zipf_alpha <= 1.0:
        raise ValueError("--zipf-alpha must be > 1.0 for stable sampling")

    rng = np.random.RandomState(args.seed)
    n_objects = args.n_small + args.n_large
    sizes = np.concatenate(
        [
            np.full(args.n_small, args.size_small, dtype=np.int32),
            np.full(args.n_large, args.size_large, dtype=np.int32),
        ]
    )

    print(
        f"objects={n_objects}, small={args.n_small}x{args.size_small}B, "
        f"large={args.n_large}x{args.size_large}B, requests={args.n_requests}",
        flush=True,
    )
    print(
        f"req_dist={args.req_dist}, zipf_alpha={args.zipf_alpha}, "
        f"small_req_prob={args.small_req_prob}",
        flush=True,
    )

    with open(args.output, "wb") as output_file:
        for batch_start in range(0, args.n_requests, args.batch):
            batch_size = min(args.batch, args.n_requests - batch_start)
            obj_ids = sample_obj_ids(rng, batch_size, args)
            times = np.arange(batch_start + 1, batch_start + batch_size + 1, dtype=np.int32)
            obj_sizes = sizes[obj_ids]
            ttls = np.zeros(batch_size, dtype=np.int32)
            data = np.column_stack([times, obj_ids, obj_sizes, ttls])
            lines = [f"{row[0]},{row[1]},{row[2]},{row[3]}\n" for row in data]
            output_file.write("".join(lines).encode())

            done = batch_start + batch_size
            print(f"  {done / 1e6:.1f}M / {args.n_requests / 1e6:.0f}M", flush=True)

    print(f"Done: {args.output}", flush=True)


if __name__ == "__main__":
    main()
