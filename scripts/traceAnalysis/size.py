"""
plot size distribution

usage:
1. run traceAnalyzer: `./traceAnalyzer /path/trace trace_format --common`,
this will generate some output, including size distribution result, trace.size
2. plot size distribution using this script:
`python3 size.py trace.size`

"""

import os, sys
import re
import logging
import matplotlib.pyplot as plt

from typing import Tuple
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")
from utils.trace_utils import extract_dataname
from utils.plot_utils import FIG_DIR, FIG_TYPE
from utils.data_utils import conv_to_cdf

logger = logging.getLogger("size")


def _load_size_data(datapath: str) -> Tuple[dict, dict]:
    """load size distribution plot data from C++ computation

    Args:
        datapath (str): the path of size data file

    Returns:
        Tuple[dict, dict]: obj_size_req_cnt, obj_size_obj_cnt

    """

    ifile = open(datapath)
    data_line = ifile.readline()
    desc_line = ifile.readline()
    m = re.match(r"# object_size: req_cnt", desc_line)
    assert (
        "# object_size: req_cnt" in desc_line or "# object_size: freq" in desc_line
    ), (
        "the input file might not be size data file, desc line "
        + desc_line
        + " data "
        + datapath
    )

    obj_size_req_cnt, obj_size_obj_cnt = {}, {}
    for line in ifile:
        if line[0] == "#" and "object_size: obj_cnt" in line:
            break
        else:
            size, count = [int(i) for i in line.split(":")]
            obj_size_req_cnt[size] = count

    for line in ifile:
        size, count = [int(i) for i in line.split(":")]
        obj_size_obj_cnt[size] = count

    ifile.close()

    return obj_size_req_cnt, obj_size_obj_cnt


def plot_size_distribution(
    datapath: str,
    figname_prefix: str = "",
    output_dir: str = FIG_DIR,
    fig_type: str = FIG_TYPE,
):
    """
    plot size distribution

    Args:
        datapath (str): the path of size data file
        figname_prefix (str, optional): the prefix of figname. Defaults to "".

    """

    if not figname_prefix:
        figname_prefix = extract_dataname(datapath)

    os.makedirs(output_dir, exist_ok=True)
    label_fontsize = float(plt.rcParams.get("axes.labelsize", 12)) * 1.5

    obj_size_req_cnt, obj_size_obj_cnt = _load_size_data(datapath)

    x, y = conv_to_cdf(None, data_dict=obj_size_req_cnt)
    plt.plot(x, y, label="Request")

    plt.legend()
    plt.xlabel("Object size (Byte)", fontsize=label_fontsize, fontweight="bold")
    plt.ylabel("Cumulative proportion", fontsize=label_fontsize, fontweight="bold")
    plt.savefig(
        "{}/{}_size.{}".format(output_dir, figname_prefix, fig_type), bbox_inches="tight"
    )

    plt.xscale("log")
    plt.savefig(
        "{}/{}_size_log.{}".format(output_dir, figname_prefix, fig_type),
        bbox_inches="tight",
    )
    plt.clf()

    logger.info(
        "plot saved to {}/{}_size.{} {}/{}_size.{}".format(
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

    plot_size_distribution(p.datapath, p.figname_prefix, p.output_dir, p.fig_type)
