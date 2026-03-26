#!/bin/bash
set -euo pipefail

SOURCE=$(readlink -f "${BASH_SOURCE[0]}")
SCRIPT_DIR=$(dirname "${SOURCE}")
CURR_DIR=$(pwd)

usage() {
	echo "Usage: $0 [options] [-- program_args]"
	echo "Options:"
	echo "  -h, --help      Show this help message"
	echo "  -c, --clean     Clean the build directory"
	echo "  -r, --release   Build in Release mode (_build_rel, -O2 -DNDEBUG)"
	echo "  --              Separator between script options and program arguments"
	echo ""
	echo "Example:"
	echo "  $0 -c -- ${SCRIPT_DIR}/../data/cloudPhysicsIO.oracleGeneral.bin oracleGeneral LRU,S3-FIFO 200M,1GB"
	echo "  $0 -r -c    # clean release build with LOH_INCLUDE_* support"
	echo "  note that the trace filepath is relative to current directory"
	exit 1
}

# Parse command line arguments
CLEAN=0
BUILD_RELEASE=0
PROGRAM_ARGS=()

while [[ $# -gt 0 ]]; do
	case $1 in
	-h | --help)
		usage
		;;
	-c | --clean)
		CLEAN=1
		shift
		;;
	-r | --release)
		BUILD_RELEASE=1
		shift
		;;
	-d | --default)
		PROGRAM_ARGS=("data/cloudPhysicsIO.vscsi" "vscsi" "lru,s3fifo" "100m,1gb")
		shift
		;;
	--)
		shift
		PROGRAM_ARGS=("$@")
		break
		;;
	*)
		echo "Unknown option: $1"
		usage
		;;
	esac
done

cd "${SCRIPT_DIR}"/../

# Select build directory based on mode
if [[ ${BUILD_RELEASE} -eq 1 ]]; then
	BUILD_DIR="_build_rel"
	BUILD_MODE="Release"
else
	BUILD_DIR="_build_dbg"
	BUILD_MODE="Debug"
fi

# Clean build directory if requested
if [[ ${CLEAN} -eq 1 ]]; then
	echo "Cleaning ${BUILD_MODE} build directory (${BUILD_DIR})..."
	rm -rf "${BUILD_DIR}" || true 2>/dev/null
fi

# Create and enter build directory
mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"

# Configure and build with warning flags
echo "Configuring and building project in ${BUILD_MODE} mode..."

# 通过环境变量控制 LOH_* 相关宏：
#   - LOH_INCLUDE_HIT_MISS_FEATURES    (0/1) - Hit/Miss统计 (24维)
#   - LOH_INCLUDE_CACHE_FEATURES       (0/1) - 缓存特征统计 (12维)
#   - LOH_INCLUDE_CANDIDATE_FEATURES   (0/1) - 候选集合统计 (72维)
#   - LOH_INCLUDE_TOPK_CANDIDATE_FEATURES (0/1) - TopK候选采样 (32*6=192维)
#   - LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES (0/1) - AvgTopK平均特征 (4*6=24维)
#   - LOH_INCLUDE_REQUEST              (0/1) - 最近请求历史 (REQUEST_HISTORY_LEN×6 维)
#   - LOH_DEBUG_LEVEL                  (0/1/2/3/4) - 调试级别
# 注：前2维(hit_ratio, byte_hit_ratio)始终传递，不再通过宏控制
# 如果未设置，则使用 C 源码中的默认值。

LOH_DEFS=""
if [ -n "${LOH_INCLUDE_CACHE_FEATURES:-}" ]; then
	LOH_DEFS+=" -DLOH_INCLUDE_CACHE_FEATURES=${LOH_INCLUDE_CACHE_FEATURES}"
fi
if [ -n "${LOH_INCLUDE_CANDIDATE_FEATURES:-}" ]; then
	LOH_DEFS+=" -DLOH_INCLUDE_CANDIDATE_FEATURES=${LOH_INCLUDE_CANDIDATE_FEATURES}"
fi
if [ -n "${LOH_INCLUDE_HIT_MISS_FEATURES:-}" ]; then
	LOH_DEFS+=" -DLOH_INCLUDE_HIT_MISS_FEATURES=${LOH_INCLUDE_HIT_MISS_FEATURES}"
fi
if [ -n "${LOH_INCLUDE_TOPK_CANDIDATE_FEATURES:-}" ]; then
	LOH_DEFS+=" -DLOH_INCLUDE_TOPK_CANDIDATE_FEATURES=${LOH_INCLUDE_TOPK_CANDIDATE_FEATURES}"
fi
if [ -n "${LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES:-}" ]; then
	LOH_DEFS+=" -DLOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=${LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES}"
fi
if [ -n "${LOH_INCLUDE_REQUEST:-}" ]; then
	LOH_DEFS+=" -DLOH_INCLUDE_REQUEST=${LOH_INCLUDE_REQUEST}"
fi
if [ -n "${LOH_DEBUG_LEVEL:-}" ]; then
	LOH_DEFS+=" -DLOH_DEBUG_LEVEL=${LOH_DEBUG_LEVEL}"
fi
if [ -n "${LOH_ENABLE_PENALTY:-}" ]; then
	LOH_DEFS+=" -DLOH_ENABLE_PENALTY=${LOH_ENABLE_PENALTY}"
fi
# 支持通过环境变量控制 C 端的 perf profiling 宏：
# - 优先使用 LOH_PERF_PROFILING（直接匹配宏名），若未设置则使用 LOH_ENABLE_PROFILING
# Example: LOH_ENABLE_PROFILING=0 bash scripts/debug.sh -c
if [ -n "${LOH_PERF_PROFILING:-}" ]; then
    LOH_DEFS+=" -DLOH_PERF_PROFILING=${LOH_PERF_PROFILING}"
elif [ -n "${LOH_ENABLE_PROFILING:-}" ]; then
    LOH_DEFS+=" -DLOH_PERF_PROFILING=${LOH_ENABLE_PROFILING}"
fi

if [ -n "${LOH_DEFS}" ]; then
	echo "[debug.sh] Using LOH compile defs:${LOH_DEFS}"
else
	echo "[debug.sh] No LOH_* environment overrides; using C defaults (AVGTOPK=1, others=0)."
fi

if [[ ${BUILD_RELEASE} -eq 1 ]]; then
	C_FLAGS="-O2 -DNDEBUG -DG_DISABLE_ASSERT -Wno-unused-variable -Wno-unused-function -Wno-unused-parameter -Wno-unused-but-set-variable${LOH_DEFS}"
	CXX_FLAGS="-O2 -DNDEBUG -DG_DISABLE_ASSERT -Wno-unused-variable -Wno-unused-function -Wno-unused-parameter -Wno-unused-but-set-variable${LOH_DEFS}"
else
	C_FLAGS="-Wall -Wextra -Werror -Wno-unused-variable -Wno-unused-function -Wno-unused-parameter -Wno-unused-but-set-variable -Wpedantic -Wformat=2 -Wformat-security -Wshadow -Wwrite-strings -Wstrict-prototypes -Wold-style-definition -Wredundant-decls -Wnested-externs -Wmissing-include-dirs${LOH_DEFS}"
	CXX_FLAGS="-Wall -Wextra -Werror -Wno-error=cast-user-defined -Wno-error=array-bounds -Wno-deprecated-copy -Wno-unused-variable -Wno-unused-function -Wno-unused-parameter -Wno-unused-but-set-variable -Wno-pedantic -Wformat=2 -Wformat-security -Wshadow -Wwrite-strings -Wmissing-include-dirs${LOH_DEFS}"
fi

cmake -G Ninja -DCMAKE_BUILD_TYPE="${BUILD_MODE}" \
	-DCMAKE_C_FLAGS="${C_FLAGS}" \
	-DCMAKE_CXX_FLAGS="${CXX_FLAGS}" \
	-DCMAKE_BUILD_WITH_INSTALL_RPATH=TRUE \
	-DENABLE_GLCACHE=ON -DENABLE_LRB=ON -DENABLE_3L_CACHE=ON \
	..

ninja

# Return to script directory
cd "${CURR_DIR}"

if [[ ${#PROGRAM_ARGS[@]} -ne 0 ]]; then
	# Run the program with gdb and pass arguments
	echo "Starting debug session with arguments..."
	gdb -ex "set print thread-events off" -ex r --args "${SCRIPT_DIR}"/../${BUILD_DIR}/bin/cachesim "${PROGRAM_ARGS[@]}"
else
	echo ''
	echo '########################################################'
	echo "${BUILD_MODE} build is at ${SCRIPT_DIR}/../${BUILD_DIR}/bin/cachesim"
	echo "you can debug cachesim by running: "
	echo "gdb -ex r --args PATH_TO_CACHESIM <trace_filepath> <trace_type> <cache_name> <cache_size>"
	echo "or you can provide cachesim arguments when running the debug script: "
	echo "bash scripts/debug.sh <trace_filepath> <trace_type> <cache_name> <cache_size>"
	echo '########################################################'
	echo ''
fi
