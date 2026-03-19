#!/usr/bin/env bash
set -euo pipefail
TA=_build_dbg/bin/traceAnalyzer
if [[ ! -x "$TA" ]]; then
  echo "missing executable: $TA" >&2
  exit 1
fi
run_one(){
  name="$1"
  path="$2"
  fmt="$3"
  log="tmp/20260319-traceanalyzer/${name}_traceanalyzer.log"
  rm -f stat traceStat
  "$TA" "$path" "$fmt" --common > "$log" 2>&1
  cp stat "Output/${name}.stat"
  cp traceStat "Output/${name}.traceStat"
}
run_one wiki data/WikiCDN/wiki_2019t.oracleGeneral.zst oracleGeneral
run_one tencent1063 data/TencentCBS/1063.oracleGeneral.zst oracleGeneral
run_one lru10m data/lrutest_10m.csv csv
run_one lfu10m data/lfutest_10m.csv csv
ls -lh Output/meta.stat Output/meta.traceStat Output/wiki.stat Output/wiki.traceStat Output/tencent1063.stat Output/tencent1063.traceStat Output/lru10m.stat Output/lru10m.traceStat Output/lfu10m.stat Output/lfu10m.traceStat > tmp/20260319-traceanalyzer/output_manifest.log
