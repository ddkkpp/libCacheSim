#!/bin/bash
set -euo pipefail

SOURCE=$(readlink -f "${BASH_SOURCE[0]}")
DIR=$(dirname "${SOURCE}")

cd "${DIR}"/../
mkdir -p _build
cd _build

EXTRA_CXX_FLAGS=""
if "${CXX:-c++}" --version 2>/dev/null | grep -qi "gcc"; then
  EXTRA_CXX_FLAGS="-Wno-error=cast-user-defined -Wno-error=array-bounds"
fi

cmake -G Ninja \
  -DCMAKE_CXX_FLAGS="${EXTRA_CXX_FLAGS}" \
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
