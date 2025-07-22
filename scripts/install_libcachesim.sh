#!/bin/bash
set -euo pipefail

SOURCE=$(readlink -f "${BASH_SOURCE[0]}")
DIR=$(dirname "${SOURCE}")

cd "${DIR}"/../
mkdir -p _build
cd _build
cmake -G Ninja \
  -DENABLE_LRB=ON \
  -DENABLE_GLCACHE=ON \
  -DENABLE_3L_CACHE=ON \
  -DSUPPORT_TTL=ON \
  -DUSE_HUGEPAGE=ON \
  -DOPT_SUPPORT_ZSTD_TRACE=ON \
  -DENABLE_TESTS=ON \
  -DBUILD_SHARED_LIBS=ON \
  -DLOG_LEVEL=INFO \
  ..
ninja
cd "${DIR}"
