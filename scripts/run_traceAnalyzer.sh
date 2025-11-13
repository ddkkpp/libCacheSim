#!/bin/bash

function help() {
    echo "Usage: $0 <tracepath> <trace_format> [<trace_format_parameters>]"
}

if [ $# -lt 2 ]; then
    help;
    exit 1;
fi

CURR_DIR=$(cd $(dirname $0); pwd)
tracepath=$1
trace_format=$2
trace_format_parameters=${@:3}

STAT_DIR="analysis"
FIG_DIR="figure"
mkdir -p "${STAT_DIR}" "${FIG_DIR}"

# run analyzer (outputs go to CWD), then move raw outputs into ${STAT_DIR}
./_build/bin/traceAnalyzer ${tracepath} ${trace_format} ${trace_format_parameters} --common

dataname=$(basename ${tracepath})
# move analyzer outputs into stat/
# Move any analyzer outputs that start with the dataname into ${STAT_DIR}.
# Older script only moved a fixed list; that left intermediate files like
# "${dataname}.reuseWindow_w300_rt" in the repo root. Move all matching
# files so intermediate outputs land under the analysis directory.
for f in ${dataname}.*; do
    if [ -f "$f" ]; then
        mv -f "$f" "${STAT_DIR}/"
    fi
done

# plot figures from files in stat/; figures will go to ${FIG_DIR} by default (plot_utils.FIG_DIR)
python3 ${CURR_DIR}/traceAnalysis/access_pattern.py ${STAT_DIR}/${dataname}.accessRtime
python3 ${CURR_DIR}/traceAnalysis/access_pattern.py ${STAT_DIR}/${dataname}.accessVtime
python3 ${CURR_DIR}/traceAnalysis/req_rate.py ${STAT_DIR}/${dataname}.reqRate_w300
python3 ${CURR_DIR}/traceAnalysis/size.py ${STAT_DIR}/${dataname}.size
python3 ${CURR_DIR}/traceAnalysis/reuse.py ${STAT_DIR}/${dataname}.reuse
python3 ${CURR_DIR}/traceAnalysis/popularity.py ${STAT_DIR}/${dataname}.popularity
# python3 ${CURR_DIR}/traceAnalysis/requestAge.py ${dataname}.requestAge
# python3 ${CURR_DIR}/traceAnalysis/size_heatmap.py ${dataname}.sizeWindow_w300
# python3 ${CURR_DIR}/traceAnalysis/futureReuse.py ${dataname}.access

# python3 ${CURR_DIR}/traceAnalysis/popularity_decay.py ${dataname}.popularityDecay_w300_obj
# python3 ${CURR_DIR}/traceAnalysis/reuse_heatmap.py ${dataname}.reuseWindow_w300

# --- post-processing: write comparable metrics to analysis/summary.json ---
# Metrics:
#   - popularity Top-k shares (1/10/100/1%) and Zipf alpha (log-log slope)
#   - (optional) reqRate mean/std/CV over 300s windows [DISABLED by default]
#       NOTE: Many synthetic traces don't use real time; enable only when SUMMARY_INCLUDE_REQRATE=1.
#   - (optional) sliding-window stationarity from scripts/trace_stationarity.py when RUN_STATIONARITY=1

python3 - <<PY
import json, math, os, re, subprocess
from pathlib import Path

STAT_DIR = os.environ.get('STAT_DIR', '${STAT_DIR}')
FIG_DIR = os.environ.get('FIG_DIR', '${FIG_DIR}')
pop_path = Path(f"{STAT_DIR}/${dataname}.popularity")
req_path = Path(f"{STAT_DIR}/${dataname}.reqRate_w300")
summary_path = Path(f"{STAT_DIR}/summary.json")
tracepath = '${tracepath}'
trace_format = '${trace_format}'
run_stationarity = os.environ.get('RUN_STATIONARITY', '0') == '1'
include_reqrate = os.environ.get('SUMMARY_INCLUDE_REQRATE', '0') == '1'
stat_win = os.environ.get('STATIONARITY_WINDOW', '100000')
stat_step = os.environ.get('STATIONARITY_STEP', '100000')
stat_topk = os.environ.get('STATIONARITY_TOPK', '100')
scripts_dir = Path('${CURR_DIR}')

def load_popularity(p: Path):
    if not p.exists():
        return None
    freqs = []
    total_req = 0
    total_obj = 0
    with p.open() as f:
        for line in f:
            if not line.strip() or line.startswith('#'):
                continue
            try:
                freq_s, cnt_s = line.split(':')
                freq = int(freq_s); cnt = int(cnt_s)
            except Exception:
                continue
            freqs.extend([freq] * cnt)
            total_req += freq * cnt
            total_obj += cnt
    if not freqs:
        return None
    freqs.sort(reverse=True)
    def share(k):
        k = min(k, len(freqs))
        return float(sum(freqs[:k]) / max(1, total_req))
    top1 = share(1)
    top10 = share(10)
    top100 = share(100)
    top1pct = share(max(1, total_obj // 100))
    # Zipf alpha via linear fit on mid ranks
    import numpy as np
    ranks = np.arange(1, len(freqs) + 1)
    lo = 10
    hi = max(lo + 50, len(freqs) // 2)
    try:
        log_r = np.log(ranks[lo:hi])
        log_f = np.log(np.array(freqs[lo:hi]))
        a, b = np.polyfit(log_r, log_f, 1)
        alpha = float(-a)
    except Exception:
        alpha = float('nan')
    return dict(
        topk=dict(top1=top1, top10=top10, top100=top100, top1pct=top1pct),
        zipf_alpha=alpha,
        total_req=int(total_req), total_obj=int(total_obj),
    )

def load_req_rate(p: Path):
    if not p.exists():
        return None
    vals = []
    with p.open() as f:
        mode = None
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                if 'req rate' in line:
                    mode = 'req'
                else:
                    mode = None
                continue
            if mode == 'req':
                # comma separated numbers possibly spanning multiple lines
                for tok in line.split(','):
                    tok = tok.strip()
                    if not tok:
                        continue
                    try:
                        vals.append(float(tok))
                    except Exception:
                        pass
            # stop at next section
            if mode == 'req' and line.startswith('#'):
                break
    if not vals:
        return None
    import statistics as st
    mean = float(st.mean(vals))
    std = float(st.pstdev(vals))
    cv = float(std / mean) if mean != 0 else float('inf')
    return dict(mean=mean, std=std, cv=cv, n=len(vals))

def run_stationarity_diag():
    if not run_stationarity:
        return None
    # Only run on CSV traces by default to avoid parsing other formats.
    # Allow forcing stationarity via FORCE_STATIONARITY=1 environment variable.
    force_stationarity = os.environ.get('FORCE_STATIONARITY', '0') == '1'
    if not (tracepath.endswith('.csv') or trace_format.lower() == 'csv' or force_stationarity):
        return None
    tool = scripts_dir.parent / 'scripts' / 'trace_stationarity.py'
    if not tool.exists():
        return None
    try:
        # If trace is not CSV but user forced stationarity, try to convert using tracePrint
        use_tracepath = tracepath
        temp_csv = None
        if not (tracepath.endswith('.csv') or trace_format.lower() == 'csv') and os.environ.get('FORCE_STATIONARITY','0') == '1':
            traceprint = scripts_dir.parent / '_build' / 'bin' / 'tracePrint'
            # fallback to _build_dbg if not present
            if not traceprint.exists():
                traceprint = scripts_dir.parent / '_build_dbg' / 'bin' / 'tracePrint'
            if traceprint.exists():
                temp_csv = Path(f"{STAT_DIR}/${dataname}.stationarity.csv")
                try:
                    with temp_csv.open('w') as outf:
                        subprocess.run([str(traceprint), tracepath, trace_format, '--field-delimiter', ',', '--num-req', str(-1)], stdout=outf, check=True)
                    use_tracepath = str(temp_csv)
                except Exception:
                    # conversion failed, fall back to original tracepath (stationarity will likely skip)
                    use_tracepath = tracepath
            else:
                # tracePrint not available
                use_tracepath = tracepath

        cp = subprocess.run(
            ['python3', str(tool), '--trace', use_tracepath, '--window', str(int(stat_win)), '--step', str(int(stat_step)), '--topk', str(int(stat_topk))],
            capture_output=True, text=True, check=True
        )
        out = cp.stdout.splitlines()
        res = {}
        for ln in out:
            m = re.match(r"(\w+):\s+mean=([\d\.eE+-]+),\s*std=([\d\.eE+-]+)", ln)
            if m:
                key, mean, std = m.group(1), float(m.group(2)), float(m.group(3))
                res[key] = dict(mean=mean, std=std)
        if res:
            return res
    except Exception:
        return None
    return None

pop = load_popularity(pop_path)
req = load_req_rate(req_path) if include_reqrate else None
stationarity = run_stationarity_diag()

entry = dict()
if pop: entry.update(pop)
if req: entry['req_rate'] = req
if stationarity: entry['stationarity'] = stationarity

# Derive stationarity labels (identity/distribution/size) when stationarity stats present
if stationarity:
    import os
    # thresholds (can be tuned via env vars)
    j_mean = stationarity.get('jaccard_topk', {}).get('mean', float('nan'))
    j_std = stationarity.get('jaccard_topk', {}).get('std', float('nan'))
    ts_std = stationarity.get('topk_share', {}).get('std', float('nan'))
    za_std = stationarity.get('zipf_alpha', {}).get('std', float('nan'))
    p50m, p50s = stationarity.get('size_p50', {}).get('mean', float('nan')), stationarity.get('size_p50', {}).get('std', float('nan'))
    p90m, p90s = stationarity.get('size_p90', {}).get('mean', float('nan')), stationarity.get('size_p90', {}).get('std', float('nan'))
    p99m, p99s = stationarity.get('size_p99', {}).get('mean', float('nan')), stationarity.get('size_p99', {}).get('std', float('nan'))

    def _get(name, default):
        try:
            return float(os.environ.get(name, default))
        except Exception:
            return float(default)

    JACCARD_STABLE = _get('JACCARD_STABLE', 0.85)
    JACCARD_UNSTABLE = _get('JACCARD_UNSTABLE', 0.5)
    TOPK_SHARE_STD_STABLE = _get('TOPK_SHARE_STD_STABLE', 0.01)
    TOPK_SHARE_STD_UNSTABLE = _get('TOPK_SHARE_STD_UNSTABLE', 0.05)
    ZIPF_STD_STABLE = _get('ZIPF_STD_STABLE', 0.02)
    ZIPF_STD_UNSTABLE = _get('ZIPF_STD_UNSTABLE', 0.1)
    SIZE_REL_STD_STABLE = _get('SIZE_REL_STD_STABLE', 0.05)
    SIZE_REL_STD_UNSTABLE = _get('SIZE_REL_STD_UNSTABLE', 0.2)

    # identity label from Jaccard@K statistics
    if not math.isnan(j_mean):
        if j_mean >= JACCARD_STABLE:
            identity_label = 'stable'
        elif j_mean < JACCARD_UNSTABLE:
            identity_label = 'unstable'
        else:
            identity_label = 'weak'
    else:
        identity_label = 'unknown'

    # distribution label from topk_share std and zipf_alpha std
    dist_bad = (not math.isnan(ts_std) and ts_std > TOPK_SHARE_STD_UNSTABLE) or (not math.isnan(za_std) and za_std > ZIPF_STD_UNSTABLE)
    dist_good = (not math.isnan(ts_std) and ts_std <= TOPK_SHARE_STD_STABLE) and (not math.isnan(za_std) and za_std <= ZIPF_STD_STABLE)
    if dist_good:
        distribution_label = 'stable'
    elif dist_bad:
        distribution_label = 'unstable'
    else:
        distribution_label = 'weak'

    # size label from relative std of quantiles
    def rel(std, mean):
        if math.isnan(std) or math.isnan(mean) or mean == 0:
            return float('nan')
        return float(std / mean)
    rels = [rel(p50s, p50m), rel(p90s, p90m), rel(p99s, p99m)]
    size_bad = any((not math.isnan(r) and r > SIZE_REL_STD_UNSTABLE) for r in rels)
    size_good = all((not math.isnan(r) and r <= SIZE_REL_STD_STABLE) for r in rels)
    if size_good:
        size_label = 'stable'
    elif size_bad:
        size_label = 'unstable'
    else:
        size_label = 'weak'

    entry['stationarity_labels'] = {
        'identity': identity_label,
        'distribution': distribution_label,
        'size': size_label,
    }

name = '${dataname}'
data = {}
if summary_path.exists():
    try:
        data = json.loads(summary_path.read_text())
    except Exception:
        data = {}
data[name] = entry
summary_path.write_text(json.dumps(data, indent=2, sort_keys=True))
print(f"[summary] wrote {summary_path} entry={name}")
PY
