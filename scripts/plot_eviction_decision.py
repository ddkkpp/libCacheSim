#!/usr/bin/env python3
"""Short trace: LFU beats Belady/BeladySize."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

def plot(outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 3.8))

    s1_t = [1, 3, 9]
    s2_t = [2, 4, 10]
    l_t  = [5, 7, 8]
    x_t  = [6]

    ax.plot(s1_t, [3]*len(s1_t), 'o-', color='#3498DB', markersize=11, linewidth=2)
    ax.plot(s2_t, [2]*len(s2_t), 's-', color='#2ECC71', markersize=11, linewidth=2)
    ax.plot(l_t,  [1]*len(l_t),  'D-', color='#F39C12', markersize=11, linewidth=2)
    ax.plot(x_t,  [0.5],         'D', color='#9B59B6', markersize=13)

    ax.axvline(x=6, color='black', linewidth=2, linestyle='--', zorder=2)
    ax.text(5.85, 3.55, 'Eviction Time', fontsize=13, fontweight='bold', ha='right')

    box_style = dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='#888888', alpha=0.95)
    arrow_style = dict(arrowstyle='->', color='#888888', lw=1.5)

    ax.annotate('Belady / BeladySize:\nevict S₂ + S₁ → 4/10 hits',
                xy=(6, 2.5), fontsize=12, color='#E74C3C', fontweight='bold',
                xytext=(6.5, 3.4),
                arrowprops=arrow_style, bbox=box_style)
    ax.annotate('LFU:\nevict L (size=2) → 5/10 hits',
                xy=(6, 1), fontsize=12, color='#E74C3C', fontweight='bold',
                xytext=(6.5, 0.2),
                arrowprops=arrow_style, bbox=box_style)

    ax.set_xlim(0.5, 10.5)
    ax.set_xticks(range(1, 11))
    ax.set_ylim(0, 4.0)
    ax.set_yticks([0.5, 1, 2, 3])
    ax.set_yticklabels(['X (size=2)', 'L (size=2)', 'S₂ (size=1)', 'S₁ (size=1)'],
                        fontsize=13)
    ax.tick_params(axis='both', labelsize=13)
    ax.grid(axis='x', alpha=0.3)

    fig.tight_layout()
    for ext in ['png', 'pdf']:
        path = outdir / f'beladysize_suboptimal_proof.{ext}'
        fig.savefig(path, dpi=180, bbox_inches='tight')
        print(f"Saved: {path}")
    plt.close(fig)

if __name__ == "__main__":
    plot(Path("tmp/20260602-oracle-gap-plots"))
