#!/usr/bin/env python3
"""Train LightGBM regressors for the LOH GBM weight actor.

Accepted input formats:
  1. JSONL rows with fields: {"state": [...], "weights": [...]}
  2. CSV with JSON/list fields: state, weights
  3. CSV with expanded columns: state0..stateN and weight0..weight6

The script trains one scalar LightGBM regressor per weight dimension and writes
model files compatible with scripts/loh_gbm_weight_actor.py.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import numpy as np


def _parse_vector(value: str) -> List[float]:
    text = value.strip()
    if not text:
        return []
    if text[0] in "[{":
        parsed = json.loads(text) if text[0] == "[" else ast.literal_eval(text)
        return [float(item) for item in parsed]
    return [float(item.strip()) for item in text.replace(";", ",").split(",") if item.strip()]


def _load_jsonl(path: Path) -> Iterable[Tuple[List[float], List[float]]]:
    with path.open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            yield [float(x) for x in row["state"]], [float(x) for x in row["weights"]]


def _load_csv(path: Path) -> Iterable[Tuple[List[float], List[float]]]:
    with path.open("r", encoding="utf-8", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        if reader.fieldnames is None:
            return

        state_cols = sorted(
            [name for name in reader.fieldnames if name.startswith("state") and name[5:].isdigit()],
            key=lambda item: int(item[5:]),
        )
        weight_cols = sorted(
            [name for name in reader.fieldnames if name.startswith("weight") and name[6:].isdigit()],
            key=lambda item: int(item[6:]),
        )

        for row in reader:
            if "state" in row and "weights" in row:
                yield _parse_vector(row["state"]), _parse_vector(row["weights"])
            elif state_cols and weight_cols:
                yield [float(row[name]) for name in state_cols], [float(row[name]) for name in weight_cols]
            else:
                raise ValueError(
                    f"{path} must contain state/weights fields or expanded stateN/weightN columns"
                )


def load_samples(paths: Sequence[Path], input_dim: int, weight_dim: int) -> Tuple[np.ndarray, np.ndarray]:
    states: List[List[float]] = []
    weights: List[List[float]] = []
    for path in paths:
        rows = _load_jsonl(path) if path.suffix.lower() in {".jsonl", ".ndjson"} else _load_csv(path)
        for state, weight in rows:
            if len(state) < input_dim:
                state = state + [0.0] * (input_dim - len(state))
            if len(weight) < weight_dim:
                weight = weight + [0.0] * (weight_dim - len(weight))
            states.append(state[:input_dim])
            weights.append(weight[:weight_dim])

    if not states:
        raise RuntimeError("no samples loaded")
    return np.asarray(states, dtype=np.float64), np.asarray(weights, dtype=np.float64)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train LOH state->weight LightGBM regressors")
    parser.add_argument("--input", action="append", required=True, help="CSV/JSONL sample file; can be repeated")
    parser.add_argument("--out-dir", required=True, help="Output model directory")
    parser.add_argument("--input-dim", type=int, required=True, help="Number of state features consumed by the model")
    parser.add_argument("--weight-dim", type=int, default=7, help="Number of LOH weights to train")
    parser.add_argument("--num-boost-round", type=int, default=96)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--num-leaves", type=int, default=31)
    parser.add_argument("--min-data-in-leaf", type=int, default=20)
    parser.add_argument("--feature-fraction", type=float, default=0.9)
    parser.add_argument("--bagging-fraction", type=float, default=0.9)
    parser.add_argument("--bagging-freq", type=int, default=1)
    parser.add_argument("--num-threads", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    try:
        import lightgbm as lgb  # type: ignore
    except Exception as exc:
        raise RuntimeError("Python package lightgbm is required to train GBM weight models") from exc

    input_paths = [Path(item) for item in args.input]
    output_dir = Path(args.out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    x, y = load_samples(input_paths, input_dim=args.input_dim, weight_dim=args.weight_dim)
    params = {
        "boosting": "gbdt",
        "objective": "regression",
        "metric": "l2",
        "learning_rate": args.learning_rate,
        "num_leaves": args.num_leaves,
        "min_data_in_leaf": args.min_data_in_leaf,
        "feature_fraction": args.feature_fraction,
        "bagging_fraction": args.bagging_fraction,
        "bagging_freq": args.bagging_freq,
        "num_threads": args.num_threads,
        "seed": args.seed,
        "verbosity": -1,
    }

    model_files = []
    metrics = []
    for dim in range(args.weight_dim):
        train_data = lgb.Dataset(x, label=y[:, dim], free_raw_data=False)
        booster = lgb.train(params, train_data, num_boost_round=args.num_boost_round)
        model_name = f"weight_{dim}.txt"
        booster.save_model(str(output_dir / model_name))
        pred = booster.predict(x)
        rmse = float(np.sqrt(np.mean((pred - y[:, dim]) ** 2)))
        model_files.append(model_name)
        metrics.append({"weight_dim": dim, "train_rmse": rmse})
        print(f"weight_{dim}: train_rmse={rmse:.8f}")

    manifest = {
        "kind": "loh_gbm_weight_model",
        "input_dim": args.input_dim,
        "weight_dim": args.weight_dim,
        "n_samples": int(x.shape[0]),
        "model_files": model_files,
        "params": params,
        "metrics": metrics,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"saved model directory: {output_dir}")


if __name__ == "__main__":
    main()
