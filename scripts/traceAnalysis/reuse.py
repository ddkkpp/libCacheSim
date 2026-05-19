"""
plot reuse time distribution

usage:
1. run traceAnalyzer: `./traceAnalyzer /path/trace trace_format --common`,
this will generate some output, including reuse distribution result, trace.reuse
2. plot reuse distribution using this script:
`python3 reuse.py trace.reuse`

"""

import os
import sys
import re
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from utils.trace_utils import extract_dataname
from utils.plot_utils import FIG_DIR, FIG_TYPE
from utils.data_utils import conv_to_cdf

logger = logging.getLogger("reuse")


def _load_reuse_data(
    datapath: str, ignore_compulsory_miss: bool = True
) -> Tuple[dict, dict]:
    """load reuse distribution plot data from C++ computation

    Args:
        datapath (str): the path of reuse data file

    Returns:
        Tuple[dict, dict]: reuse_rtime_count, reuse_vtime_count

    """

    ifile = open(datapath)
    data_line = ifile.readline()
    desc_line = ifile.readline()
    m = re.match(r"# reuse real time: freq \(time granularity (?P<tg>\d+)\)", desc_line)
    assert m is not None, (
        "the input file might not be reuse data file, desc line "
        + desc_line
        + " data "
        + datapath
    )

    rtime_granularity = int(m.group("tg"))
    log_base = 1.5

    reuse_rtime_count, reuse_vtime_count = {}, {}

    for line in ifile:
        if line[0] == "#" and "virtual time" in line:
            m = re.match(
                r"# reuse virtual time: freq \(log base (?P<lb>\d+\.?\d*)\)", line
            )
            assert m is not None, "the input file might not be "\
                f"reuse data file, desc line {line} data {datapath}"
            log_base = float(m.group("lb"))
            break
        elif not line.strip():
            continue
        else:
            reuse_time, count = [int(i) for i in line.split(":")]
            if reuse_time < -1:
                # it can be -1, which indicates compulsory misses
                print("find negative reuse time " + line)
            if reuse_time == -1 and not ignore_compulsory_miss:
                continue
            reuse_rtime_count[reuse_time * rtime_granularity] = count

    for line in ifile:
        if not line.strip():
            continue
        else:
            reuse_time, count = [int(i) for i in line.split(":")]
            if reuse_time < -1:
                # it can be -1, which indicates compulsory misses
                print("find negative reuse time " + line)
            if reuse_time == -1 and not ignore_compulsory_miss:
                continue
            reuse_vtime_count[log_base**reuse_time] = count

    ifile.close()

    return reuse_rtime_count, reuse_vtime_count


def plot_reuse(
    datapath: str,
    figname_prefix: str = "",
    output_dir: str = FIG_DIR,
    fig_type: str = FIG_TYPE,
) -> None:
    """
    plot reuse time distribution

    Args:
        datapath (str): the path of reuse data file
        figname_prefix (str, optional): the prefix of figname. Defaults to "".

    Returns:
        None: None

    """

    if not figname_prefix:
        figname_prefix = extract_dataname(datapath)

    os.makedirs(output_dir, exist_ok=True)
    label_fontsize = float(plt.rcParams.get("axes.labelsize", 12)) * 1.5

    reuse_rtime_count, reuse_vtime_count = _load_reuse_data(datapath, False)

    x, y = conv_to_cdf(None, data_dict=reuse_rtime_count)
    if x[0] < 0:
        # this is compulsory miss
        x = x[1:]
        y = [y[i] - y[0] for i in range(1, len(y))]
    plt.step([i / 3600 for i in x], y, where="post")
    plt.ylim(0.0, 1.0)
    plt.xlabel("Time (Hour)", fontsize=label_fontsize, fontweight="bold")
    plt.ylabel("Cumulative proportion", fontsize=label_fontsize, fontweight="bold")
    plt.savefig(
        "{}/{}_reuse_rt.{}".format(output_dir, figname_prefix, fig_type),
        bbox_inches="tight",
    )
    plt.xscale("log")
    plt.xticks(
        np.array([60, 300, 3600, 86400, 86400 * 2, 86400 * 4]) / 3600,
        ["1 min", "5 min", "1 hour", "1 day", "", "4 day"],
        rotation=28,
    )
    plt.savefig(
        "{}/{}_reuse_rt_log.{}".format(output_dir, figname_prefix, fig_type),
        bbox_inches="tight",
    )
    plt.clf()

    x, y = conv_to_cdf(None, data_dict=reuse_vtime_count)
    if x[0] < 0:
        x = x[1:]
        y = [y[i] - y[0] for i in range(1, len(y))]
    plt.step([i / 1e6 for i in x], y, where="post")
    plt.ylim(0.0, 1.0)
    plt.xlabel(
        "Re-access distance (million of requests)",
        fontsize=label_fontsize,
        fontweight="bold",
    )
    plt.ylabel("Cumulative proportion", fontsize=label_fontsize, fontweight="bold")
    plt.savefig(
        "{}/{}_reuse_vt.{}".format(output_dir, figname_prefix, fig_type),
        bbox_inches="tight",
    )
    plt.xscale("log")
    plt.savefig(
        "{}/{}_reuse_vt_log.{}".format(output_dir, figname_prefix, fig_type),
        bbox_inches="tight",
    )
    plt.clf()
    logger.info(
        "reuse time plot saved to {}/{}_reuse_rt.{} and {}/{}_reuse_vt.{}".format(
            output_dir, figname_prefix, fig_type, output_dir, figname_prefix, fig_type
        )
    )


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("datapath", type=str, help="data path")
    ap.add_argument(
        "--figname-prefix", type=str, default="", help="the prefix of figname"
    )
    ap.add_argument(
        "--output-dir", type=str, default=FIG_DIR, help="output directory"
    )
    ap.add_argument("--fig-type", type=str, default=FIG_TYPE, help="figure type")
    p = ap.parse_args()

    plot_reuse(p.datapath, p.figname_prefix, p.output_dir, p.fig_type)
