#!/usr/bin/env python3
import argparse
import json
import math
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


PROCESSED_RE = re.compile(r"processed\s+(\d+)\s+requests,\s+(\d+)\s+objects,\s+(\d+)\s+bytes")
PROCESSED_CAP_RE = re.compile(r"processed\s+(\d+)\s+requests\s+capped\s+by\s+the\s+user")
WSS_RE = re.compile(r"estimated working set size .*:\s+(\d+)\s+object\s+(\d+)\s+byte")


def load_db(db_path: Path) -> dict:
    with db_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db_path: Path, data: dict) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with db_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def compute_features(profile: dict) -> Dict[str, float]:
    req = max(float(profile["req_seen"]), 1.0)
    obj = float(profile["obj_seen"])
    req_bytes = float(profile["req_bytes_seen"])
    wss_obj = float(profile["wss_obj_est"])
    wss_bytes = float(profile["wss_bytes_est"])

    return {
        "obj_per_req": obj / req,
        "req_bytes_per_req": req_bytes / req,
        "wss_obj_per_req": wss_obj / req,
        "wss_bytes_per_req": wss_bytes / req,
        "wss_bytes_over_req_bytes": wss_bytes / max(req_bytes, 1.0),
    }


def parse_profile_from_text(text: str) -> dict:
    processed = PROCESSED_RE.findall(text)
    processed_cap = PROCESSED_CAP_RE.findall(text)
    wss = WSS_RE.findall(text)

    if not wss:
        raise RuntimeError("Cannot parse estimated working-set line from cachesim output")

    if processed:
        req_seen, obj_seen, req_bytes_seen = processed[-1]
    elif processed_cap:
        req_seen = processed_cap[-1]
        obj_seen = wss[-1][0]
        req_bytes_seen = wss[-1][1]
    else:
        raise RuntimeError("Cannot parse processed-requests line from cachesim output")

    wss_obj_est, wss_bytes_est = wss[-1]

    return {
        "req_seen": int(req_seen),
        "obj_seen": int(obj_seen),
        "req_bytes_seen": int(req_bytes_seen),
        "wss_obj_est": int(wss_obj_est),
        "wss_bytes_est": int(wss_bytes_est),
    }


def collect_profile_with_cachesim(
    cachesim_bin: Path,
    trace_path: str,
    trace_type: str,
    cache_ratio: float,
    num_req: int,
    eviction_params: str,
) -> dict:
    env = os.environ.copy()
    env["LOH_ENABLE_RL"] = "0"
    env["LOH_FIXED_WEIGHTS"] = "1,0,2.5,0,0,0"
    env["LOH_SCORE_USE_IRT"] = "1"
    env["LOH_SCORE_USE_COMPOUND"] = "1"
    env["LOH_USE_HEURISTIC_SIGNS"] = "1"
    env["LOH_USE_SOFTMAX"] = "1"
    env["LOH_FEATURE_LOG1P"] = "1"
    env["LOH_FEATURE_LOG1P_RECIPROCAL"] = "0"
    env["LOH_ENABLE_FEATURE_NORMALIZATION"] = "1"
    env["LOH_SCORE_MODEL"] = "linear"

    cmd = [
        str(cachesim_bin),
        trace_path,
        trace_type,
        "LOH",
        str(cache_ratio),
        f"--num-req={num_req}",
        f"--eviction-params={eviction_params}",
        "-v",
        "0",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    profile = parse_profile_from_text(text)
    profile["command_ok"] = proc.returncode == 0
    profile["return_code"] = proc.returncode
    return profile


def vec_from_features(features: Dict[str, float], keys: List[str]) -> List[float]:
    return [math.log1p(max(features[k], 0.0)) for k in keys]


def euclidean(a: List[float], b: List[float]) -> float:
    s = 0.0
    for x, y in zip(a, b):
        d = x - y
        s += d * d
    return math.sqrt(s)


def predict_weights(
    profile: dict,
    db: dict,
    top_k: int = 3,
    min_entries: int = 5,
    max_nearest_dist: float = 0.25,
) -> Tuple[List[float], List[dict]]:
    entries = db.get("entries", [])
    if not entries:
        raise RuntimeError("Profile DB is empty")
    if len(entries) < min_entries:
        raise RuntimeError(
            f"Profile DB too small ({len(entries)} entries), require >= {min_entries} for reliable prediction"
        )

    keys = db.get("feature_keys")
    if not keys:
        raise RuntimeError("DB missing feature_keys")

    qf = compute_features(profile)
    qv = vec_from_features(qf, keys)

    scored = []
    for e in entries:
        ef = compute_features(e["profile"])
        ev = vec_from_features(ef, keys)
        dist = euclidean(qv, ev)
        scored.append({"entry": e, "dist": dist})

    scored.sort(key=lambda x: x["dist"])
    keep = scored[: max(1, min(top_k, len(scored)))]

    if keep[0]["dist"] > max_nearest_dist:
        raise RuntimeError(
            f"Nearest profile distance too large ({keep[0]['dist']:.6f} > {max_nearest_dist}); refuse to predict"
        )

    if keep[0]["dist"] <= 1e-12:
        exact = [float(x) for x in keep[0]["entry"]["weights"]]
        used = [
            {
                "name": keep[0]["entry"].get("name", "unknown"),
                "dist": keep[0]["dist"],
                "weights": keep[0]["entry"]["weights"],
            }
        ]
        return exact, used

    tau = max(keep[-1]["dist"], 1e-9)
    weights = [0.0] * 6
    z = 0.0
    for item in keep:
        d = item["dist"]
        alpha = math.exp(-d / tau)
        z += alpha
        w = item["entry"]["weights"]
        for i in range(6):
            weights[i] += alpha * float(w[i])

    if z > 0:
        weights = [x / z for x in weights]

    used = [
        {
            "name": item["entry"].get("name", "unknown"),
            "dist": item["dist"],
            "weights": item["entry"]["weights"],
        }
        for item in keep
    ]
    return weights, used


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict LOH fixed weights from trace profile")
    parser.add_argument("--db", default="configs/loh_weight_profiles.json")
    parser.add_argument("--mode", choices=["predict", "add-entry"], default="predict")
    parser.add_argument("--trace", help="Trace file path")
    parser.add_argument("--trace-type", default="oracleGeneral")
    parser.add_argument("--cache-ratio", type=float, default=0.1)
    parser.add_argument("--num-req", type=int, default=3000000)
    parser.add_argument("--eviction-params", default="miss-ratio-weight=1.0")
    parser.add_argument("--cachesim-bin", default="_build_dbg/bin/cachesim")
    parser.add_argument("--top-k", type=int, default=1)
    parser.add_argument("--min-entries", type=int, default=5)
    parser.add_argument("--max-nearest-dist", type=float, default=0.25)

    parser.add_argument("--name", help="Entry name when mode=add-entry")
    parser.add_argument("--weights", help="Comma-separated 6 weights when mode=add-entry")
    args = parser.parse_args()

    db_path = Path(args.db)
    db = load_db(db_path)

    if not args.trace:
        raise RuntimeError("--trace is required")

    profile = collect_profile_with_cachesim(
        cachesim_bin=Path(args.cachesim_bin),
        trace_path=args.trace,
        trace_type=args.trace_type,
        cache_ratio=args.cache_ratio,
        num_req=args.num_req,
        eviction_params=args.eviction_params,
    )

    if args.mode == "add-entry":
        if not args.name or not args.weights:
            raise RuntimeError("--name and --weights are required in add-entry mode")
        weights = [float(x.strip()) for x in args.weights.split(",")]
        if len(weights) != 6:
            raise RuntimeError("--weights must contain 6 numbers")
        db.setdefault("entries", []).append(
            {
                "name": args.name,
                "trace": args.trace,
                "weights": weights,
                "profile": profile,
            }
        )
        save_db(db_path, db)
        print(f"Added entry: {args.name}")
        return

    pred, used = predict_weights(
        profile,
        db,
        top_k=args.top_k,
        min_entries=args.min_entries,
        max_nearest_dist=args.max_nearest_dist,
    )
    print("Predicted LOH_FIXED_WEIGHTS=")
    print(",".join(f"{x:.6f}" for x in pred))
    print("\nNearest profiles:")
    for u in used:
        print(f"- {u['name']}: dist={u['dist']:.6f}, weights={u['weights']}")


if __name__ == "__main__":
    main()
