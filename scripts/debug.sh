#!/bin/bash
set -euo pipefail

SOURCE=$(readlink -f "${BASH_SOURCE[0]}")
SCRIPT_DIR=$(dirname "${SOURCE}")
CURR_DIR=$(pwd)

usage() {
	echo "Usage: $0 [options] [-- program_args]"
	echo "Options:"
	echo "  -h, --help    Show this help message"
	echo "  -c, --clean   Clean the build directory"
	echo "  --            Separator between script options and program arguments"
	echo ""
	echo "Example:"
	echo "  $0 -c -- ${SCRIPT_DIR}/../data/cloudPhysicsIO.oracleGeneral.bin oracleGeneral LRU,S3-FIFO 200M,1GB"
	echo "  note that the trace filepath is relative to current directory"
	exit 1
}

# Parse command line arguments
CLEAN=0
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

# Clean build directory if requested
if [[ ${CLEAN} -eq 1 ]]; then
	echo "Cleaning build directory..."
	rm -rf _build_dbg || true 2>/dev/null
fi

# Create and enter build directory
mkdir -p _build_dbg
cd _build_dbg

# Configure and build with warning flags
echo "Configuring and building project with strict warnings..."
## Propagate LOH state-dimension to compiler as a macro (default 26 -> no cache features)
# Priority: explicit LOH_INCLUDE_CACHE_FEATURES > LOH_STATE_DIM mapping > default
LOH_FEATURES_DEFINE=""
if [[ -n "${LOH_INCLUDE_CACHE_FEATURES:-}" ]]; then
	# Use caller-provided 0/1 directly
	VAL="${LOH_INCLUDE_CACHE_FEATURES}"
	if [[ "${VAL}" != "0" && "${VAL}" != "1" ]]; then
		VAL=1
	fi
	LOH_FEATURES_DEFINE="-DLOH_INCLUDE_CACHE_FEATURES=${VAL}"
elif [[ -n "${LOH_STATE_DIM:-}" ]]; then
	# Map 26 -> 0, 38 -> 1 (others default to 1 for safety)
	if [[ "${LOH_STATE_DIM}" == "26" ]]; then
		LOH_FEATURES_DEFINE="-DLOH_INCLUDE_CACHE_FEATURES=0"
	elif [[ "${LOH_STATE_DIM}" == "38" ]]; then
		LOH_FEATURES_DEFINE="-DLOH_INCLUDE_CACHE_FEATURES=1"
	else
		LOH_FEATURES_DEFINE="-DLOH_INCLUDE_CACHE_FEATURES=1"
	fi
else
	# Default: include cache features (38)
	LOH_FEATURES_DEFINE="-DLOH_INCLUDE_CACHE_FEATURES=1"
fi

# Compose flags including the macro define
# Propagate optional candidate features switch (default OFF)
LOH_CAND_DEFINE=""
if [[ -n "${LOH_INCLUDE_CANDIDATE_FEATURES:-}" ]]; then
	VAL="${LOH_INCLUDE_CANDIDATE_FEATURES}"
	if [[ "${VAL}" != "0" && "${VAL}" != "1" ]]; then
		VAL=0
	fi
	LOH_CAND_DEFINE="-DLOH_INCLUDE_CANDIDATE_FEATURES=${VAL}"
else
	LOH_CAND_DEFINE="-DLOH_INCLUDE_CANDIDATE_FEATURES=0"
fi

C_FLAGS="-Wall -Wextra -Werror -Wno-unused-variable -Wno-unused-function -Wno-unused-parameter -Wno-unused-but-set-variable -Wpedantic -Wformat=2 -Wformat-security -Wshadow -Wwrite-strings -Wstrict-prototypes -Wold-style-definition -Wredundant-decls -Wnested-externs -Wmissing-include-dirs ${LOH_FEATURES_DEFINE} ${LOH_CAND_DEFINE}"
CXX_FLAGS="-Wall -Wextra -Werror -Wno-deprecated-copy -Wno-unused-variable -Wno-unused-function -Wno-unused-parameter -Wno-unused-but-set-variable -Wno-pedantic -Wformat=2 -Wformat-security -Wshadow -Wwrite-strings -Wmissing-include-dirs ${LOH_FEATURES_DEFINE} ${LOH_CAND_DEFINE}"

cmake -G Ninja -DCMAKE_BUILD_TYPE=Debug \
	-DCMAKE_C_FLAGS="${C_FLAGS}" \
	-DCMAKE_CXX_FLAGS="${CXX_FLAGS}" \
	-DENABLE_GLCACHE=ON -DENABLE_LRB=ON -DENABLE_3L_CACHE=ON \
	..

ninja

# Return to script directory
# cd ${DIR}
cd "${CURR_DIR}"

if [[ ${#PROGRAM_ARGS[@]} -ne 0 ]]; then
	# Run the program with gdb and pass arguments
	echo "Starting debug session with arguments..."
	gdb -ex "set print thread-events off" -ex r --args "${SCRIPT_DIR}"/../_build_dbg/bin/cachesim "${PROGRAM_ARGS[@]}"
else
	echo ''
	echo '########################################################'
	echo "debug build is at ${SCRIPT_DIR}/../_build_dbg/bin/cachesim"
	echo "you can debug cachesim by running: "
	echo "gdb -ex r --args PATH_TO_CACHESIM <trace_filepath> <trace_type> <cache_name> <cache_size>"
	echo "or you can provide cachesim arguments when running the debug script: "
	echo "bash scripts/debug.sh <trace_filepath> <trace_type> <cache_name> <cache_size>"
	echo '########################################################'
	echo ''
fi
