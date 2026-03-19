#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

CSV="tmp/transformq0_mrw_sweep_orig3_cache01_0318/results.csv"
TMP="${CSV}.tmp"

if [ ! -f "$CSV" ]; then
  echo "missing: $CSV" >&2
  exit 1
fi

extract_final() {
  local log_path="$1"
  awk '
    /LOH-.*cache size/ {
      mr=""; bmr=""; mqps="";
      if (match($0, /miss ratio [0-9]+\.[0-9]+/)) mr = substr($0, RSTART + 11, RLENGTH - 11);
      if (match($0, /byte miss ratio [0-9]+\.[0-9]+/)) bmr = substr($0, RSTART + 16, RLENGTH - 16);
      if (match($0, /throughput [0-9]+\.[0-9]+ MQPS/)) mqps = substr($0, RSTART + 11, RLENGTH - 16);
      if (mr != "" && bmr != "" && mqps != "") last = mr "," bmr "," mqps;
    }
    END { if (last != "") print last; }
  ' "$log_path"
}

{
  IFS= read -r header
  echo "$header"
  while IFS=, read -r w t status rc fmr fbmr fmqps logp; do
    if [ "$status" = "ok" ] && { [ "$fmr" = "NA" ] || [ "$fbmr" = "NA" ] || [ "$fmqps" = "NA" ]; }; then
      fin=$(extract_final "$logp" || true)
      if [ -n "$fin" ]; then
        IFS=, read -r nfmr nfbmr nfmqps <<< "$fin"
        fmr="$nfmr"
        fbmr="$nfbmr"
        fmqps="$nfmqps"
      fi
    fi
    echo "$w,$t,$status,$rc,$fmr,$fbmr,$fmqps,$logp"
  done
} < "$CSV" > "$TMP"

mv -f "$TMP" "$CSV"
