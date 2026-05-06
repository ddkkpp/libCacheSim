""" plot popularity Zipf curve

usage:
1. run traceAnalyzer: `./traceAnalyzer /path/trace trace_format --common`,
this will generate some output, including popularity result, trace.popularity
2. plot popularity using this script:
`python3 popularity.py trace.popularity`

"""

import os, sys
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__))+ "/../")
from utils.trace_utils import extract_dataname
from utils.plot_utils import FIG_DIR, FIG_TYPE


logger = logging.getLogger("popularity")


def load_popularity_data(datapath):
    """load popularity plot data from C++ computation"""

    ifile = open(datapath)
    data_line = ifile.readline()
    desc_line = ifile.readline()
    assert "# freq (sorted):cnt" in desc_line, (
        "the input file might not be popularity freq data file " + "data " + datapath
    )

    sorted_freq = []
    freq_cnt = Counter()
    for line in ifile:
        freq, cnt = [int(i) for i in line.strip("\n").split(":")]
        for i in range(cnt):
            sorted_freq.append(freq)
        freq_cnt[freq] += 1

    ifile.close()

    return sorted_freq, freq_cnt


def plot_popularity_Zipf(
    datapath,
    figname_prefix="",
    output_dir=FIG_DIR,
    fig_type=FIG_TYPE,
):
    if not figname_prefix:
        figname_prefix = extract_dataname(datapath)

    os.makedirs(output_dir, exist_ok=True)
    label_fontsize = float(plt.rcParams.get("axes.labelsize", 12)) * 1.5

    sorted_freq, _ = load_popularity_data(datapath)

    plt.plot(
        sorted_freq,
    )
    plt.xlabel("Object rank", fontsize=label_fontsize, fontweight="bold")
    plt.ylabel("Frequency", fontsize=label_fontsize, fontweight="bold")
    plt.xscale("log")
    plt.yscale("log")
    plt.savefig(
        "{}/{}_pop_rank.{}".format(output_dir, figname_prefix, fig_type),
        bbox_inches="tight",
    )
    plt.clf()
    logger.info(
        "save fig to {}/{}_pop_rank.{}".format(output_dir, figname_prefix, fig_type)
    )

    x = np.log(np.arange(1, 1 + len(sorted_freq), dtype=np.float64))
    y = np.log(np.array(sorted_freq, dtype=np.float64))
    slope, intercept = np.polyfit(x, y, 1)
    y_hat = slope * x + intercept
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 0.0 if ss_tot == 0.0 else 1.0 - ss_res / ss_tot

    if sorted_freq[0] < 100:
        s = "{:48} {:12} obj alpha 0, r^2 0 (the most popular object has less than 100 requests)".format(
            figname_prefix,
            len(sorted_freq),
        )
    else:
        s = "{:48} {:12} obj alpha {:.4f}, r^2 {:.4f}".format(
            figname_prefix, len(sorted_freq), -slope, r2
        )

    logger.info(s)

    return s


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "datapath",
        type=str,
        help="data path, should have the format of dataname.popularity",
    )
    ap.add_argument(
        "--figname-prefix", type=str, default="", help="the prefix of figname"
    )
    ap.add_argument(
        "--output-dir", type=str, default=FIG_DIR, help="output directory"
    )
    ap.add_argument("--fig-type", type=str, default=FIG_TYPE, help="figure type")
    p = ap.parse_args()

    plot_popularity_Zipf(p.datapath, p.figname_prefix, p.output_dir, p.fig_type)
