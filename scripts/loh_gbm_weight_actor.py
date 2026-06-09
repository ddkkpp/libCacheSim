#!/usr/bin/env python3
"""LightGBM/GBM weight actor for LOH shared-memory inference/online training.

This script reuses the existing LOH C/Python shared-memory protocol:
  C side publishes state[CONTEXT_DIM] and sets ready_for_inference=1.
  This actor predicts weights[SHM_WEIGHT_DIM], writes them back, then sets
  weights_updated=1 and ready_for_inference=0.

With LOH_GBM_ONLINE_TRAIN=1 it follows the LRB/3LCache lifecycle at the
weight-policy level: sample a weight vector online, label it from the next
window's cache outcome, append it to an in-memory batch, and periodically
retrain LightGBM regressors used by later inference.
"""

from __future__ import annotations

import ctypes
import errno
import json
import math
import mmap
import os
import random
import signal
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple


DEFAULT_LOH_SHM_KEY = "9876"
DEFAULT_LOH_SEM_TIMEOUT_S = "1.0"
DEFAULT_LOH_POLL_SLEEP_US = "200"
DEFAULT_LOH_PRINT_SHM_LAYOUT = "1"

DEFAULT_LOH_INCLUDE_HIT_MISS_FEATURES = "0"
DEFAULT_LOH_INCLUDE_CACHE_FEATURES = "0"
DEFAULT_LOH_INCLUDE_CANDIDATE_FEATURES = "0"
DEFAULT_LOH_INCLUDE_TOPK_CANDIDATE_FEATURES = "0"
DEFAULT_LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES = "0"
DEFAULT_LOH_INCLUDE_REQUEST = "0"
DEFAULT_LOH_SCORE_USE_IRT = "0"
DEFAULT_LOH_SCORE_USE_COMPOUND = "1"

STATE_OBJ_FEATURE_CAP_DIM = 6
SHM_WEIGHT_DIM = 7
FEATURE_DIM = STATE_OBJ_FEATURE_CAP_DIM
WEIGHT_DIM = SHM_WEIGHT_DIM

LOH_SCORE_MODEL_LINEAR = 0
LOH_MLP_MAX_HIDDEN = 64
LOH_MLP_MAX_PARAMS = LOH_MLP_MAX_HIDDEN * (STATE_OBJ_FEATURE_CAP_DIM + 2) + 1


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _env_int_flag(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return 1 if int(raw.strip()) != 0 else 0
    except ValueError:
        return 1 if _env_flag(name, default != 0) else 0


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


def _env_optional_float(name: str) -> Optional[float]:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    try:
        return float(raw.strip())
    except ValueError:
        return None


def _print_config(message: str) -> None:
    print(message, flush=True)


try:
    SHM_KEY = int(os.environ.get("LOH_SHM_KEY", DEFAULT_LOH_SHM_KEY))
except Exception:
    SHM_KEY = int(DEFAULT_LOH_SHM_KEY)

LOH_SCORE_USE_IRT = _env_int_flag("LOH_SCORE_USE_IRT", int(DEFAULT_LOH_SCORE_USE_IRT))
LOH_SCORE_USE_COMPOUND = _env_int_flag(
    "LOH_SCORE_USE_COMPOUND", int(DEFAULT_LOH_SCORE_USE_COMPOUND)
)
LOH_SCORE_COMPOUND_V2 = _env_int_flag("LOH_SCORE_COMPOUND_V2", 0)
if LOH_SCORE_COMPOUND_V2:
    LOH_SCORE_USE_COMPOUND = 1
    LOH_SCORE_USE_IRT = 0

LOH_USE_FREQ_REC = _env_int_flag("LOH_USE_FREQ_REC", 1)
LOH_USE_FREQ_SIZE = _env_int_flag("LOH_USE_FREQ_SIZE", 1)
LOH_USE_REC_SIZE = _env_int_flag("LOH_USE_REC_SIZE", 1)
LOH_DEBUG_LEVEL = _env_int("LOH_DEBUG_LEVEL", 0)
if LOH_SCORE_USE_COMPOUND:
    LOH_SCORE_USE_IRT = 0

if LOH_SCORE_USE_COMPOUND:
    SCORE_FEATURE_DIM = (
        SHM_WEIGHT_DIM
        if LOH_SCORE_COMPOUND_V2
        else 3 + int(bool(LOH_USE_FREQ_REC)) + int(bool(LOH_USE_FREQ_SIZE)) + int(bool(LOH_USE_REC_SIZE))
    )
elif LOH_SCORE_USE_IRT == 0:
    SCORE_FEATURE_DIM = 3
else:
    SCORE_FEATURE_DIM = 6

STATE_OBJ_FEATURE_DIM = STATE_OBJ_FEATURE_CAP_DIM if LOH_SCORE_USE_IRT else 3


def _flag_enabled(name: str, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def get_state_dim(feature_dim: int, scope: str) -> int:
    n_topk_samples = 32
    samples_per_eviction = 4
    request_history_len = 200
    candidate_source_dim = STATE_OBJ_FEATURE_CAP_DIM if feature_dim >= STATE_OBJ_FEATURE_CAP_DIM else feature_dim

    missratio_dim = 2
    hit_miss_dim = feature_dim * 4 if _flag_enabled(
        "LOH_INCLUDE_HIT_MISS_FEATURES", DEFAULT_LOH_INCLUDE_HIT_MISS_FEATURES
    ) else 0
    cache_dim = feature_dim * 2 if _flag_enabled(
        "LOH_INCLUDE_CACHE_FEATURES", DEFAULT_LOH_INCLUDE_CACHE_FEATURES
    ) else 0
    cand_dim = candidate_source_dim * feature_dim * 2 if _flag_enabled(
        "LOH_INCLUDE_CANDIDATE_FEATURES", DEFAULT_LOH_INCLUDE_CANDIDATE_FEATURES
    ) else 0
    topk_dim = n_topk_samples * feature_dim if _flag_enabled(
        "LOH_INCLUDE_TOPK_CANDIDATE_FEATURES", DEFAULT_LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
    ) else 0
    avgtopk_dim = samples_per_eviction * feature_dim if _flag_enabled(
        "LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES", DEFAULT_LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES
    ) else 0
    request_dim = request_history_len * feature_dim if _flag_enabled(
        "LOH_INCLUDE_REQUEST", DEFAULT_LOH_INCLUDE_REQUEST
    ) else 0

    total = missratio_dim + hit_miss_dim + cache_dim + cand_dim + topk_dim + avgtopk_dim + request_dim
    _print_config(
        f"[CONTEXT_DIM_CONFIG][{scope.upper()}] MISSRATIO={missratio_dim} "
        f"HIT_MISS={hit_miss_dim} CACHE={cache_dim} CAND={cand_dim} "
        f"TOPK={topk_dim} AVGTOPK={avgtopk_dim} REQUEST={request_dim} "
        f"TOTAL={total} (feature_dim={feature_dim})"
    )
    return total


CONTEXT_DIM = get_state_dim(STATE_OBJ_FEATURE_CAP_DIM, scope="context")
STATE_DIM = get_state_dim(STATE_OBJ_FEATURE_DIM, scope="active")

_print_config(
    f"[LOH CONFIG] Score model: gbm-weight-actor "
    f"(SCORE_FEATURE_DIM={SCORE_FEATURE_DIM}, SHM_WEIGHT_DIM={SHM_WEIGHT_DIM})"
)
_print_config(f"[LOH CONFIG] Shared state dims: CONTEXT_DIM={CONTEXT_DIM}, STATE_DIM={STATE_DIM}")


class Timespec(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]


libc = ctypes.CDLL("libc.so.6", use_errno=True)
SEM_FAILED = ctypes.c_void_p(-1).value
libc.sem_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
libc.sem_open.restype = ctypes.c_void_p
libc.sem_close.argtypes = [ctypes.c_void_p]
libc.sem_close.restype = ctypes.c_int
libc.sem_post.argtypes = [ctypes.c_void_p]
libc.sem_post.restype = ctypes.c_int
libc.sem_trywait.argtypes = [ctypes.c_void_p]
libc.sem_trywait.restype = ctypes.c_int
libc.sem_wait.argtypes = [ctypes.c_void_p]
libc.sem_wait.restype = ctypes.c_int
libc.sem_timedwait.argtypes = [ctypes.c_void_p, ctypes.POINTER(Timespec)]
libc.sem_timedwait.restype = ctypes.c_int


class SharedMemoryData(ctypes.Structure):
    _fields_ = [
        ("ready_for_inference", ctypes.c_int),
        ("weights_updated", ctypes.c_int),
        ("terminate", ctypes.c_int),
        ("is_training", ctypes.c_int),
        ("state", ctypes.c_double * CONTEXT_DIM),
        ("weights", ctypes.c_double * SHM_WEIGHT_DIM),
        ("total_evicted_bytes", ctypes.c_uint64),
        ("total_evicted_count", ctypes.c_uint64),
        ("state_version", ctypes.c_uint64),
        ("ack_version", ctypes.c_uint64),
        ("timestamp", ctypes.c_int64),
        ("pending_penalty_count", ctypes.c_int),
        ("score_model", ctypes.c_int),
        ("mlp_hidden", ctypes.c_int),
        ("mlp_param_len", ctypes.c_int),
        ("mlp_params", ctypes.c_double * LOH_MLP_MAX_PARAMS),
    ]


def _print_shm_layout_once() -> None:
    if not _env_flag("LOH_PRINT_SHM_LAYOUT", DEFAULT_LOH_PRINT_SHM_LAYOUT == "1"):
        return
    _print_config(
        f"[SHM] Python SharedMemoryData sizeof={ctypes.sizeof(SharedMemoryData)} bytes "
        f"CONTEXT_DIM={CONTEXT_DIM} SHM_WEIGHT_DIM={SHM_WEIGHT_DIM}"
    )
    for name, _ in SharedMemoryData._fields_:
        _print_config(f"[SHM]   offset {getattr(SharedMemoryData, name).offset:4d} : {name}")


_print_shm_layout_once()


def _parse_vector(raw: Optional[str], expected: int, default: Sequence[float]) -> List[float]:
    if not raw:
        return list(default)
    values: List[float] = []
    for item in raw.replace(";", ",").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            values.append(float(item))
        except ValueError:
            pass
    if len(values) < expected:
        values.extend(float(default[i]) if i < len(default) else 0.0 for i in range(len(values), expected))
    return values[:expected]


def _default_weights() -> List[float]:
    weights = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    raw = os.environ.get("LOH_GBM_FALLBACK_WEIGHTS") or os.environ.get("LOH_FIXED_WEIGHTS")
    return _parse_vector(raw, SHM_WEIGHT_DIM, weights)


def _resolve_model_paths() -> List[Path]:
    raw_paths = os.environ.get("LOH_GBM_MODEL_PATHS", "").strip()
    if raw_paths:
        return [Path(item.strip()) for item in raw_paths.split(",") if item.strip()]

    model_dir = os.environ.get("LOH_GBM_MODEL_DIR", "").strip()
    if not model_dir:
        return []

    root = Path(model_dir)
    manifest = root / "manifest.json"
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        files = data.get("model_files") or data.get("models") or []
        return [(root / item) if not Path(item).is_absolute() else Path(item) for item in files]

    paths: List[Path] = []
    for i in range(SHM_WEIGHT_DIM):
        for name in (f"weight_{i}.txt", f"w{i}.txt", f"model_{i}.txt"):
            candidate = root / name
            if candidate.exists():
                paths.append(candidate)
                break
    return paths


def _lgb_params_to_string(params: Dict[str, Any]) -> bytes:
    items = []
    for key, value in params.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        else:
            rendered = str(value)
        items.append(f"{key}={rendered}")
    return " ".join(items).encode("utf-8")


class PythonLightGbmBackend:
    name = "python-lightgbm"

    def __init__(self, module: Any) -> None:
        self.module = module

    def train(
        self,
        x: Any,
        y: Any,
        sample_weight: Any,
        params: Dict[str, Any],
        num_boost_round: int,
    ) -> Any:
        dataset = self.module.Dataset(x, label=y, weight=sample_weight, free_raw_data=False)
        return self.module.train(params, dataset, num_boost_round=num_boost_round)

    def predict(self, booster: Any, x: Any) -> Any:
        return booster.predict(x)

    def save_model(self, booster: Any, path: Path) -> None:
        booster.save_model(str(path))

    def free_booster(self, _booster: Any) -> None:
        return


class LightGbmCBooster:
    def __init__(self, backend: "CLightGbmBackend", handle: ctypes.c_void_p) -> None:
        self.backend = backend
        self.handle = handle

    def free(self) -> None:
        if self.handle:
            self.backend.lib.LGBM_BoosterFree(self.handle)
            self.handle = ctypes.c_void_p()

    def __del__(self) -> None:
        try:
            self.free()
        except Exception:
            pass


class CLightGbmBackend:
    name = "c-api-lightgbm"
    C_API_DTYPE_FLOAT32 = 0
    C_API_DTYPE_FLOAT64 = 1
    C_API_PREDICT_NORMAL = 0
    C_API_FEATURE_IMPORTANCE_SPLIT = 0

    def __init__(self) -> None:
        raw_path = os.environ.get("LOH_GBM_LIGHTGBM_LIB", "").strip()
        candidates = [raw_path] if raw_path else []
        candidates.extend([
            "/usr/local/lib/lib_lightgbm.so",
            "lib_lightgbm.so",
            "liblightgbm.so",
        ])
        last_error: Optional[Exception] = None
        for candidate in candidates:
            if not candidate:
                continue
            try:
                self.lib = ctypes.CDLL(candidate)
                self.lib_path = candidate
                break
            except OSError as exc:
                last_error = exc
        else:
            raise RuntimeError("cannot load lib_lightgbm.so for LOH GBM online training") from last_error
        self._configure_api()

    def _configure_api(self) -> None:
        self.lib.LGBM_GetLastError.restype = ctypes.c_char_p
        self.lib.LGBM_DatasetCreateFromMat.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int32,
            ctypes.c_int32,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self.lib.LGBM_DatasetCreateFromMat.restype = ctypes.c_int
        self.lib.LGBM_DatasetSetField.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
        ]
        self.lib.LGBM_DatasetSetField.restype = ctypes.c_int
        self.lib.LGBM_DatasetFree.argtypes = [ctypes.c_void_p]
        self.lib.LGBM_DatasetFree.restype = ctypes.c_int
        self.lib.LGBM_BoosterCreate.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self.lib.LGBM_BoosterCreate.restype = ctypes.c_int
        self.lib.LGBM_BoosterUpdateOneIter.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
        self.lib.LGBM_BoosterUpdateOneIter.restype = ctypes.c_int
        self.lib.LGBM_BoosterPredictForMat.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int32,
            ctypes.c_int32,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int64),
            ctypes.c_void_p,
        ]
        self.lib.LGBM_BoosterPredictForMat.restype = ctypes.c_int
        self.lib.LGBM_BoosterSaveModel.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_char_p,
        ]
        self.lib.LGBM_BoosterSaveModel.restype = ctypes.c_int
        self.lib.LGBM_BoosterFree.argtypes = [ctypes.c_void_p]
        self.lib.LGBM_BoosterFree.restype = ctypes.c_int

    def _check(self, result: int) -> None:
        if result == 0:
            return
        raw = self.lib.LGBM_GetLastError()
        message = raw.decode("utf-8", errors="replace") if raw else "unknown LightGBM C API error"
        raise RuntimeError(message)

    def train(
        self,
        x: Any,
        y: Any,
        sample_weight: Any,
        params: Dict[str, Any],
        num_boost_round: int,
    ) -> LightGbmCBooster:
        import numpy as np  # type: ignore

        x_arr = np.ascontiguousarray(x, dtype=np.float64)
        y_arr = np.ascontiguousarray(y, dtype=np.float32)
        w_arr = np.ascontiguousarray(sample_weight, dtype=np.float32)
        params_bytes = _lgb_params_to_string(params)
        dataset = ctypes.c_void_p()
        self._check(
            self.lib.LGBM_DatasetCreateFromMat(
                x_arr.ctypes.data_as(ctypes.c_void_p),
                self.C_API_DTYPE_FLOAT64,
                ctypes.c_int32(x_arr.shape[0]),
                ctypes.c_int32(x_arr.shape[1]),
                ctypes.c_int(1),
                params_bytes,
                ctypes.c_void_p(),
                ctypes.byref(dataset),
            )
        )
        try:
            self._check(
                self.lib.LGBM_DatasetSetField(
                    dataset,
                    b"label",
                    y_arr.ctypes.data_as(ctypes.c_void_p),
                    ctypes.c_int(y_arr.size),
                    self.C_API_DTYPE_FLOAT32,
                )
            )
            self._check(
                self.lib.LGBM_DatasetSetField(
                    dataset,
                    b"weight",
                    w_arr.ctypes.data_as(ctypes.c_void_p),
                    ctypes.c_int(w_arr.size),
                    self.C_API_DTYPE_FLOAT32,
                )
            )
            booster_handle = ctypes.c_void_p()
            self._check(self.lib.LGBM_BoosterCreate(dataset, params_bytes, ctypes.byref(booster_handle)))
            booster = LightGbmCBooster(self, booster_handle)
            try:
                for _ in range(num_boost_round):
                    is_finished = ctypes.c_int(0)
                    self._check(self.lib.LGBM_BoosterUpdateOneIter(booster.handle, ctypes.byref(is_finished)))
                    if int(is_finished.value):
                        break
            except Exception:
                booster.free()
                raise
            return booster
        finally:
            self.lib.LGBM_DatasetFree(dataset)

    def predict(self, booster: LightGbmCBooster, x: Any) -> Any:
        import numpy as np  # type: ignore

        x_arr = np.ascontiguousarray(x, dtype=np.float64)
        out = np.zeros((x_arr.shape[0],), dtype=np.float64)
        out_len = ctypes.c_int64(0)
        self._check(
            self.lib.LGBM_BoosterPredictForMat(
                booster.handle,
                x_arr.ctypes.data_as(ctypes.c_void_p),
                self.C_API_DTYPE_FLOAT64,
                ctypes.c_int32(x_arr.shape[0]),
                ctypes.c_int32(x_arr.shape[1]),
                ctypes.c_int(1),
                self.C_API_PREDICT_NORMAL,
                ctypes.c_int(0),
                ctypes.c_int(0),
                b"",
                ctypes.byref(out_len),
                out.ctypes.data_as(ctypes.c_void_p),
            )
        )
        return out

    def save_model(self, booster: LightGbmCBooster, path: Path) -> None:
        self._check(
            self.lib.LGBM_BoosterSaveModel(
                booster.handle,
                ctypes.c_int(0),
                ctypes.c_int(0),
                self.C_API_FEATURE_IMPORTANCE_SPLIT,
                str(path).encode("utf-8"),
            )
        )

    def free_booster(self, booster: LightGbmCBooster) -> None:
        booster.free()


class OnlineWeightTrainer:
    def __init__(self, input_dim: int, fallback_weights: Sequence[float]) -> None:
        self.enabled = _env_flag("LOH_GBM_ONLINE_TRAIN", False)
        self.input_dim = input_dim
        self.fallback_weights = list(fallback_weights)
        self.batch_size = max(1, _env_int("LOH_GBM_ONLINE_BATCH_SIZE", 128))
        self.min_train_samples = max(2, _env_int("LOH_GBM_ONLINE_MIN_TRAIN_SAMPLES", self.batch_size))
        self.max_samples = max(self.min_train_samples, _env_int("LOH_GBM_ONLINE_MAX_SAMPLES", 4096))
        self.samples: Deque[Tuple[List[float], List[float], float, int]] = deque(maxlen=self.max_samples)
        self.pending: Optional[Tuple[List[float], List[float], int]] = None
        self.samples_since_train = 0
        self.train_count = 0
        self.boosters: List[Any] = []
        self.last_reward: Optional[float] = None
        self.last_immediate_reward: Optional[float] = None
        self.last_explored = False

        alpha_default = _env_float("LOH_MISS_RATIO_WEIGHT", 1.0)
        self.reward_alpha = _env_float("LOH_GBM_REWARD_OBJ_WEIGHT", alpha_default)
        self.reward_beta = _env_float("LOH_GBM_REWARD_BYTE_WEIGHT", 1.0 - alpha_default)
        self.reward_mode = os.environ.get("LOH_GBM_ONLINE_REWARD_MODE", "delta").strip().lower()
        if self.reward_mode not in {"absolute", "delta"}:
            self.reward_mode = "delta"
        self.reward_scale = _env_float("LOH_GBM_ONLINE_REWARD_SCALE", 1.0)
        self.reward_clip = _env_float("LOH_GBM_ONLINE_REWARD_CLIP", 1.0)

        self.explore_prob = max(0.0, min(1.0, _env_float("LOH_GBM_ONLINE_EXPLORE_PROB", 0.35)))
        self.bootstrap_explore_prob = max(
            0.0,
            min(1.0, _env_float("LOH_GBM_ONLINE_BOOTSTRAP_EXPLORE_PROB", 1.0)),
        )
        self.explore_std = max(0.0, _env_float("LOH_GBM_ONLINE_EXPLORE_STD", 0.10))
        self.explore_decay = max(0.0, min(1.0, _env_float("LOH_GBM_ONLINE_EXPLORE_DECAY", 1.0)))
        self.min_explore_std = max(0.0, _env_float("LOH_GBM_ONLINE_MIN_EXPLORE_STD", 0.0))
        self.seed = _env_int("LOH_GBM_ONLINE_SEED", 42)
        self.rng = random.Random(self.seed)

        self.elite_quantile = max(0.0, min(0.99, _env_float("LOH_GBM_ONLINE_ELITE_QUANTILE", 0.70)))
        self.min_elite = max(2, _env_int("LOH_GBM_ONLINE_MIN_ELITE", 8))
        self.min_sample_weight = max(0.0, _env_float("LOH_GBM_ONLINE_MIN_SAMPLE_WEIGHT", 0.10))
        self.max_sample_weight = max(self.min_sample_weight, _env_float("LOH_GBM_ONLINE_MAX_SAMPLE_WEIGHT", 8.0))

        self.num_boost_round = max(1, _env_int("LOH_GBM_ONLINE_NUM_BOOST_ROUND", 64))
        self.learning_rate = _env_float("LOH_GBM_ONLINE_LEARNING_RATE", 0.05)
        self.num_leaves = max(2, _env_int("LOH_GBM_ONLINE_NUM_LEAVES", 31))
        self.min_data_in_leaf = max(1, _env_int("LOH_GBM_ONLINE_MIN_DATA_IN_LEAF", 8))
        self.feature_fraction = max(0.01, min(1.0, _env_float("LOH_GBM_ONLINE_FEATURE_FRACTION", 1.0)))
        self.bagging_fraction = max(0.01, min(1.0, _env_float("LOH_GBM_ONLINE_BAGGING_FRACTION", 1.0)))
        self.bagging_freq = max(0, _env_int("LOH_GBM_ONLINE_BAGGING_FREQ", 0))
        self.num_threads = max(1, _env_int("LOH_GBM_ONLINE_NUM_THREADS", 1))
        self.model_dir = os.environ.get("LOH_GBM_ONLINE_MODEL_DIR", "").strip()
        self._np = None
        self._backend: Optional[Any] = None

        if self.enabled:
            self._ensure_backend()
            _print_config(
                "[GBM ONLINE] enabled: "
                f"batch_size={self.batch_size} min_train_samples={self.min_train_samples} "
                f"max_samples={self.max_samples} reward_mode={self.reward_mode} "
                f"reward_weights=({self.reward_alpha:.3f},{self.reward_beta:.3f}) "
                f"explore_prob={self.explore_prob:.3f} explore_std={self.explore_std:.3f} "
                f"backend={self._backend.name if self._backend is not None else 'unknown'}"
            )

    def _ensure_backend(self) -> None:
        if self._np is not None and self._backend is not None:
            return
        try:
            import numpy as np  # type: ignore
        except Exception as exc:
            raise RuntimeError("LOH_GBM_ONLINE_TRAIN=1 requires numpy") from exc
        self._np = np

        backend_preference = os.environ.get("LOH_GBM_BACKEND", "auto").strip().lower()
        if backend_preference in {"auto", "python", "python-lightgbm"}:
            try:
                import lightgbm as lgb  # type: ignore
                self._backend = PythonLightGbmBackend(lgb)
                return
            except Exception as exc:
                if backend_preference in {"python", "python-lightgbm"}:
                    raise RuntimeError("LOH_GBM_BACKEND=python requires Python package lightgbm") from exc

        if backend_preference in {"auto", "c", "c-api", "c-api-lightgbm"}:
            self._backend = CLightGbmBackend()
            return

        raise RuntimeError(f"unknown LOH_GBM_BACKEND={backend_preference!r}")

    def observe_outcome(self, data: SharedMemoryData) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        immediate_reward = self._immediate_reward(data)
        reward = immediate_reward
        if self.reward_mode == "delta":
            reward = 0.0 if self.last_immediate_reward is None else immediate_reward - self.last_immediate_reward
        reward *= self.reward_scale
        if self.reward_clip > 0.0:
            reward = max(-self.reward_clip, min(self.reward_clip, reward))
        self.last_immediate_reward = immediate_reward

        info: Dict[str, Any] = {
            "reward": float(reward),
            "immediate_reward": float(immediate_reward),
            "buffer_size": len(self.samples),
            "train_count": self.train_count,
        }
        if self.pending is not None:
            state, weights, version = self.pending
            self.samples.append((list(state), list(weights), float(reward), int(version)))
            self.samples_since_train += 1
            self.last_reward = float(reward)
            info["labeled_state_version"] = int(version)
            info["buffer_size"] = len(self.samples)
            if self._maybe_train():
                info["trained"] = True
                info["train_count"] = self.train_count
                info["buffer_size"] = len(self.samples)
        return info

    def _immediate_reward(self, data: SharedMemoryData) -> float:
        obj_hit_ratio = float(data.state[0]) if CONTEXT_DIM >= 1 else 0.0
        byte_hit_ratio = float(data.state[1]) if CONTEXT_DIM >= 2 else 0.0
        return float(self.reward_alpha) * obj_hit_ratio + float(self.reward_beta) * byte_hit_ratio

    def _maybe_train(self) -> bool:
        if self.samples_since_train < self.batch_size or len(self.samples) < self.min_train_samples:
            return False
        self._ensure_backend()
        np = self._np
        backend = self._backend
        assert np is not None and backend is not None

        rows = list(self.samples)
        x = np.asarray([row[0] for row in rows], dtype=np.float64)
        y = np.asarray([row[1] for row in rows], dtype=np.float64)
        rewards = np.asarray([row[2] for row in rows], dtype=np.float64)

        train_x = x
        train_y = y
        train_rewards = rewards
        if len(rows) >= self.min_elite and self.elite_quantile > 0.0:
            threshold = float(np.quantile(rewards, self.elite_quantile))
            mask = rewards >= threshold
            if int(np.sum(mask)) >= self.min_elite:
                train_x = x[mask]
                train_y = y[mask]
                train_rewards = rewards[mask]

        reward_center = float(np.mean(train_rewards)) if train_rewards.size else 0.0
        reward_scale = float(np.std(train_rewards)) if train_rewards.size else 0.0
        if reward_scale < 1e-9:
            sample_weight = np.ones((train_x.shape[0],), dtype=np.float64)
        else:
            sample_weight = 1.0 + np.maximum(0.0, (train_rewards - reward_center) / reward_scale)
        sample_weight = np.clip(sample_weight, self.min_sample_weight, self.max_sample_weight)

        params = {
            "boosting_type": "gbdt",
            "objective": "regression",
            "metric": "l2",
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "min_data_in_leaf": self.min_data_in_leaf,
            "feature_fraction": self.feature_fraction,
            "bagging_fraction": self.bagging_fraction,
            "bagging_freq": self.bagging_freq,
            "num_threads": self.num_threads,
            "seed": self.seed + self.train_count,
            "verbosity": -1,
            "force_col_wise": True,
        }

        for booster in self.boosters:
            try:
                backend.free_booster(booster)
            except Exception:
                pass

        boosters = []
        for dim in range(SHM_WEIGHT_DIM):
            boosters.append(
                backend.train(
                    train_x,
                    train_y[:, dim],
                    sample_weight,
                    params,
                    self.num_boost_round,
                )
            )

        self.boosters = boosters
        self.train_count += 1
        self.samples_since_train = 0
        self._save_latest_model(params, int(train_x.shape[0]), float(np.mean(train_rewards)))
        _print_config(
            f"[GBM ONLINE] trained #{self.train_count}: "
            f"samples={len(rows)} train_rows={int(train_x.shape[0])} "
            f"reward_mean={float(np.mean(train_rewards)):.6f} reward_max={float(np.max(train_rewards)):.6f}"
        )
        return True

    def _save_latest_model(self, params: Dict[str, Any], train_rows: int, train_reward_mean: float) -> None:
        if not self.model_dir:
            return
        root = Path(self.model_dir)
        root.mkdir(parents=True, exist_ok=True)
        model_files = []
        for dim, booster in enumerate(self.boosters):
            name = f"weight_{dim}.txt"
            if self._backend is not None:
                self._backend.save_model(booster, root / name)
            model_files.append(name)
        manifest = {
            "kind": "loh_gbm_online_weight_model",
            "backend": self._backend.name if self._backend is not None else "unknown",
            "input_dim": self.input_dim,
            "weight_dim": SHM_WEIGHT_DIM,
            "n_samples": len(self.samples),
            "train_rows": train_rows,
            "train_count": self.train_count,
            "reward_mode": self.reward_mode,
            "train_reward_mean": train_reward_mean,
            "model_files": model_files,
            "params": params,
        }
        (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def predict_online(self, state: Sequence[float]) -> Optional[List[float]]:
        if not self.enabled or not self.boosters:
            return None
        self._ensure_backend()
        np = self._np
        backend = self._backend
        assert np is not None and backend is not None
        x = np.asarray([list(state)], dtype=np.float64)
        return [float(backend.predict(booster, x)[0]) for booster in self.boosters[:SHM_WEIGHT_DIM]]

    def maybe_explore(self, weights: Sequence[float], has_model: bool) -> List[float]:
        if not self.enabled:
            self.last_explored = False
            return list(weights)
        prob = self.explore_prob if has_model else self.bootstrap_explore_prob
        self.last_explored = self.rng.random() < prob and self.explore_std > 0.0
        if not self.last_explored:
            return list(weights)

        out = list(weights)
        active_dim = max(1, min(SCORE_FEATURE_DIM, SHM_WEIGHT_DIM))
        for i in range(active_dim):
            out[i] = float(out[i]) + self.rng.gauss(0.0, self.explore_std)
        if self.explore_decay < 1.0:
            self.explore_std = max(self.min_explore_std, self.explore_std * self.explore_decay)
        return out

    def set_pending(self, state: Sequence[float], weights: Sequence[float], state_version: int) -> None:
        if not self.enabled:
            return
        self.pending = (list(state), list(weights), int(state_version))

    def status(self) -> Dict[str, Any]:
        if not self.enabled:
            return {}
        return {
            "enabled": True,
            "backend": self._backend.name if self._backend is not None else None,
            "buffer_size": len(self.samples),
            "samples_since_train": self.samples_since_train,
            "train_count": self.train_count,
            "last_reward": self.last_reward,
            "last_explored": self.last_explored,
            "explore_std": self.explore_std,
        }

    def close(self) -> None:
        if self._backend is None:
            return
        for booster in self.boosters:
            try:
                self._backend.free_booster(booster)
            except Exception:
                pass
        self.boosters = []


class WeightPredictor:
    def __init__(self) -> None:
        self.fallback_weights = _default_weights()
        self.last_weights = list(self.fallback_weights)
        self.weight_ema = _env_float("LOH_GBM_WEIGHT_EMA", _env_float("LOH_WEIGHT_EMA", 0.0))
        self.weight_clip = _env_float("LOH_GBM_WEIGHT_CLIP", _env_float("LOH_WEIGHT_CLIP", 0.0))
        self.weight_lb = _env_optional_float("LOH_GBM_WEIGHT_LB")
        self.weight_ub = _env_optional_float("LOH_GBM_WEIGHT_UB")
        self.normalize = os.environ.get("LOH_GBM_WEIGHT_NORMALIZE", "none").strip().lower()
        self.input_dim = self._resolve_input_dim()
        self.trace_log_path = os.environ.get("LOH_GBM_TRACE_LOG", "").strip()
        self.trace_log = open(self.trace_log_path, "a", encoding="utf-8") if self.trace_log_path else None
        self.boosters = []
        self.model_paths = _resolve_model_paths()
        self.online_trainer = OnlineWeightTrainer(self.input_dim, self.fallback_weights)
        self._load_boosters()

    def close(self) -> None:
        self.online_trainer.close()
        if self.trace_log is not None:
            self.trace_log.close()

    def _resolve_input_dim(self) -> int:
        raw = os.environ.get("LOH_GBM_INPUT_DIM", "context").strip().lower()
        if raw in {"", "context", "context_dim"}:
            return CONTEXT_DIM
        if raw in {"active", "state", "state_dim"}:
            return STATE_DIM
        try:
            dim = int(raw)
            return max(1, min(dim, CONTEXT_DIM))
        except ValueError:
            return CONTEXT_DIM

    def _load_boosters(self) -> None:
        if not self.model_paths:
            if _env_flag("LOH_GBM_REQUIRE_MODEL", False):
                raise RuntimeError("LOH_GBM_REQUIRE_MODEL=1 but no LOH_GBM_MODEL_DIR/PATHS provided")
            _print_config(
                "[GBM ACTOR] No LightGBM model configured; using fallback weights: "
                + ",".join(f"{w:.6f}" for w in self.fallback_weights)
            )
            return

        try:
            import lightgbm as lgb  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "LightGBM Python package is required when LOH_GBM_MODEL_DIR/PATHS is set"
            ) from exc

        for path in self.model_paths:
            if not path.exists():
                raise FileNotFoundError(path)
            self.boosters.append(lgb.Booster(model_file=str(path)))

        if len(self.boosters) not in {SCORE_FEATURE_DIM, SHM_WEIGHT_DIM}:
            _print_config(
                f"[GBM ACTOR] WARNING: loaded {len(self.boosters)} boosters; "
                f"expected SCORE_FEATURE_DIM={SCORE_FEATURE_DIM} or SHM_WEIGHT_DIM={SHM_WEIGHT_DIM}"
            )
        _print_config(
            f"[GBM ACTOR] Loaded {len(self.boosters)} LightGBM boosters, input_dim={self.input_dim}"
        )

    def predict(self, data: SharedMemoryData) -> List[float]:
        state = [float(data.state[i]) for i in range(min(self.input_dim, CONTEXT_DIM))]
        if len(state) < self.input_dim:
            state.extend(0.0 for _ in range(self.input_dim - len(state)))

        online_info = self.online_trainer.observe_outcome(data)
        online_weights = self.online_trainer.predict_online(state)
        model_name = "lightgbm_online" if online_weights is not None else "fallback"

        if online_weights is not None:
            weights = list(online_weights)
        elif self.boosters:
            import numpy as np  # type: ignore

            x = np.asarray([state], dtype=np.float64)
            weights = []
            for booster in self.boosters[:SHM_WEIGHT_DIM]:
                pred = booster.predict(x)
                weights.append(float(pred[0]))
            model_name = "lightgbm"
        else:
            weights = list(self.fallback_weights)

        weights = self.online_trainer.maybe_explore(weights, has_model=(online_weights is not None or bool(self.boosters)))
        weights = self._sanitize(weights)
        self.online_trainer.set_pending(state, weights, int(data.state_version))
        if self.online_trainer.enabled and self.online_trainer.last_explored:
            model_name += "+explore"
        self._log_trace(data, state, weights, model_name, online_info)
        self.last_weights = list(weights)
        return weights

    def _sanitize(self, weights: Sequence[float]) -> List[float]:
        out = [0.0] * SHM_WEIGHT_DIM
        for i in range(SHM_WEIGHT_DIM):
            value = float(weights[i]) if i < len(weights) else 0.0
            if not math.isfinite(value):
                value = self.last_weights[i] if i < len(self.last_weights) else self.fallback_weights[i]
            out[i] = value

        if self.weight_clip > 0.0:
            clip = abs(self.weight_clip)
            out = [max(-clip, min(clip, value)) for value in out]

        if self.weight_lb is not None:
            out = [max(self.weight_lb, value) for value in out]
        if self.weight_ub is not None:
            out = [min(self.weight_ub, value) for value in out]

        if self.normalize in {"l1", "abs"}:
            denom = sum(abs(value) for value in out[:SCORE_FEATURE_DIM])
            if denom > 1e-12:
                out = [value / denom for value in out]
        elif self.normalize in {"sum", "simplex"}:
            denom = sum(out[:SCORE_FEATURE_DIM])
            if abs(denom) > 1e-12:
                out = [value / denom for value in out]

        if 0.0 < self.weight_ema < 1.0:
            out = [self.weight_ema * self.last_weights[i] + (1.0 - self.weight_ema) * out[i] for i in range(SHM_WEIGHT_DIM)]

        if LOH_SCORE_USE_COMPOUND:
            if not LOH_USE_FREQ_REC:
                out[3] = 0.0
            if not LOH_USE_FREQ_SIZE:
                out[4] = 0.0
            if not LOH_USE_REC_SIZE:
                out[5] = 0.0
            if not LOH_SCORE_COMPOUND_V2:
                out[6] = 0.0
        elif LOH_SCORE_USE_IRT == 0:
            for i in range(3, SHM_WEIGHT_DIM):
                out[i] = 0.0
        else:
            out[6] = 0.0

        return out

    def _log_trace(
        self,
        data: SharedMemoryData,
        state: Sequence[float],
        weights: Sequence[float],
        model_name: str,
        online_info: Optional[Dict[str, Any]],
    ) -> None:
        if self.trace_log is None:
            return
        record = {
            "state_version": int(data.state_version),
            "timestamp": int(data.timestamp),
            "state": list(state),
            "weights": list(weights),
            "model": model_name,
        }
        online_status = self.online_trainer.status()
        if online_status:
            record["online"] = online_status
        if online_info:
            record["online_outcome"] = online_info
        self.trace_log.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.trace_log.flush()


class LohGbmActor:
    def __init__(self) -> None:
        self.shm_key = SHM_KEY
        self.shm_file = None
        self.shm = None
        self.stop_requested = False
        self.sem_ready = None
        self.sem_ack = None
        self.sem_enabled = False
        self.sem_requested = not _env_flag("LOH_DISABLE_SEMAPHORE", False)
        self.sem_timeout_s = _env_float("LOH_SEM_TIMEOUT_S", float(DEFAULT_LOH_SEM_TIMEOUT_S))
        self.poll_sleep_s = max(_env_int("LOH_POLL_SLEEP_US", int(DEFAULT_LOH_POLL_SLEEP_US)), 0) / 1_000_000.0
        self.disable_fsync = _env_flag("LOH_DISABLE_FSYNC", False)
        self.log_every = _env_int("LOH_GBM_LOG_EVERY", _env_int("LOH_WEIGHT_LOG_EVERY", 100))
        self.predictor = WeightPredictor()

    def close(self) -> None:
        self.predictor.close()
        if self.sem_ready is not None:
            libc.sem_close(self.sem_ready)
            self.sem_ready = None
        if self.sem_ack is not None:
            libc.sem_close(self.sem_ack)
            self.sem_ack = None
        if self.shm is not None:
            self.shm.close()
            self.shm = None
        if self.shm_file is not None:
            self.shm_file.close()
            self.shm_file = None

    def request_stop(self, *_args) -> None:
        self.stop_requested = True

    def attach_shared_memory(self) -> None:
        shm_path = Path(f"/dev/shm/loh_ac_{self.shm_key}")
        expected_size = ctypes.sizeof(SharedMemoryData)
        if not shm_path.exists():
            shm_path.write_bytes(b"\x00" * expected_size)
        elif shm_path.stat().st_size < expected_size:
            with shm_path.open("r+b") as file_obj:
                file_obj.truncate(expected_size)

        self.shm_file = shm_path.open("r+b")
        self.shm = mmap.mmap(self.shm_file.fileno(), expected_size)
        os.chmod(shm_path, 0o666)
        _print_config(f"[GBM ACTOR] Shared memory connected: {shm_path} size={expected_size}")

    def init_semaphores(self) -> None:
        if not self.sem_requested:
            _print_config("[SEM] semaphore disabled by LOH_DISABLE_SEMAPHORE=1; polling only")
            return

        ready_name = f"/loh_ac_ready_{self.shm_key}".encode()
        ack_name = f"/loh_ac_ack_{self.shm_key}".encode()
        sem_ready = libc.sem_open(ready_name, os.O_CREAT, 0o666, 0)
        if sem_ready == SEM_FAILED:
            _print_config(f"[SEM] sem_open ready failed: {os.strerror(ctypes.get_errno())}; polling only")
            return
        sem_ack = libc.sem_open(ack_name, os.O_CREAT, 0o666, 0)
        if sem_ack == SEM_FAILED:
            _print_config(f"[SEM] sem_open ack failed: {os.strerror(ctypes.get_errno())}; polling only")
            libc.sem_close(sem_ready)
            return

        self.sem_ready = sem_ready
        self.sem_ack = sem_ack
        self.sem_enabled = True
        self._drain_sem(self.sem_ready)
        self._drain_sem(self.sem_ack)
        _print_config("[SEM] POSIX semaphore handshake enabled")

    def _drain_sem(self, sem_handle) -> None:
        while True:
            result = libc.sem_trywait(sem_handle)
            if result == 0:
                continue
            err = ctypes.get_errno()
            if err == errno.EINTR:
                continue
            break

    def _sem_wait_ready(self) -> bool:
        if not self.sem_enabled or self.sem_ready is None:
            return False
        deadline = time.time() + max(self.sem_timeout_s, 0.001)
        ts = Timespec(int(deadline), int((deadline - int(deadline)) * 1e9))
        while not self.stop_requested:
            result = libc.sem_timedwait(self.sem_ready, ctypes.byref(ts))
            if result == 0:
                return True
            err = ctypes.get_errno()
            if err == errno.EINTR:
                continue
            if err == errno.ETIMEDOUT:
                return False
            _print_config(f"[SEM] sem_timedwait failed: {os.strerror(err)}; polling only")
            self.sem_enabled = False
            return False
        return False

    def _sem_post_ack(self) -> None:
        if not self.sem_enabled or self.sem_ack is None:
            return
        if libc.sem_post(self.sem_ack) != 0:
            _print_config(f"[SEM] sem_post ack failed: {os.strerror(ctypes.get_errno())}; polling only")
            self.sem_enabled = False

    def read_shm(self) -> Optional[SharedMemoryData]:
        if self.shm is None:
            return None
        try:
            self.shm.seek(0)
            raw = self.shm.read(ctypes.sizeof(SharedMemoryData))
            return SharedMemoryData.from_buffer_copy(raw)
        except Exception as exc:
            _print_config(f"[GBM ACTOR] read shm failed: {exc}")
            return None

    def write_shm(self, data: SharedMemoryData) -> bool:
        if self.shm is None:
            return False
        try:
            raw = ctypes.string_at(ctypes.byref(data), ctypes.sizeof(data))
            self.shm.seek(0)
            self.shm.write(raw)
            self.shm.flush()
            if self.shm_file is not None and not self.disable_fsync:
                os.fsync(self.shm_file.fileno())
            return True
        except Exception as exc:
            _print_config(f"[GBM ACTOR] write shm failed: {exc}")
            return False

    def run(self) -> None:
        self.attach_shared_memory()
        self.init_semaphores()
        _print_config(
            f"[GBM ACTOR] started shm_key={self.shm_key} input_dim={self.predictor.input_dim} "
            f"score_feature_dim={SCORE_FEATURE_DIM} poll_sleep_us={int(self.poll_sleep_s * 1_000_000)}"
        )

        updates = 0
        last_ready_version = -1
        while not self.stop_requested:
            self._sem_wait_ready()
            data = self.read_shm()
            if data is None:
                time.sleep(self.poll_sleep_s)
                continue
            if data.terminate:
                _print_config("[GBM ACTOR] terminate flag received")
                break
            if data.ready_for_inference != 1:
                time.sleep(self.poll_sleep_s)
                continue

            state_version = int(data.state_version)
            if state_version == last_ready_version and data.weights_updated:
                time.sleep(self.poll_sleep_s)
                continue

            weights = self.predictor.predict(data)
            for i in range(SHM_WEIGHT_DIM):
                data.weights[i] = float(weights[i])
            data.score_model = int(LOH_SCORE_MODEL_LINEAR)
            data.mlp_hidden = 0
            data.mlp_param_len = 0
            data.ack_version = data.state_version
            data.weights_updated = 1
            data.ready_for_inference = 0
            data.is_training = 0

            if self.write_shm(data):
                self._sem_post_ack()
                updates += 1
                last_ready_version = state_version
                if LOH_DEBUG_LEVEL > 0 and self.log_every > 0 and (updates == 1 or updates % self.log_every == 0):
                    _print_config(
                        f"[WEIGHTS_UPDATED] [seq {state_version}] dim={SHM_WEIGHT_DIM} "
                        f"[{', '.join(f'{w:.6f}' for w in weights)}] updates={updates}"
                    )
            else:
                time.sleep(self.poll_sleep_s)

        _print_config(f"[GBM ACTOR] stopped updates={updates}")


def main() -> int:
    actor = LohGbmActor()
    signal.signal(signal.SIGTERM, actor.request_stop)
    signal.signal(signal.SIGINT, actor.request_stop)
    try:
        actor.run()
        return 0
    finally:
        actor.close()


if __name__ == "__main__":
    sys.exit(main())
