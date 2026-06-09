# Feature Ablation Analysis

## Config encoding

| Config | Label | freq_rec | freq_size | rec_size |
|:---|:---|:---:|:---:|:---:|
| f000 | base | ✗ | ✗ | ✗ |
| f001 | +rs | ✗ | ✗ | ✓ |
| f010 | +fs | ✗ | ✓ | ✗ |
| f011 | +fs+rs | ✗ | ✓ | ✓ |
| f100 | +fr | ✓ | ✗ | ✗ |
| f101 | +fr+rs | ✓ | ✗ | ✓ |
| f110 | +fr+fs | ✓ | ✓ | ✗ |
| f111 | all | ✓ | ✓ | ✓ |

## Per-group analysis

### cloudphysics (106 traces)

**MR wins** (times each config has lowest MR):

| Config | Label | Wins | Win% |
|:---|:---|---:|---:|
| f000 | base | 1 | 0.9% |
| f001 | +rs | 6 | 5.7% |
| f010 | +fs | 20 | 18.9% |
| f011 | +fs+rs | 42 | 39.6% |
| f100 | +fr | 9 | 8.5% |
| f101 | +fr+rs | 0 | 0.0% |
| f110 | +fr+fs | 10 | 9.4% |
| f111 | all | 18 | 17.0% |

**MR change vs base** (negative = improvement):

| Config | Label | Mean Δ% | Median Δ% | P10 | P90 |
|:---|:---|---:|---:|---:|---:|
| f001 | +rs | -4.63% | -2.82% | -12.99% | 1.53% |
| f010 | +fs | 17.74% | -5.45% | -16.49% | 3.49% |
| f011 | +fs+rs | 15.94% | -5.68% | -19.04% | 0.84% |
| f100 | +fr | 0.49% | 0.01% | -4.15% | 4.82% |
| f101 | +fr+rs | -4.33% | -2.68% | -10.99% | 0.20% |
| f110 | +fr+fs | 19.55% | -3.10% | -12.69% | 8.95% |
| f111 | all | 17.13% | -4.68% | -15.54% | 3.13% |

### metaKV (5 traces)

**MR wins** (times each config has lowest MR):

| Config | Label | Wins | Win% |
|:---|:---|---:|---:|
| f000 | base | 0 | 0.0% |
| f001 | +rs | 0 | 0.0% |
| f010 | +fs | 5 | 100.0% |
| f011 | +fs+rs | 0 | 0.0% |
| f100 | +fr | 0 | 0.0% |
| f101 | +fr+rs | 0 | 0.0% |
| f110 | +fr+fs | 0 | 0.0% |
| f111 | all | 0 | 0.0% |

**MR change vs base** (negative = improvement):

| Config | Label | Mean Δ% | Median Δ% | P10 | P90 |
|:---|:---|---:|---:|---:|---:|
| f001 | +rs | -2.40% | -2.16% | -3.68% | -1.35% |
| f010 | +fs | -4.47% | -4.15% | -5.46% | -3.77% |
| f011 | +fs+rs | -4.07% | -3.77% | -5.22% | -3.24% |
| f100 | +fr | -0.06% | -0.09% | -0.31% | 0.21% |
| f101 | +fr+rs | -2.23% | -2.30% | -3.57% | -0.98% |
| f110 | +fr+fs | -3.42% | -3.14% | -4.39% | -2.64% |
| f111 | all | -3.14% | -2.87% | -4.12% | -2.41% |

### metaCDN (3 traces)

**MR wins** (times each config has lowest MR):

| Config | Label | Wins | Win% |
|:---|:---|---:|---:|
| f000 | base | 0 | 0.0% |
| f001 | +rs | 0 | 0.0% |
| f010 | +fs | 0 | 0.0% |
| f011 | +fs+rs | 2 | 66.7% |
| f100 | +fr | 0 | 0.0% |
| f101 | +fr+rs | 0 | 0.0% |
| f110 | +fr+fs | 0 | 0.0% |
| f111 | all | 1 | 33.3% |

**MR change vs base** (negative = improvement):

| Config | Label | Mean Δ% | Median Δ% | P10 | P90 |
|:---|:---|---:|---:|---:|---:|
| f001 | +rs | -5.71% | -5.75% | -6.12% | -5.29% |
| f010 | +fs | -2.71% | -2.75% | -3.90% | -1.51% |
| f011 | +fs+rs | -7.21% | -6.68% | -8.92% | -5.71% |
| f100 | +fr | 1.90% | 1.49% | 0.75% | 3.22% |
| f101 | +fr+rs | -4.72% | -4.01% | -6.21% | -3.51% |
| f110 | +fr+fs | -0.85% | -1.30% | -1.37% | -0.14% |
| f111 | all | -7.51% | -6.25% | -10.16% | -5.36% |

### wiki (3 traces)

**MR wins** (times each config has lowest MR):

| Config | Label | Wins | Win% |
|:---|:---|---:|---:|
| f000 | base | 0 | 0.0% |
| f001 | +rs | 0 | 0.0% |
| f010 | +fs | 1 | 33.3% |
| f011 | +fs+rs | 1 | 33.3% |
| f100 | +fr | 0 | 0.0% |
| f101 | +fr+rs | 1 | 33.3% |
| f110 | +fr+fs | 0 | 0.0% |
| f111 | all | 0 | 0.0% |

**MR change vs base** (negative = improvement):

| Config | Label | Mean Δ% | Median Δ% | P10 | P90 |
|:---|:---|---:|---:|---:|---:|
| f001 | +rs | -5.01% | -1.56% | -13.45% | 2.04% |
| f010 | +fs | -3.96% | -2.69% | -8.44% | 0.01% |
| f011 | +fs+rs | -8.63% | -3.59% | -16.62% | -2.64% |
| f100 | +fr | -2.79% | -1.46% | -10.33% | 4.21% |
| f101 | +fr+rs | -7.74% | -1.09% | -17.16% | -0.97% |
| f110 | +fr+fs | -2.02% | -1.38% | -9.31% | 5.01% |
| f111 | all | -7.87% | -2.64% | -16.58% | -1.25% |

### alibabaBlock_1K (11 traces)

**MR wins** (times each config has lowest MR):

| Config | Label | Wins | Win% |
|:---|:---|---:|---:|
| f000 | base | 9 | 81.8% |
| f001 | +rs | 8 | 72.7% |
| f010 | +fs | 10 | 90.9% |
| f011 | +fs+rs | 8 | 72.7% |
| f100 | +fr | 9 | 81.8% |
| f101 | +fr+rs | 9 | 81.8% |
| f110 | +fr+fs | 8 | 72.7% |
| f111 | all | 8 | 72.7% |

**MR change vs base** (negative = improvement):

| Config | Label | Mean Δ% | Median Δ% | P10 | P90 |
|:---|:---|---:|---:|---:|---:|
| f001 | +rs | 0.23% | 0.00% | 0.00% | 0.00% |
| f010 | +fs | 0.05% | 0.00% | 0.00% | 0.00% |
| f011 | +fs+rs | 0.09% | 0.00% | 0.00% | 0.28% |
| f100 | +fr | 1.30% | 0.00% | 0.00% | 1.14% |
| f101 | +fr+rs | 0.91% | 0.00% | 0.00% | 0.49% |
| f110 | +fr+fs | 0.24% | 0.00% | 0.00% | 0.62% |
| f111 | all | 0.83% | 0.00% | 0.00% | 0.62% |

### alibabaBlock_10K (41 traces)

**MR wins** (times each config has lowest MR):

| Config | Label | Wins | Win% |
|:---|:---|---:|---:|
| f000 | base | 25 | 61.0% |
| f001 | +rs | 30 | 73.2% |
| f010 | +fs | 27 | 65.9% |
| f011 | +fs+rs | 27 | 65.9% |
| f100 | +fr | 5 | 12.2% |
| f101 | +fr+rs | 5 | 12.2% |
| f110 | +fr+fs | 11 | 26.8% |
| f111 | all | 13 | 31.7% |

**MR change vs base** (negative = improvement):

| Config | Label | Mean Δ% | Median Δ% | P10 | P90 |
|:---|:---|---:|---:|---:|---:|
| f001 | +rs | -0.09% | 0.00% | -0.36% | 0.01% |
| f010 | +fs | 0.58% | 0.00% | -0.01% | 3.43% |
| f011 | +fs+rs | 0.61% | 0.00% | -0.01% | 3.47% |
| f100 | +fr | 1.03% | 0.04% | 0.00% | 3.70% |
| f101 | +fr+rs | 0.80% | 0.03% | 0.00% | 2.75% |
| f110 | +fr+fs | 0.70% | 0.01% | 0.00% | 3.39% |
| f111 | all | 0.70% | 0.01% | 0.00% | 3.56% |

### alibabaBlock_100K (345 traces)

**MR wins** (times each config has lowest MR):

| Config | Label | Wins | Win% |
|:---|:---|---:|---:|
| f000 | base | 44 | 12.8% |
| f001 | +rs | 100 | 29.0% |
| f010 | +fs | 77 | 22.3% |
| f011 | +fs+rs | 51 | 14.8% |
| f100 | +fr | 16 | 4.6% |
| f101 | +fr+rs | 38 | 11.0% |
| f110 | +fr+fs | 22 | 6.4% |
| f111 | all | 23 | 6.7% |

**MR change vs base** (negative = improvement):

| Config | Label | Mean Δ% | Median Δ% | P10 | P90 |
|:---|:---|---:|---:|---:|---:|
| f001 | +rs | -2.55% | -0.35% | -11.41% | 1.15% |
| f010 | +fs | 1.40% | -0.12% | -9.98% | 12.61% |
| f011 | +fs+rs | 1.38% | -0.14% | -9.63% | 12.43% |
| f100 | +fr | 1.04% | 0.29% | -5.37% | 7.43% |
| f101 | +fr+rs | -1.71% | -0.03% | -7.97% | 2.30% |
| f110 | +fr+fs | 1.96% | 0.08% | -9.73% | 12.78% |
| f111 | all | 1.68% | 0.00% | -9.24% | 12.64% |

### alibabaBlock_1M (366 traces)

**MR wins** (times each config has lowest MR):

| Config | Label | Wins | Win% |
|:---|:---|---:|---:|
| f000 | base | 75 | 20.5% |
| f001 | +rs | 100 | 27.3% |
| f010 | +fs | 38 | 10.4% |
| f011 | +fs+rs | 42 | 11.5% |
| f100 | +fr | 32 | 8.7% |
| f101 | +fr+rs | 48 | 13.1% |
| f110 | +fr+fs | 16 | 4.4% |
| f111 | all | 16 | 4.4% |

**MR change vs base** (negative = improvement):

| Config | Label | Mean Δ% | Median Δ% | P10 | P90 |
|:---|:---|---:|---:|---:|---:|
| f001 | +rs | -3.73% | -0.95% | -23.80% | 8.34% |
| f010 | +fs | 25.45% | 4.01% | -11.69% | 75.42% |
| f011 | +fs+rs | 24.06% | 3.47% | -11.32% | 75.39% |
| f100 | +fr | 5.77% | 1.38% | -15.16% | 27.76% |
| f101 | +fr+rs | -1.20% | -0.29% | -18.99% | 14.45% |
| f110 | +fr+fs | 20.07% | 3.34% | -11.67% | 70.45% |
| f111 | all | 19.60% | 2.92% | -11.28% | 70.83% |

### alibabaBlock_new (237 traces)

**MR wins** (times each config has lowest MR):

| Config | Label | Wins | Win% |
|:---|:---|---:|---:|
| f000 | base | 86 | 36.3% |
| f001 | +rs | 23 | 9.7% |
| f010 | +fs | 31 | 13.1% |
| f011 | +fs+rs | 27 | 11.4% |
| f100 | +fr | 26 | 11.0% |
| f101 | +fr+rs | 19 | 8.0% |
| f110 | +fr+fs | 14 | 5.9% |
| f111 | all | 15 | 6.3% |

**MR change vs base** (negative = improvement):

| Config | Label | Mean Δ% | Median Δ% | P10 | P90 |
|:---|:---|---:|---:|---:|---:|
| f001 | +rs | 0.72% | 0.33% | -3.10% | 5.99% |
| f010 | +fs | 66.89% | 1.19% | -2.95% | 224.29% |
| f011 | +fs+rs | 66.59% | 1.08% | -2.15% | 223.20% |
| f100 | +fr | 2.61% | 0.95% | -2.69% | 9.03% |
| f101 | +fr+rs | 1.53% | 0.28% | -2.74% | 9.05% |
| f110 | +fr+fs | 44.01% | 2.00% | -2.64% | 136.90% |
| f111 | all | 42.31% | 0.93% | -2.32% | 137.04% |

---

## Overall summary (1117 traces)

### MR wins (overall)

| Config | Label | Wins | Win% |
|:---|:---|---:|---:|
| f001 | +rs | 267 | 23.9% |
| f000 | base | 240 | 21.5% |
| f010 | +fs | 209 | 18.7% |
| f011 | +fs+rs | 200 | 17.9% |
| f101 | +fr+rs | 120 | 10.7% |
| f100 | +fr | 97 | 8.7% |
| f111 | all | 94 | 8.4% |
| f110 | +fr+fs | 81 | 7.3% |

### BMR wins (overall)

| Config | Label | Wins | Win% |
|:---|:---|---:|---:|
| f100 | +fr | 246 | 22.0% |
| f001 | +rs | 189 | 16.9% |
| f101 | +fr+rs | 179 | 16.0% |
| f000 | base | 170 | 15.2% |
| f010 | +fs | 164 | 14.7% |
| f110 | +fr+fs | 144 | 12.9% |
| f011 | +fs+rs | 124 | 11.1% |
| f111 | all | 94 | 8.4% |

### MR change vs base (overall, negative = improvement)

| Config | Label | Mean Δ% | Median Δ% | P10 | P90 | Improve% |
|:---|:---|---:|---:|---:|---:|---:|
| f001 | +rs | -2.34% | -0.22% | -12.82% | 5.10% | 56.9% |
| f101 | +fr+rs | -1.01% | -0.04% | -10.53% | 7.42% | 52.1% |
| f100 | +fr | 2.86% | 0.40% | -6.04% | 14.09% | 37.8% |
| f111 | all | 17.52% | 0.03% | -10.05% | 64.24% | 46.2% |
| f110 | +fr+fs | 18.38% | 0.32% | -9.16% | 63.10% | 40.9% |
| f011 | +fs+rs | 23.92% | 0.00% | -10.12% | 90.44% | 49.6% |
| f010 | +fs | 24.63% | 0.00% | -9.91% | 90.14% | 49.0% |

### BMR change vs base (overall)

| Config | Label | Mean Δ% | Median Δ% | Improve% |
|:---|:---|---:|---:|---:|
| f101 | +fr+rs | -2.66% | -0.29% | 59.4% |
| f100 | +fr | -1.57% | -0.21% | 56.2% |
| f001 | +rs | 0.23% | 0.00% | 47.3% |
| f111 | all | 14.50% | 0.00% | 48.6% |
| f110 | +fr+fs | 14.51% | 0.00% | 48.1% |
| f011 | +fs+rs | 19.58% | 0.05% | 43.0% |
| f010 | +fs | 19.80% | 0.00% | 47.0% |

## Anomalies: traces where a config worsens MR by >20%

| Trace | Group | Config | Base MR | Config MR | Δ% |
|:---|:---|:---|---:|---:|---:|
| alibabaBlock_101_1M | alibabaBlock_1M | f010 (+fs) | 0.1115 | 0.1464 | +31.3% |
| alibabaBlock_101_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1115 | 0.1467 | +31.6% |
| alibabaBlock_101_1M | alibabaBlock_1M | f100 (+fr) | 0.1115 | 0.2299 | +106.2% |
| alibabaBlock_101_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.1115 | 0.1428 | +28.1% |
| alibabaBlock_101_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1115 | 0.1408 | +26.3% |
| alibabaBlock_101_1M | alibabaBlock_1M | f111 (all) | 0.1115 | 0.1418 | +27.2% |
| alibabaBlock_104_1M | alibabaBlock_1M | f010 (+fs) | 0.2992 | 0.3657 | +22.2% |
| alibabaBlock_104_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2992 | 0.3658 | +22.2% |
| alibabaBlock_104_1M | alibabaBlock_1M | f100 (+fr) | 0.2992 | 0.3659 | +22.3% |
| alibabaBlock_10_new | alibabaBlock_new | f010 (+fs) | 0.0438 | 0.1092 | +149.4% |
| alibabaBlock_10_new | alibabaBlock_new | f011 (+fs+rs) | 0.0438 | 0.0969 | +121.4% |
| alibabaBlock_10_new | alibabaBlock_new | f100 (+fr) | 0.0438 | 0.0570 | +30.2% |
| alibabaBlock_10_new | alibabaBlock_new | f110 (+fr+fs) | 0.0438 | 0.0812 | +85.4% |
| alibabaBlock_10_new | alibabaBlock_new | f111 (all) | 0.0438 | 0.0762 | +74.2% |
| alibabaBlock_112_new | alibabaBlock_new | f010 (+fs) | 0.1596 | 0.2468 | +54.7% |
| alibabaBlock_112_new | alibabaBlock_new | f011 (+fs+rs) | 0.1596 | 0.2471 | +54.9% |
| alibabaBlock_112_new | alibabaBlock_new | f110 (+fr+fs) | 0.1596 | 0.2034 | +27.4% |
| alibabaBlock_112_new | alibabaBlock_new | f111 (all) | 0.1596 | 0.2302 | +44.3% |
| alibabaBlock_113_new | alibabaBlock_new | f010 (+fs) | 0.1014 | 0.2908 | +186.7% |
| alibabaBlock_113_new | alibabaBlock_new | f011 (+fs+rs) | 0.1014 | 0.2912 | +187.1% |
| alibabaBlock_113_new | alibabaBlock_new | f110 (+fr+fs) | 0.1014 | 0.1592 | +56.9% |
| alibabaBlock_113_new | alibabaBlock_new | f111 (all) | 0.1014 | 0.1607 | +58.4% |
| alibabaBlock_115_new | alibabaBlock_new | f010 (+fs) | 0.0889 | 0.2724 | +206.3% |
| alibabaBlock_115_new | alibabaBlock_new | f011 (+fs+rs) | 0.0889 | 0.2704 | +204.1% |
| alibabaBlock_115_new | alibabaBlock_new | f110 (+fr+fs) | 0.0889 | 0.1436 | +61.5% |
| alibabaBlock_115_new | alibabaBlock_new | f111 (all) | 0.0889 | 0.1428 | +60.6% |
| alibabaBlock_118_1M | alibabaBlock_1M | f100 (+fr) | 0.1029 | 0.1253 | +21.8% |
| alibabaBlock_120_1M | alibabaBlock_1M | f100 (+fr) | 0.1142 | 0.1526 | +33.6% |
| alibabaBlock_121_new | alibabaBlock_new | f010 (+fs) | 0.0237 | 0.1956 | +725.1% |
| alibabaBlock_121_new | alibabaBlock_new | f011 (+fs+rs) | 0.0237 | 0.1955 | +725.0% |
| alibabaBlock_121_new | alibabaBlock_new | f110 (+fr+fs) | 0.0237 | 0.1931 | +714.6% |
| alibabaBlock_121_new | alibabaBlock_new | f111 (all) | 0.0237 | 0.1923 | +711.5% |
| alibabaBlock_124_new | alibabaBlock_new | f010 (+fs) | 0.0522 | 0.0707 | +35.7% |
| alibabaBlock_124_new | alibabaBlock_new | f011 (+fs+rs) | 0.0522 | 0.0699 | +34.0% |
| alibabaBlock_124_new | alibabaBlock_new | f110 (+fr+fs) | 0.0522 | 0.0654 | +25.4% |
| alibabaBlock_125_1M | alibabaBlock_1M | f010 (+fs) | 0.0971 | 0.1276 | +31.4% |
| alibabaBlock_125_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0971 | 0.1277 | +31.6% |
| alibabaBlock_127_1M | alibabaBlock_1M | f010 (+fs) | 0.1207 | 0.1470 | +21.8% |
| alibabaBlock_127_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1207 | 0.1471 | +21.9% |
| alibabaBlock_128_new | alibabaBlock_new | f010 (+fs) | 0.0908 | 0.3137 | +245.4% |
| alibabaBlock_128_new | alibabaBlock_new | f011 (+fs+rs) | 0.0908 | 0.3133 | +244.9% |
| alibabaBlock_128_new | alibabaBlock_new | f110 (+fr+fs) | 0.0908 | 0.2719 | +199.4% |
| alibabaBlock_128_new | alibabaBlock_new | f111 (all) | 0.0908 | 0.2741 | +201.8% |
| alibabaBlock_12_new | alibabaBlock_new | f100 (+fr) | 0.1359 | 0.1674 | +23.2% |
| alibabaBlock_131_new | alibabaBlock_new | f010 (+fs) | 0.0823 | 0.2809 | +241.1% |
| alibabaBlock_131_new | alibabaBlock_new | f011 (+fs+rs) | 0.0823 | 0.2808 | +241.0% |
| alibabaBlock_131_new | alibabaBlock_new | f110 (+fr+fs) | 0.0823 | 0.2192 | +166.2% |
| alibabaBlock_131_new | alibabaBlock_new | f111 (all) | 0.0823 | 0.1833 | +122.6% |
| alibabaBlock_135_new | alibabaBlock_new | f010 (+fs) | 0.0915 | 0.2861 | +212.7% |
| alibabaBlock_135_new | alibabaBlock_new | f011 (+fs+rs) | 0.0915 | 0.2874 | +214.1% |
| alibabaBlock_135_new | alibabaBlock_new | f110 (+fr+fs) | 0.0915 | 0.2522 | +175.7% |
| alibabaBlock_135_new | alibabaBlock_new | f111 (all) | 0.0915 | 0.2528 | +176.4% |
| alibabaBlock_137_1M | alibabaBlock_1M | f010 (+fs) | 0.0483 | 0.2332 | +382.7% |
| alibabaBlock_137_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0483 | 0.2331 | +382.7% |
| alibabaBlock_137_1M | alibabaBlock_1M | f100 (+fr) | 0.0483 | 0.0694 | +43.6% |
| alibabaBlock_137_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.0483 | 0.0605 | +25.3% |
| alibabaBlock_137_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0483 | 0.2328 | +381.9% |
| alibabaBlock_137_1M | alibabaBlock_1M | f111 (all) | 0.0483 | 0.2325 | +381.3% |
| alibabaBlock_139_1M | alibabaBlock_1M | f100 (+fr) | 0.0773 | 0.0955 | +23.6% |
| alibabaBlock_147_new | alibabaBlock_new | f010 (+fs) | 0.0898 | 0.2793 | +211.0% |
| alibabaBlock_147_new | alibabaBlock_new | f011 (+fs+rs) | 0.0898 | 0.2769 | +208.3% |
| alibabaBlock_147_new | alibabaBlock_new | f110 (+fr+fs) | 0.0898 | 0.1422 | +58.4% |
| alibabaBlock_147_new | alibabaBlock_new | f111 (all) | 0.0898 | 0.1371 | +52.7% |
| alibabaBlock_148_new | alibabaBlock_new | f010 (+fs) | 0.1711 | 0.3714 | +117.1% |
| alibabaBlock_148_new | alibabaBlock_new | f011 (+fs+rs) | 0.1711 | 0.3717 | +117.2% |
| alibabaBlock_148_new | alibabaBlock_new | f110 (+fr+fs) | 0.1711 | 0.3667 | +114.3% |
| alibabaBlock_148_new | alibabaBlock_new | f111 (all) | 0.1711 | 0.3668 | +114.4% |
| alibabaBlock_154_new | alibabaBlock_new | f010 (+fs) | 0.0819 | 0.3269 | +298.9% |
| alibabaBlock_154_new | alibabaBlock_new | f011 (+fs+rs) | 0.0819 | 0.3269 | +298.9% |
| alibabaBlock_154_new | alibabaBlock_new | f110 (+fr+fs) | 0.0819 | 0.2227 | +171.7% |
| alibabaBlock_154_new | alibabaBlock_new | f111 (all) | 0.0819 | 0.2166 | +164.3% |
| alibabaBlock_157_new | alibabaBlock_new | f010 (+fs) | 0.0907 | 0.2922 | +222.1% |
| alibabaBlock_157_new | alibabaBlock_new | f011 (+fs+rs) | 0.0907 | 0.2923 | +222.2% |
| alibabaBlock_157_new | alibabaBlock_new | f110 (+fr+fs) | 0.0907 | 0.1486 | +63.8% |
| alibabaBlock_157_new | alibabaBlock_new | f111 (all) | 0.0907 | 0.1456 | +60.5% |
| alibabaBlock_159_1M | alibabaBlock_1M | f100 (+fr) | 0.1467 | 0.1905 | +29.8% |
| alibabaBlock_160_new | alibabaBlock_new | f010 (+fs) | 0.1200 | 0.1628 | +35.6% |
| alibabaBlock_160_new | alibabaBlock_new | f011 (+fs+rs) | 0.1200 | 0.1614 | +34.5% |
| alibabaBlock_160_new | alibabaBlock_new | f110 (+fr+fs) | 0.1200 | 0.1610 | +34.2% |
| alibabaBlock_160_new | alibabaBlock_new | f111 (all) | 0.1200 | 0.1565 | +30.4% |
| alibabaBlock_161_new | alibabaBlock_new | f010 (+fs) | 0.1132 | 0.2846 | +151.4% |
| alibabaBlock_161_new | alibabaBlock_new | f011 (+fs+rs) | 0.1132 | 0.2826 | +149.6% |
| alibabaBlock_161_new | alibabaBlock_new | f110 (+fr+fs) | 0.1132 | 0.1611 | +42.3% |
| alibabaBlock_161_new | alibabaBlock_new | f111 (all) | 0.1132 | 0.1622 | +43.2% |
| alibabaBlock_163_new | alibabaBlock_new | f010 (+fs) | 0.0853 | 0.2006 | +135.3% |
| alibabaBlock_163_new | alibabaBlock_new | f011 (+fs+rs) | 0.0853 | 0.2004 | +135.1% |
| alibabaBlock_163_new | alibabaBlock_new | f110 (+fr+fs) | 0.0853 | 0.1956 | +129.4% |
| alibabaBlock_163_new | alibabaBlock_new | f111 (all) | 0.0853 | 0.1954 | +129.1% |
| alibabaBlock_167_1M | alibabaBlock_1M | f100 (+fr) | 0.2948 | 0.3609 | +22.4% |
| alibabaBlock_170_1M | alibabaBlock_1M | f010 (+fs) | 0.2707 | 0.4081 | +50.7% |
| alibabaBlock_170_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2707 | 0.4078 | +50.6% |
| alibabaBlock_170_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2707 | 0.3788 | +39.9% |
| alibabaBlock_170_1M | alibabaBlock_1M | f111 (all) | 0.2707 | 0.3724 | +37.6% |
| alibabaBlock_171_1M | alibabaBlock_1M | f010 (+fs) | 0.1032 | 0.1486 | +44.0% |
| alibabaBlock_171_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1032 | 0.1479 | +43.3% |
| alibabaBlock_171_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1032 | 0.1342 | +30.0% |
| alibabaBlock_171_1M | alibabaBlock_1M | f111 (all) | 0.1032 | 0.1325 | +28.4% |
| alibabaBlock_173_new | alibabaBlock_new | f010 (+fs) | 0.0862 | 0.2760 | +220.2% |
| alibabaBlock_173_new | alibabaBlock_new | f011 (+fs+rs) | 0.0862 | 0.2761 | +220.3% |
| alibabaBlock_173_new | alibabaBlock_new | f110 (+fr+fs) | 0.0862 | 0.1414 | +64.0% |
| alibabaBlock_173_new | alibabaBlock_new | f111 (all) | 0.0862 | 0.1313 | +52.3% |
| alibabaBlock_174_new | alibabaBlock_new | f010 (+fs) | 0.0865 | 0.2897 | +235.1% |
| alibabaBlock_174_new | alibabaBlock_new | f011 (+fs+rs) | 0.0865 | 0.2897 | +235.0% |
| alibabaBlock_174_new | alibabaBlock_new | f110 (+fr+fs) | 0.0865 | 0.1766 | +104.2% |
| alibabaBlock_174_new | alibabaBlock_new | f111 (all) | 0.0865 | 0.1468 | +69.7% |
| alibabaBlock_17_new | alibabaBlock_new | f010 (+fs) | 0.1580 | 0.3371 | +113.4% |
| alibabaBlock_17_new | alibabaBlock_new | f011 (+fs+rs) | 0.1580 | 0.3370 | +113.4% |
| alibabaBlock_17_new | alibabaBlock_new | f110 (+fr+fs) | 0.1580 | 0.3200 | +102.6% |
| alibabaBlock_17_new | alibabaBlock_new | f111 (all) | 0.1580 | 0.2922 | +85.0% |
| alibabaBlock_180_1M | alibabaBlock_1M | f010 (+fs) | 0.1567 | 0.2602 | +66.0% |
| alibabaBlock_180_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1567 | 0.2600 | +65.9% |
| alibabaBlock_180_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1567 | 0.2602 | +66.0% |
| alibabaBlock_180_1M | alibabaBlock_1M | f111 (all) | 0.1567 | 0.2562 | +63.5% |
| alibabaBlock_181_new | alibabaBlock_new | f010 (+fs) | 0.0399 | 0.1843 | +362.0% |
| alibabaBlock_181_new | alibabaBlock_new | f011 (+fs+rs) | 0.0399 | 0.1842 | +361.8% |
| alibabaBlock_181_new | alibabaBlock_new | f110 (+fr+fs) | 0.0399 | 0.1626 | +307.5% |
| alibabaBlock_181_new | alibabaBlock_new | f111 (all) | 0.0399 | 0.1625 | +307.2% |
| alibabaBlock_188_new | alibabaBlock_new | f010 (+fs) | 0.0381 | 0.2409 | +532.8% |
| alibabaBlock_188_new | alibabaBlock_new | f011 (+fs+rs) | 0.0381 | 0.2406 | +532.2% |
| alibabaBlock_188_new | alibabaBlock_new | f110 (+fr+fs) | 0.0381 | 0.2340 | +514.8% |
| alibabaBlock_188_new | alibabaBlock_new | f111 (all) | 0.0381 | 0.1245 | +227.2% |
| alibabaBlock_189_new | alibabaBlock_new | f010 (+fs) | 0.1546 | 0.2150 | +39.1% |
| alibabaBlock_189_new | alibabaBlock_new | f011 (+fs+rs) | 0.1546 | 0.2151 | +39.1% |
| alibabaBlock_189_new | alibabaBlock_new | f110 (+fr+fs) | 0.1546 | 0.2140 | +38.4% |
| alibabaBlock_189_new | alibabaBlock_new | f111 (all) | 0.1546 | 0.2137 | +38.2% |
| alibabaBlock_191_new | alibabaBlock_new | f010 (+fs) | 0.1749 | 0.3325 | +90.1% |
| alibabaBlock_191_new | alibabaBlock_new | f011 (+fs+rs) | 0.1749 | 0.3326 | +90.2% |
| alibabaBlock_191_new | alibabaBlock_new | f100 (+fr) | 0.1749 | 0.2204 | +26.0% |
| alibabaBlock_191_new | alibabaBlock_new | f110 (+fr+fs) | 0.1749 | 0.2841 | +62.5% |
| alibabaBlock_191_new | alibabaBlock_new | f111 (all) | 0.1749 | 0.3226 | +84.5% |
| alibabaBlock_192_new | alibabaBlock_new | f010 (+fs) | 0.0927 | 0.3175 | +242.5% |
| alibabaBlock_192_new | alibabaBlock_new | f011 (+fs+rs) | 0.0927 | 0.3167 | +241.6% |
| alibabaBlock_192_new | alibabaBlock_new | f110 (+fr+fs) | 0.0927 | 0.2694 | +190.6% |
| alibabaBlock_192_new | alibabaBlock_new | f111 (all) | 0.0927 | 0.2708 | +192.1% |
| alibabaBlock_193_new | alibabaBlock_new | f010 (+fs) | 0.0942 | 0.3071 | +226.0% |
| alibabaBlock_193_new | alibabaBlock_new | f011 (+fs+rs) | 0.0942 | 0.3070 | +225.9% |
| alibabaBlock_193_new | alibabaBlock_new | f110 (+fr+fs) | 0.0942 | 0.2592 | +175.1% |
| alibabaBlock_193_new | alibabaBlock_new | f111 (all) | 0.0942 | 0.2582 | +174.1% |
| alibabaBlock_195_new | alibabaBlock_new | f010 (+fs) | 0.0810 | 0.1736 | +114.3% |
| alibabaBlock_195_new | alibabaBlock_new | f011 (+fs+rs) | 0.0810 | 0.1738 | +114.5% |
| alibabaBlock_195_new | alibabaBlock_new | f110 (+fr+fs) | 0.0810 | 0.1645 | +103.1% |
| alibabaBlock_195_new | alibabaBlock_new | f111 (all) | 0.0810 | 0.1646 | +103.1% |
| alibabaBlock_19_new | alibabaBlock_new | f010 (+fs) | 0.0897 | 0.2738 | +205.3% |
| alibabaBlock_19_new | alibabaBlock_new | f011 (+fs+rs) | 0.0897 | 0.2732 | +204.6% |
| alibabaBlock_19_new | alibabaBlock_new | f110 (+fr+fs) | 0.0897 | 0.1481 | +65.2% |
| alibabaBlock_19_new | alibabaBlock_new | f111 (all) | 0.0897 | 0.1527 | +70.2% |
| alibabaBlock_1_new | alibabaBlock_new | f010 (+fs) | 0.0844 | 0.2083 | +146.7% |
| alibabaBlock_1_new | alibabaBlock_new | f011 (+fs+rs) | 0.0844 | 0.2083 | +146.7% |
| alibabaBlock_1_new | alibabaBlock_new | f110 (+fr+fs) | 0.0844 | 0.2018 | +139.0% |
| alibabaBlock_1_new | alibabaBlock_new | f111 (all) | 0.0844 | 0.2042 | +141.9% |
| alibabaBlock_204_1M | alibabaBlock_1M | f010 (+fs) | 0.2920 | 0.3816 | +30.7% |
| alibabaBlock_204_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2920 | 0.3817 | +30.7% |
| alibabaBlock_210_new | alibabaBlock_new | f010 (+fs) | 0.2182 | 0.3201 | +46.7% |
| alibabaBlock_210_new | alibabaBlock_new | f011 (+fs+rs) | 0.2182 | 0.3201 | +46.7% |
| alibabaBlock_210_new | alibabaBlock_new | f110 (+fr+fs) | 0.2182 | 0.2708 | +24.1% |
| alibabaBlock_210_new | alibabaBlock_new | f111 (all) | 0.2182 | 0.2717 | +24.5% |
| alibabaBlock_211_new | alibabaBlock_new | f010 (+fs) | 0.1163 | 0.1856 | +59.6% |
| alibabaBlock_211_new | alibabaBlock_new | f011 (+fs+rs) | 0.1163 | 0.1855 | +59.4% |
| alibabaBlock_211_new | alibabaBlock_new | f110 (+fr+fs) | 0.1163 | 0.1620 | +39.3% |
| alibabaBlock_211_new | alibabaBlock_new | f111 (all) | 0.1163 | 0.1847 | +58.8% |
| alibabaBlock_214_1M | alibabaBlock_1M | f010 (+fs) | 0.2636 | 0.3499 | +32.7% |
| alibabaBlock_214_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2636 | 0.3500 | +32.8% |
| alibabaBlock_214_1M | alibabaBlock_1M | f100 (+fr) | 0.2636 | 0.3269 | +24.0% |
| alibabaBlock_217_1M | alibabaBlock_1M | f010 (+fs) | 0.1883 | 0.2858 | +51.8% |
| alibabaBlock_217_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1883 | 0.2858 | +51.8% |
| alibabaBlock_217_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1883 | 0.2820 | +49.8% |
| alibabaBlock_217_1M | alibabaBlock_1M | f111 (all) | 0.1883 | 0.2834 | +50.6% |
| alibabaBlock_218_1M | alibabaBlock_1M | f100 (+fr) | 0.1145 | 0.1528 | +33.4% |
| alibabaBlock_219_new | alibabaBlock_new | f010 (+fs) | 0.0933 | 0.2007 | +115.2% |
| alibabaBlock_219_new | alibabaBlock_new | f011 (+fs+rs) | 0.0933 | 0.2017 | +116.2% |
| alibabaBlock_219_new | alibabaBlock_new | f110 (+fr+fs) | 0.0933 | 0.1982 | +112.5% |
| alibabaBlock_219_new | alibabaBlock_new | f111 (all) | 0.0933 | 0.1978 | +112.0% |
| alibabaBlock_21_1M | alibabaBlock_1M | f001 (+rs) | 0.0405 | 0.1229 | +203.6% |
| alibabaBlock_21_1M | alibabaBlock_1M | f010 (+fs) | 0.0405 | 0.4073 | +906.1% |
| alibabaBlock_21_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0405 | 0.4073 | +906.2% |
| alibabaBlock_21_1M | alibabaBlock_1M | f100 (+fr) | 0.0405 | 0.0780 | +92.6% |
| alibabaBlock_21_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0405 | 0.3421 | +745.1% |
| alibabaBlock_21_1M | alibabaBlock_1M | f111 (all) | 0.0405 | 0.3421 | +745.2% |
| alibabaBlock_228_new | alibabaBlock_new | f010 (+fs) | 0.0267 | 0.0843 | +216.0% |
| alibabaBlock_228_new | alibabaBlock_new | f011 (+fs+rs) | 0.0267 | 0.0834 | +212.9% |
| alibabaBlock_228_new | alibabaBlock_new | f110 (+fr+fs) | 0.0267 | 0.0840 | +215.2% |
| alibabaBlock_228_new | alibabaBlock_new | f111 (all) | 0.0267 | 0.0731 | +174.1% |
| alibabaBlock_229_1M | alibabaBlock_1M | f010 (+fs) | 0.2596 | 0.3490 | +34.5% |
| alibabaBlock_229_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2596 | 0.3490 | +34.4% |
| alibabaBlock_229_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2596 | 0.3125 | +20.4% |
| alibabaBlock_233_1M | alibabaBlock_1M | f010 (+fs) | 0.2669 | 0.3670 | +37.5% |
| alibabaBlock_233_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2669 | 0.3671 | +37.6% |
| alibabaBlock_233_1M | alibabaBlock_1M | f100 (+fr) | 0.2669 | 0.3251 | +21.8% |
| alibabaBlock_233_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2669 | 0.3233 | +21.1% |
| alibabaBlock_233_1M | alibabaBlock_1M | f111 (all) | 0.2669 | 0.3271 | +22.6% |
| alibabaBlock_234_1M | alibabaBlock_1M | f010 (+fs) | 0.0443 | 0.1270 | +186.7% |
| alibabaBlock_234_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0443 | 0.1268 | +186.3% |
| alibabaBlock_234_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0443 | 0.1223 | +176.1% |
| alibabaBlock_234_1M | alibabaBlock_1M | f111 (all) | 0.0443 | 0.1222 | +175.9% |
| alibabaBlock_235_1M | alibabaBlock_1M | f010 (+fs) | 0.1444 | 0.1975 | +36.8% |
| alibabaBlock_235_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1444 | 0.1974 | +36.7% |
| alibabaBlock_235_1M | alibabaBlock_1M | f100 (+fr) | 0.1444 | 0.1944 | +34.6% |
| alibabaBlock_235_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.1444 | 0.2790 | +93.2% |
| alibabaBlock_235_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1444 | 0.1857 | +28.6% |
| alibabaBlock_235_1M | alibabaBlock_1M | f111 (all) | 0.1444 | 0.1863 | +29.0% |
| alibabaBlock_236_new | alibabaBlock_new | f010 (+fs) | 0.0966 | 0.3161 | +227.4% |
| alibabaBlock_236_new | alibabaBlock_new | f011 (+fs+rs) | 0.0966 | 0.3164 | +227.7% |
| alibabaBlock_236_new | alibabaBlock_new | f110 (+fr+fs) | 0.0966 | 0.2588 | +168.0% |
| alibabaBlock_236_new | alibabaBlock_new | f111 (all) | 0.0966 | 0.2588 | +168.0% |
| alibabaBlock_237_new | alibabaBlock_new | f010 (+fs) | 0.1771 | 0.2711 | +53.0% |
| alibabaBlock_237_new | alibabaBlock_new | f011 (+fs+rs) | 0.1771 | 0.2700 | +52.4% |
| alibabaBlock_237_new | alibabaBlock_new | f110 (+fr+fs) | 0.1771 | 0.2629 | +48.4% |
| alibabaBlock_237_new | alibabaBlock_new | f111 (all) | 0.1771 | 0.2622 | +48.0% |
| alibabaBlock_238_1M | alibabaBlock_1M | f010 (+fs) | 0.0600 | 0.1445 | +140.7% |
| alibabaBlock_238_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0600 | 0.1446 | +140.9% |
| alibabaBlock_238_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0600 | 0.1155 | +92.4% |
| alibabaBlock_238_1M | alibabaBlock_1M | f111 (all) | 0.0600 | 0.1067 | +77.8% |
| alibabaBlock_239_new | alibabaBlock_new | f010 (+fs) | 0.0873 | 0.2811 | +222.1% |
| alibabaBlock_239_new | alibabaBlock_new | f011 (+fs+rs) | 0.0873 | 0.2783 | +218.9% |
| alibabaBlock_239_new | alibabaBlock_new | f110 (+fr+fs) | 0.0873 | 0.1626 | +86.3% |
| alibabaBlock_239_new | alibabaBlock_new | f111 (all) | 0.0873 | 0.1587 | +81.8% |
| alibabaBlock_23_new | alibabaBlock_new | f010 (+fs) | 0.0989 | 0.2059 | +108.2% |
| alibabaBlock_23_new | alibabaBlock_new | f011 (+fs+rs) | 0.0989 | 0.2056 | +108.0% |
| alibabaBlock_23_new | alibabaBlock_new | f110 (+fr+fs) | 0.0989 | 0.2024 | +104.6% |
| alibabaBlock_23_new | alibabaBlock_new | f111 (all) | 0.0989 | 0.2022 | +104.5% |
| alibabaBlock_240_1M | alibabaBlock_1M | f010 (+fs) | 0.0948 | 0.1617 | +70.5% |
| alibabaBlock_240_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0948 | 0.1611 | +70.0% |
| alibabaBlock_240_1M | alibabaBlock_1M | f100 (+fr) | 0.0948 | 0.1181 | +24.6% |
| alibabaBlock_240_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0948 | 0.1618 | +70.7% |
| alibabaBlock_240_1M | alibabaBlock_1M | f111 (all) | 0.0948 | 0.1616 | +70.4% |
| alibabaBlock_241_new | alibabaBlock_new | f010 (+fs) | 0.0890 | 0.2464 | +177.0% |
| alibabaBlock_241_new | alibabaBlock_new | f011 (+fs+rs) | 0.0890 | 0.2465 | +177.1% |
| alibabaBlock_241_new | alibabaBlock_new | f110 (+fr+fs) | 0.0890 | 0.2442 | +174.5% |
| alibabaBlock_241_new | alibabaBlock_new | f111 (all) | 0.0890 | 0.2441 | +174.4% |
| alibabaBlock_242_new | alibabaBlock_new | f010 (+fs) | 0.1189 | 0.1607 | +35.2% |
| alibabaBlock_242_new | alibabaBlock_new | f011 (+fs+rs) | 0.1189 | 0.1623 | +36.5% |
| alibabaBlock_242_new | alibabaBlock_new | f110 (+fr+fs) | 0.1189 | 0.1597 | +34.3% |
| alibabaBlock_242_new | alibabaBlock_new | f111 (all) | 0.1189 | 0.1589 | +33.7% |
| alibabaBlock_246_1M | alibabaBlock_1M | f010 (+fs) | 0.0465 | 0.3055 | +557.0% |
| alibabaBlock_246_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0465 | 0.3055 | +556.9% |
| alibabaBlock_246_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0465 | 0.2401 | +416.2% |
| alibabaBlock_246_1M | alibabaBlock_1M | f111 (all) | 0.0465 | 0.2404 | +417.0% |
| alibabaBlock_247_1M | alibabaBlock_1M | f010 (+fs) | 0.0409 | 0.0750 | +83.6% |
| alibabaBlock_247_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0409 | 0.0741 | +81.2% |
| alibabaBlock_247_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0409 | 0.0768 | +87.9% |
| alibabaBlock_247_1M | alibabaBlock_1M | f111 (all) | 0.0409 | 0.0757 | +85.1% |
| alibabaBlock_24_new | alibabaBlock_new | f010 (+fs) | 0.0890 | 0.2913 | +227.4% |
| alibabaBlock_24_new | alibabaBlock_new | f011 (+fs+rs) | 0.0890 | 0.2863 | +221.8% |
| alibabaBlock_24_new | alibabaBlock_new | f110 (+fr+fs) | 0.0890 | 0.1589 | +78.6% |
| alibabaBlock_24_new | alibabaBlock_new | f111 (all) | 0.0890 | 0.1534 | +72.3% |
| alibabaBlock_250_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1429 | 0.1735 | +21.4% |
| alibabaBlock_251_new | alibabaBlock_new | f010 (+fs) | 0.0820 | 0.2801 | +241.5% |
| alibabaBlock_251_new | alibabaBlock_new | f011 (+fs+rs) | 0.0820 | 0.2807 | +242.2% |
| alibabaBlock_251_new | alibabaBlock_new | f110 (+fr+fs) | 0.0820 | 0.1165 | +42.1% |
| alibabaBlock_251_new | alibabaBlock_new | f111 (all) | 0.0820 | 0.1483 | +80.8% |
| alibabaBlock_252_1M | alibabaBlock_1M | f001 (+rs) | 0.3605 | 0.4495 | +24.7% |
| alibabaBlock_259_1M | alibabaBlock_1M | f010 (+fs) | 0.0392 | 0.0967 | +146.4% |
| alibabaBlock_259_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0392 | 0.0960 | +144.9% |
| alibabaBlock_259_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0392 | 0.0950 | +142.3% |
| alibabaBlock_259_1M | alibabaBlock_1M | f111 (all) | 0.0392 | 0.0946 | +141.2% |
| alibabaBlock_262_new | alibabaBlock_new | f010 (+fs) | 0.0438 | 0.1941 | +343.5% |
| alibabaBlock_262_new | alibabaBlock_new | f011 (+fs+rs) | 0.0438 | 0.1939 | +343.1% |
| alibabaBlock_262_new | alibabaBlock_new | f110 (+fr+fs) | 0.0438 | 0.1778 | +306.2% |
| alibabaBlock_262_new | alibabaBlock_new | f111 (all) | 0.0438 | 0.1775 | +305.7% |
| alibabaBlock_264_new | alibabaBlock_new | f010 (+fs) | 0.1228 | 0.1668 | +35.8% |
| alibabaBlock_264_new | alibabaBlock_new | f011 (+fs+rs) | 0.1228 | 0.1677 | +36.6% |
| alibabaBlock_264_new | alibabaBlock_new | f110 (+fr+fs) | 0.1228 | 0.1660 | +35.1% |
| alibabaBlock_264_new | alibabaBlock_new | f111 (all) | 0.1228 | 0.1652 | +34.5% |
| alibabaBlock_266_1M | alibabaBlock_1M | f010 (+fs) | 0.1490 | 0.2574 | +72.8% |
| alibabaBlock_266_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1490 | 0.2573 | +72.7% |
| alibabaBlock_266_1M | alibabaBlock_1M | f100 (+fr) | 0.1490 | 0.2022 | +35.8% |
| alibabaBlock_266_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1490 | 0.2441 | +63.9% |
| alibabaBlock_266_1M | alibabaBlock_1M | f111 (all) | 0.1490 | 0.2484 | +66.7% |
| alibabaBlock_271_1M | alibabaBlock_1M | f100 (+fr) | 0.1311 | 0.1932 | +47.3% |
| alibabaBlock_273_new | alibabaBlock_new | f010 (+fs) | 0.1484 | 0.3288 | +121.6% |
| alibabaBlock_273_new | alibabaBlock_new | f011 (+fs+rs) | 0.1484 | 0.3288 | +121.6% |
| alibabaBlock_273_new | alibabaBlock_new | f110 (+fr+fs) | 0.1484 | 0.3135 | +111.3% |
| alibabaBlock_273_new | alibabaBlock_new | f111 (all) | 0.1484 | 0.2952 | +99.0% |
| alibabaBlock_276_new | alibabaBlock_new | f010 (+fs) | 0.1556 | 0.2557 | +64.4% |
| alibabaBlock_276_new | alibabaBlock_new | f011 (+fs+rs) | 0.1556 | 0.2553 | +64.0% |
| alibabaBlock_276_new | alibabaBlock_new | f110 (+fr+fs) | 0.1556 | 0.2477 | +59.2% |
| alibabaBlock_276_new | alibabaBlock_new | f111 (all) | 0.1556 | 0.2477 | +59.2% |
| alibabaBlock_277_1M | alibabaBlock_1M | f010 (+fs) | 0.0032 | 0.0239 | +636.2% |
| alibabaBlock_277_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0032 | 0.0115 | +255.3% |
| alibabaBlock_277_1M | alibabaBlock_1M | f100 (+fr) | 0.0032 | 0.0056 | +72.1% |
| alibabaBlock_277_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0032 | 0.0106 | +226.3% |
| alibabaBlock_277_1M | alibabaBlock_1M | f111 (all) | 0.0032 | 0.0082 | +151.7% |
| alibabaBlock_281_1M | alibabaBlock_1M | f010 (+fs) | 0.0725 | 0.1866 | +157.5% |
| alibabaBlock_281_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0725 | 0.1866 | +157.5% |
| alibabaBlock_281_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0725 | 0.1849 | +155.2% |
| alibabaBlock_281_1M | alibabaBlock_1M | f111 (all) | 0.0725 | 0.1846 | +154.8% |
| alibabaBlock_282_1M | alibabaBlock_1M | f010 (+fs) | 0.0831 | 0.1194 | +43.6% |
| alibabaBlock_282_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0831 | 0.1115 | +34.2% |
| alibabaBlock_282_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.0831 | 0.1148 | +38.1% |
| alibabaBlock_282_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0831 | 0.1147 | +38.0% |
| alibabaBlock_287_1M | alibabaBlock_1M | f001 (+rs) | 0.0379 | 0.0671 | +77.2% |
| alibabaBlock_287_1M | alibabaBlock_1M | f010 (+fs) | 0.0379 | 0.1588 | +319.2% |
| alibabaBlock_287_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0379 | 0.1587 | +318.8% |
| alibabaBlock_287_1M | alibabaBlock_1M | f100 (+fr) | 0.0379 | 0.0456 | +20.4% |
| alibabaBlock_287_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0379 | 0.1041 | +174.8% |
| alibabaBlock_287_1M | alibabaBlock_1M | f111 (all) | 0.0379 | 0.0990 | +161.2% |
| alibabaBlock_289_new | alibabaBlock_new | f010 (+fs) | 0.0630 | 0.1195 | +89.8% |
| alibabaBlock_289_new | alibabaBlock_new | f011 (+fs+rs) | 0.0630 | 0.1193 | +89.4% |
| alibabaBlock_289_new | alibabaBlock_new | f110 (+fr+fs) | 0.0630 | 0.1136 | +80.5% |
| alibabaBlock_289_new | alibabaBlock_new | f111 (all) | 0.0630 | 0.1137 | +80.6% |
| alibabaBlock_290_1M | alibabaBlock_1M | f010 (+fs) | 0.1027 | 0.1631 | +58.9% |
| alibabaBlock_290_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1027 | 0.1633 | +59.0% |
| alibabaBlock_290_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1027 | 0.1632 | +58.9% |
| alibabaBlock_290_1M | alibabaBlock_1M | f111 (all) | 0.1027 | 0.1633 | +59.0% |
| alibabaBlock_295_new | alibabaBlock_new | f010 (+fs) | 0.0807 | 0.2722 | +237.4% |
| alibabaBlock_295_new | alibabaBlock_new | f011 (+fs+rs) | 0.0807 | 0.2703 | +235.1% |
| alibabaBlock_295_new | alibabaBlock_new | f110 (+fr+fs) | 0.0807 | 0.1925 | +138.6% |
| alibabaBlock_295_new | alibabaBlock_new | f111 (all) | 0.0807 | 0.2009 | +149.1% |
| alibabaBlock_298_1M | alibabaBlock_1M | f010 (+fs) | 0.2596 | 0.3655 | +40.8% |
| alibabaBlock_298_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2596 | 0.3655 | +40.8% |
| alibabaBlock_298_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2596 | 0.3220 | +24.0% |
| alibabaBlock_298_1M | alibabaBlock_1M | f111 (all) | 0.2596 | 0.3311 | +27.5% |
| alibabaBlock_309_1M | alibabaBlock_1M | f010 (+fs) | 0.2670 | 0.3265 | +22.3% |
| alibabaBlock_309_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2670 | 0.3266 | +22.3% |
| alibabaBlock_309_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.2670 | 0.3215 | +20.4% |
| alibabaBlock_309_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2670 | 0.3223 | +20.7% |
| alibabaBlock_309_1M | alibabaBlock_1M | f111 (all) | 0.2670 | 0.3252 | +21.8% |
| alibabaBlock_30_new | alibabaBlock_new | f010 (+fs) | 0.0844 | 0.2896 | +243.0% |
| alibabaBlock_30_new | alibabaBlock_new | f011 (+fs+rs) | 0.0844 | 0.2886 | +241.8% |
| alibabaBlock_30_new | alibabaBlock_new | f110 (+fr+fs) | 0.0844 | 0.1729 | +104.7% |
| alibabaBlock_30_new | alibabaBlock_new | f111 (all) | 0.0844 | 0.1541 | +82.6% |
| alibabaBlock_311_new | alibabaBlock_new | f010 (+fs) | 0.0474 | 0.1399 | +195.1% |
| alibabaBlock_311_new | alibabaBlock_new | f011 (+fs+rs) | 0.0474 | 0.1396 | +194.6% |
| alibabaBlock_311_new | alibabaBlock_new | f110 (+fr+fs) | 0.0474 | 0.1259 | +165.5% |
| alibabaBlock_311_new | alibabaBlock_new | f111 (all) | 0.0474 | 0.1251 | +164.0% |
| alibabaBlock_314_1M | alibabaBlock_1M | f010 (+fs) | 0.0920 | 0.1416 | +53.9% |
| alibabaBlock_314_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0920 | 0.1415 | +53.8% |
| alibabaBlock_314_1M | alibabaBlock_1M | f100 (+fr) | 0.0920 | 0.1286 | +39.7% |
| alibabaBlock_314_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0920 | 0.1336 | +45.2% |
| alibabaBlock_314_1M | alibabaBlock_1M | f111 (all) | 0.0920 | 0.1326 | +44.2% |
| alibabaBlock_317_100K | alibabaBlock_100K | f010 (+fs) | 0.5924 | 0.7527 | +27.1% |
| alibabaBlock_317_100K | alibabaBlock_100K | f011 (+fs+rs) | 0.5924 | 0.7528 | +27.1% |
| alibabaBlock_318_1M | alibabaBlock_1M | f010 (+fs) | 0.0811 | 0.2057 | +153.6% |
| alibabaBlock_318_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0811 | 0.2052 | +153.0% |
| alibabaBlock_318_1M | alibabaBlock_1M | f100 (+fr) | 0.0811 | 0.1013 | +24.9% |
| alibabaBlock_318_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0811 | 0.1996 | +146.1% |
| alibabaBlock_318_1M | alibabaBlock_1M | f111 (all) | 0.0811 | 0.2021 | +149.1% |
| alibabaBlock_31_1M | alibabaBlock_1M | f010 (+fs) | 0.0541 | 0.0698 | +29.1% |
| alibabaBlock_31_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0541 | 0.0690 | +27.6% |
| alibabaBlock_31_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0541 | 0.0710 | +31.3% |
| alibabaBlock_31_1M | alibabaBlock_1M | f111 (all) | 0.0541 | 0.0690 | +27.5% |
| alibabaBlock_320_1M | alibabaBlock_1M | f010 (+fs) | 0.1519 | 0.2039 | +34.3% |
| alibabaBlock_320_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1519 | 0.2025 | +33.3% |
| alibabaBlock_320_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1519 | 0.2024 | +33.3% |
| alibabaBlock_320_1M | alibabaBlock_1M | f111 (all) | 0.1519 | 0.2015 | +32.7% |
| alibabaBlock_321_1M | alibabaBlock_1M | f010 (+fs) | 0.1930 | 0.3311 | +71.5% |
| alibabaBlock_321_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1930 | 0.3311 | +71.5% |
| alibabaBlock_321_1M | alibabaBlock_1M | f100 (+fr) | 0.1930 | 0.2642 | +36.9% |
| alibabaBlock_321_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1930 | 0.3068 | +59.0% |
| alibabaBlock_321_1M | alibabaBlock_1M | f111 (all) | 0.1930 | 0.3001 | +55.5% |
| alibabaBlock_322_1M | alibabaBlock_1M | f001 (+rs) | 0.3364 | 0.4043 | +20.2% |
| alibabaBlock_322_1M | alibabaBlock_1M | f111 (all) | 0.3364 | 0.4125 | +22.6% |
| alibabaBlock_324_new | alibabaBlock_new | f010 (+fs) | 0.1506 | 0.3298 | +118.9% |
| alibabaBlock_324_new | alibabaBlock_new | f011 (+fs+rs) | 0.1506 | 0.3297 | +118.9% |
| alibabaBlock_324_new | alibabaBlock_new | f101 (+fr+rs) | 0.1506 | 0.1880 | +24.8% |
| alibabaBlock_324_new | alibabaBlock_new | f110 (+fr+fs) | 0.1506 | 0.2970 | +97.2% |
| alibabaBlock_324_new | alibabaBlock_new | f111 (all) | 0.1506 | 0.3031 | +101.2% |
| alibabaBlock_327_new | alibabaBlock_new | f010 (+fs) | 0.0854 | 0.2065 | +141.8% |
| alibabaBlock_327_new | alibabaBlock_new | f011 (+fs+rs) | 0.0854 | 0.2062 | +141.5% |
| alibabaBlock_327_new | alibabaBlock_new | f110 (+fr+fs) | 0.0854 | 0.2022 | +136.8% |
| alibabaBlock_327_new | alibabaBlock_new | f111 (all) | 0.0854 | 0.2021 | +136.8% |
| alibabaBlock_329_1M | alibabaBlock_1M | f010 (+fs) | 0.0823 | 0.1012 | +23.1% |
| alibabaBlock_329_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0823 | 0.0994 | +20.9% |
| alibabaBlock_329_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0823 | 0.1017 | +23.6% |
| alibabaBlock_329_1M | alibabaBlock_1M | f111 (all) | 0.0823 | 0.1013 | +23.1% |
| alibabaBlock_332_1M | alibabaBlock_1M | f010 (+fs) | 0.0473 | 0.1406 | +197.1% |
| alibabaBlock_332_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0473 | 0.1394 | +194.6% |
| alibabaBlock_332_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0473 | 0.1245 | +163.0% |
| alibabaBlock_332_1M | alibabaBlock_1M | f111 (all) | 0.0473 | 0.1239 | +161.8% |
| alibabaBlock_334_1M | alibabaBlock_1M | f010 (+fs) | 0.0924 | 0.1375 | +48.8% |
| alibabaBlock_334_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0924 | 0.1375 | +48.8% |
| alibabaBlock_334_1M | alibabaBlock_1M | f100 (+fr) | 0.0924 | 0.1182 | +27.9% |
| alibabaBlock_334_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0924 | 0.1377 | +49.1% |
| alibabaBlock_334_1M | alibabaBlock_1M | f111 (all) | 0.0924 | 0.1386 | +50.0% |
| alibabaBlock_335_1M | alibabaBlock_1M | f010 (+fs) | 0.0399 | 0.1030 | +158.2% |
| alibabaBlock_335_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0399 | 0.1027 | +157.4% |
| alibabaBlock_335_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0399 | 0.1031 | +158.4% |
| alibabaBlock_335_1M | alibabaBlock_1M | f111 (all) | 0.0399 | 0.1029 | +157.8% |
| alibabaBlock_336_new | alibabaBlock_new | f010 (+fs) | 0.0383 | 0.1699 | +343.6% |
| alibabaBlock_336_new | alibabaBlock_new | f011 (+fs+rs) | 0.0383 | 0.1701 | +344.1% |
| alibabaBlock_336_new | alibabaBlock_new | f110 (+fr+fs) | 0.0383 | 0.1446 | +277.6% |
| alibabaBlock_336_new | alibabaBlock_new | f111 (all) | 0.0383 | 0.1438 | +275.5% |
| alibabaBlock_337_1M | alibabaBlock_1M | f010 (+fs) | 0.2139 | 0.4203 | +96.5% |
| alibabaBlock_337_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2139 | 0.4203 | +96.5% |
| alibabaBlock_337_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2139 | 0.3851 | +80.1% |
| alibabaBlock_337_1M | alibabaBlock_1M | f111 (all) | 0.2139 | 0.3878 | +81.3% |
| alibabaBlock_338_1M | alibabaBlock_1M | f010 (+fs) | 0.1244 | 0.1664 | +33.8% |
| alibabaBlock_338_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1244 | 0.1665 | +33.9% |
| alibabaBlock_338_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1244 | 0.1665 | +33.8% |
| alibabaBlock_338_1M | alibabaBlock_1M | f111 (all) | 0.1244 | 0.1658 | +33.3% |
| alibabaBlock_339_new | alibabaBlock_new | f010 (+fs) | 0.1720 | 0.3355 | +95.1% |
| alibabaBlock_339_new | alibabaBlock_new | f011 (+fs+rs) | 0.1720 | 0.3355 | +95.1% |
| alibabaBlock_339_new | alibabaBlock_new | f100 (+fr) | 0.1720 | 0.2236 | +30.0% |
| alibabaBlock_339_new | alibabaBlock_new | f110 (+fr+fs) | 0.1720 | 0.3117 | +81.3% |
| alibabaBlock_339_new | alibabaBlock_new | f111 (all) | 0.1720 | 0.2858 | +66.2% |
| alibabaBlock_33_new | alibabaBlock_new | f010 (+fs) | 0.0934 | 0.2878 | +208.2% |
| alibabaBlock_33_new | alibabaBlock_new | f011 (+fs+rs) | 0.0934 | 0.2856 | +205.9% |
| alibabaBlock_33_new | alibabaBlock_new | f110 (+fr+fs) | 0.0934 | 0.1487 | +59.3% |
| alibabaBlock_33_new | alibabaBlock_new | f111 (all) | 0.0934 | 0.1458 | +56.1% |
| alibabaBlock_340_1M | alibabaBlock_1M | f010 (+fs) | 0.1691 | 0.2625 | +55.2% |
| alibabaBlock_340_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1691 | 0.2625 | +55.2% |
| alibabaBlock_340_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1691 | 0.2558 | +51.2% |
| alibabaBlock_340_1M | alibabaBlock_1M | f111 (all) | 0.1691 | 0.2571 | +52.0% |
| alibabaBlock_343_1M | alibabaBlock_1M | f010 (+fs) | 0.2409 | 0.3416 | +41.8% |
| alibabaBlock_343_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2409 | 0.3416 | +41.8% |
| alibabaBlock_343_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2409 | 0.3083 | +28.0% |
| alibabaBlock_343_1M | alibabaBlock_1M | f111 (all) | 0.2409 | 0.3018 | +25.3% |
| alibabaBlock_354_new | alibabaBlock_new | f010 (+fs) | 0.1630 | 0.1970 | +20.9% |
| alibabaBlock_354_new | alibabaBlock_new | f011 (+fs+rs) | 0.1630 | 0.1968 | +20.7% |
| alibabaBlock_356_1M | alibabaBlock_1M | f010 (+fs) | 0.1004 | 0.1787 | +78.0% |
| alibabaBlock_356_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1004 | 0.1787 | +78.0% |
| alibabaBlock_356_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1004 | 0.1709 | +70.2% |
| alibabaBlock_356_1M | alibabaBlock_1M | f111 (all) | 0.1004 | 0.1718 | +71.2% |
| alibabaBlock_359_1M | alibabaBlock_1M | f001 (+rs) | 0.0764 | 0.1136 | +48.7% |
| alibabaBlock_359_1M | alibabaBlock_1M | f010 (+fs) | 0.0764 | 0.1710 | +123.8% |
| alibabaBlock_359_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0764 | 0.1700 | +122.6% |
| alibabaBlock_359_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0764 | 0.1675 | +119.4% |
| alibabaBlock_359_1M | alibabaBlock_1M | f111 (all) | 0.0764 | 0.1628 | +113.1% |
| alibabaBlock_360_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.0521 | 0.0805 | +54.5% |
| alibabaBlock_361_new | alibabaBlock_new | f010 (+fs) | 0.1264 | 0.1563 | +23.6% |
| alibabaBlock_361_new | alibabaBlock_new | f011 (+fs+rs) | 0.1264 | 0.1561 | +23.5% |
| alibabaBlock_361_new | alibabaBlock_new | f110 (+fr+fs) | 0.1264 | 0.1536 | +21.5% |
| alibabaBlock_361_new | alibabaBlock_new | f111 (all) | 0.1264 | 0.1520 | +20.2% |
| alibabaBlock_364_100K | alibabaBlock_100K | f010 (+fs) | 0.1600 | 0.6404 | +300.1% |
| alibabaBlock_364_100K | alibabaBlock_100K | f011 (+fs+rs) | 0.1600 | 0.6402 | +300.0% |
| alibabaBlock_364_100K | alibabaBlock_100K | f110 (+fr+fs) | 0.1600 | 0.6401 | +299.9% |
| alibabaBlock_364_100K | alibabaBlock_100K | f111 (all) | 0.1600 | 0.6401 | +300.0% |
| alibabaBlock_378_1M | alibabaBlock_1M | f010 (+fs) | 0.0984 | 0.2144 | +118.0% |
| alibabaBlock_378_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0984 | 0.2147 | +118.3% |
| alibabaBlock_378_1M | alibabaBlock_1M | f100 (+fr) | 0.0984 | 0.1499 | +52.4% |
| alibabaBlock_378_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0984 | 0.2082 | +111.7% |
| alibabaBlock_378_1M | alibabaBlock_1M | f111 (all) | 0.0984 | 0.2064 | +109.9% |
| alibabaBlock_386_1M | alibabaBlock_1M | f010 (+fs) | 0.3001 | 0.3914 | +30.4% |
| alibabaBlock_386_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.3001 | 0.3914 | +30.4% |
| alibabaBlock_387_1M | alibabaBlock_1M | f010 (+fs) | 0.3089 | 0.3747 | +21.3% |
| alibabaBlock_387_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.3089 | 0.3747 | +21.3% |
| alibabaBlock_38_new | alibabaBlock_new | f010 (+fs) | 0.0510 | 0.0999 | +96.1% |
| alibabaBlock_38_new | alibabaBlock_new | f011 (+fs+rs) | 0.0510 | 0.0980 | +92.4% |
| alibabaBlock_38_new | alibabaBlock_new | f100 (+fr) | 0.0510 | 0.0659 | +29.4% |
| alibabaBlock_38_new | alibabaBlock_new | f110 (+fr+fs) | 0.0510 | 0.0620 | +21.8% |
| alibabaBlock_38_new | alibabaBlock_new | f111 (all) | 0.0510 | 0.0864 | +69.6% |
| alibabaBlock_393_100K | alibabaBlock_100K | f100 (+fr) | 0.3028 | 0.3887 | +28.4% |
| alibabaBlock_393_100K | alibabaBlock_100K | f101 (+fr+rs) | 0.3028 | 0.3726 | +23.0% |
| alibabaBlock_395_new | alibabaBlock_new | f010 (+fs) | 0.1898 | 0.3289 | +73.3% |
| alibabaBlock_395_new | alibabaBlock_new | f011 (+fs+rs) | 0.1898 | 0.3288 | +73.2% |
| alibabaBlock_395_new | alibabaBlock_new | f110 (+fr+fs) | 0.1898 | 0.3143 | +65.6% |
| alibabaBlock_395_new | alibabaBlock_new | f111 (all) | 0.1898 | 0.3286 | +73.1% |
| alibabaBlock_396_1M | alibabaBlock_1M | f010 (+fs) | 0.0978 | 0.2232 | +128.4% |
| alibabaBlock_396_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0978 | 0.2226 | +127.8% |
| alibabaBlock_396_1M | alibabaBlock_1M | f100 (+fr) | 0.0978 | 0.1393 | +42.5% |
| alibabaBlock_396_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0978 | 0.2187 | +123.7% |
| alibabaBlock_396_1M | alibabaBlock_1M | f111 (all) | 0.0978 | 0.2159 | +120.9% |
| alibabaBlock_398_1M | alibabaBlock_1M | f010 (+fs) | 0.0684 | 0.1251 | +83.0% |
| alibabaBlock_398_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0684 | 0.1247 | +82.4% |
| alibabaBlock_398_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0684 | 0.1247 | +82.4% |
| alibabaBlock_398_1M | alibabaBlock_1M | f111 (all) | 0.0684 | 0.1250 | +82.8% |
| alibabaBlock_399_new | alibabaBlock_new | f010 (+fs) | 0.0840 | 0.2031 | +141.7% |
| alibabaBlock_399_new | alibabaBlock_new | f011 (+fs+rs) | 0.0840 | 0.2032 | +141.9% |
| alibabaBlock_399_new | alibabaBlock_new | f110 (+fr+fs) | 0.0840 | 0.1992 | +137.0% |
| alibabaBlock_399_new | alibabaBlock_new | f111 (all) | 0.0840 | 0.1995 | +137.5% |
| alibabaBlock_400_1M | alibabaBlock_1M | f010 (+fs) | 0.2200 | 0.2828 | +28.6% |
| alibabaBlock_400_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2200 | 0.2825 | +28.4% |
| alibabaBlock_401_new | alibabaBlock_new | f010 (+fs) | 0.1486 | 0.3284 | +121.0% |
| alibabaBlock_401_new | alibabaBlock_new | f011 (+fs+rs) | 0.1486 | 0.3281 | +120.9% |
| alibabaBlock_401_new | alibabaBlock_new | f110 (+fr+fs) | 0.1486 | 0.2805 | +88.8% |
| alibabaBlock_401_new | alibabaBlock_new | f111 (all) | 0.1486 | 0.3281 | +120.9% |
| alibabaBlock_402_new | alibabaBlock_new | f001 (+rs) | 0.0847 | 0.1027 | +21.3% |
| alibabaBlock_402_new | alibabaBlock_new | f010 (+fs) | 0.0847 | 0.2065 | +143.9% |
| alibabaBlock_402_new | alibabaBlock_new | f011 (+fs+rs) | 0.0847 | 0.2065 | +143.9% |
| alibabaBlock_402_new | alibabaBlock_new | f110 (+fr+fs) | 0.0847 | 0.2000 | +136.2% |
| alibabaBlock_402_new | alibabaBlock_new | f111 (all) | 0.0847 | 0.2022 | +138.8% |
| alibabaBlock_407_1M | alibabaBlock_1M | f100 (+fr) | 0.1493 | 0.1937 | +29.7% |
| alibabaBlock_407_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.1493 | 0.2303 | +54.2% |
| alibabaBlock_408_1M | alibabaBlock_1M | f001 (+rs) | 0.0747 | 0.0934 | +25.1% |
| alibabaBlock_408_1M | alibabaBlock_1M | f010 (+fs) | 0.0747 | 0.1018 | +36.3% |
| alibabaBlock_408_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0747 | 0.1013 | +35.7% |
| alibabaBlock_408_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0747 | 0.1019 | +36.5% |
| alibabaBlock_408_1M | alibabaBlock_1M | f111 (all) | 0.0747 | 0.1021 | +36.7% |
| alibabaBlock_410_1M | alibabaBlock_1M | f100 (+fr) | 0.1270 | 0.1563 | +23.0% |
| alibabaBlock_412_1M | alibabaBlock_1M | f010 (+fs) | 0.1097 | 0.2376 | +116.5% |
| alibabaBlock_412_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1097 | 0.2375 | +116.4% |
| alibabaBlock_412_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1097 | 0.2371 | +116.0% |
| alibabaBlock_412_1M | alibabaBlock_1M | f111 (all) | 0.1097 | 0.2325 | +111.9% |
| alibabaBlock_417_1M | alibabaBlock_1M | f010 (+fs) | 0.1054 | 0.1392 | +32.1% |
| alibabaBlock_417_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1054 | 0.1396 | +32.4% |
| alibabaBlock_417_1M | alibabaBlock_1M | f111 (all) | 0.1054 | 0.1301 | +23.4% |
| alibabaBlock_418_1M | alibabaBlock_1M | f010 (+fs) | 0.2865 | 0.3457 | +20.7% |
| alibabaBlock_418_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2865 | 0.3455 | +20.6% |
| alibabaBlock_418_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2865 | 0.3458 | +20.7% |
| alibabaBlock_421_1M | alibabaBlock_1M | f010 (+fs) | 0.0750 | 0.1382 | +84.4% |
| alibabaBlock_421_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0750 | 0.1375 | +83.4% |
| alibabaBlock_421_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0750 | 0.1379 | +84.0% |
| alibabaBlock_421_1M | alibabaBlock_1M | f111 (all) | 0.0750 | 0.1383 | +84.5% |
| alibabaBlock_428_100K | alibabaBlock_100K | f100 (+fr) | 0.2577 | 0.3461 | +34.3% |
| alibabaBlock_429_1M | alibabaBlock_1M | f010 (+fs) | 0.1110 | 0.1809 | +63.0% |
| alibabaBlock_429_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1110 | 0.1808 | +63.0% |
| alibabaBlock_429_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1110 | 0.1807 | +62.8% |
| alibabaBlock_429_1M | alibabaBlock_1M | f111 (all) | 0.1110 | 0.1807 | +62.9% |
| alibabaBlock_430_new | alibabaBlock_new | f010 (+fs) | 0.0887 | 0.2024 | +128.2% |
| alibabaBlock_430_new | alibabaBlock_new | f011 (+fs+rs) | 0.0887 | 0.2024 | +128.1% |
| alibabaBlock_430_new | alibabaBlock_new | f110 (+fr+fs) | 0.0887 | 0.1988 | +124.1% |
| alibabaBlock_430_new | alibabaBlock_new | f111 (all) | 0.0887 | 0.1976 | +122.7% |
| alibabaBlock_433_1M | alibabaBlock_1M | f010 (+fs) | 0.0773 | 0.1066 | +37.9% |
| alibabaBlock_433_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0773 | 0.1071 | +38.6% |
| alibabaBlock_433_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0773 | 0.1059 | +36.9% |
| alibabaBlock_433_1M | alibabaBlock_1M | f111 (all) | 0.0773 | 0.1062 | +37.4% |
| alibabaBlock_435_new | alibabaBlock_new | f010 (+fs) | 0.0996 | 0.2142 | +115.0% |
| alibabaBlock_435_new | alibabaBlock_new | f011 (+fs+rs) | 0.0996 | 0.2143 | +115.1% |
| alibabaBlock_435_new | alibabaBlock_new | f110 (+fr+fs) | 0.0996 | 0.2133 | +114.1% |
| alibabaBlock_435_new | alibabaBlock_new | f111 (all) | 0.0996 | 0.2127 | +113.6% |
| alibabaBlock_439_1M | alibabaBlock_1M | f010 (+fs) | 0.1132 | 0.1723 | +52.1% |
| alibabaBlock_439_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1132 | 0.1723 | +52.1% |
| alibabaBlock_439_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1132 | 0.1708 | +50.8% |
| alibabaBlock_439_1M | alibabaBlock_1M | f111 (all) | 0.1132 | 0.1706 | +50.7% |
| alibabaBlock_443_100K | alibabaBlock_100K | f001 (+rs) | 0.1697 | 0.2059 | +21.3% |
| alibabaBlock_443_100K | alibabaBlock_100K | f101 (+fr+rs) | 0.1697 | 0.2070 | +22.0% |
| alibabaBlock_443_100K | alibabaBlock_100K | f110 (+fr+fs) | 0.1697 | 0.2040 | +20.2% |
| alibabaBlock_456_1M | alibabaBlock_1M | f010 (+fs) | 0.1347 | 0.1624 | +20.6% |
| alibabaBlock_456_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1347 | 0.1622 | +20.4% |
| alibabaBlock_456_1M | alibabaBlock_1M | f100 (+fr) | 0.1347 | 0.1742 | +29.4% |
| alibabaBlock_456_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.1347 | 0.2632 | +95.4% |
| alibabaBlock_457_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1100 | 0.1332 | +21.1% |
| alibabaBlock_457_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1100 | 0.1431 | +30.1% |
| alibabaBlock_457_1M | alibabaBlock_1M | f111 (all) | 0.1100 | 0.1419 | +29.0% |
| alibabaBlock_460_new | alibabaBlock_new | f010 (+fs) | 0.1229 | 0.1549 | +26.1% |
| alibabaBlock_460_new | alibabaBlock_new | f011 (+fs+rs) | 0.1229 | 0.1564 | +27.3% |
| alibabaBlock_461_1M | alibabaBlock_1M | f100 (+fr) | 0.0693 | 0.1001 | +44.4% |
| alibabaBlock_462_1M | alibabaBlock_1M | f010 (+fs) | 0.1143 | 0.2255 | +97.3% |
| alibabaBlock_462_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1143 | 0.2253 | +97.2% |
| alibabaBlock_462_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.1143 | 0.1458 | +27.6% |
| alibabaBlock_462_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1143 | 0.2252 | +97.0% |
| alibabaBlock_462_1M | alibabaBlock_1M | f111 (all) | 0.1143 | 0.2237 | +95.8% |
| alibabaBlock_46_new | alibabaBlock_new | f010 (+fs) | 0.0836 | 0.2821 | +237.5% |
| alibabaBlock_46_new | alibabaBlock_new | f011 (+fs+rs) | 0.0836 | 0.2824 | +237.9% |
| alibabaBlock_46_new | alibabaBlock_new | f110 (+fr+fs) | 0.0836 | 0.1703 | +103.8% |
| alibabaBlock_46_new | alibabaBlock_new | f111 (all) | 0.0836 | 0.1636 | +95.7% |
| alibabaBlock_471_1M | alibabaBlock_1M | f010 (+fs) | 0.3098 | 0.3787 | +22.2% |
| alibabaBlock_471_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.3098 | 0.3787 | +22.2% |
| alibabaBlock_473_1M | alibabaBlock_1M | f010 (+fs) | 0.3127 | 0.3768 | +20.5% |
| alibabaBlock_473_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.3127 | 0.3768 | +20.5% |
| alibabaBlock_474_1M | alibabaBlock_1M | f001 (+rs) | 0.0805 | 0.0980 | +21.8% |
| alibabaBlock_474_1M | alibabaBlock_1M | f010 (+fs) | 0.0805 | 0.1501 | +86.5% |
| alibabaBlock_474_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0805 | 0.1497 | +86.0% |
| alibabaBlock_474_1M | alibabaBlock_1M | f100 (+fr) | 0.0805 | 0.1027 | +27.6% |
| alibabaBlock_474_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0805 | 0.1485 | +84.6% |
| alibabaBlock_474_1M | alibabaBlock_1M | f111 (all) | 0.0805 | 0.1502 | +86.7% |
| alibabaBlock_477_1M | alibabaBlock_1M | f100 (+fr) | 0.0866 | 0.1140 | +31.6% |
| alibabaBlock_483_new | alibabaBlock_new | f010 (+fs) | 0.1158 | 0.1547 | +33.7% |
| alibabaBlock_483_new | alibabaBlock_new | f011 (+fs+rs) | 0.1158 | 0.1533 | +32.4% |
| alibabaBlock_483_new | alibabaBlock_new | f110 (+fr+fs) | 0.1158 | 0.1407 | +21.5% |
| alibabaBlock_483_new | alibabaBlock_new | f111 (all) | 0.1158 | 0.1412 | +22.0% |
| alibabaBlock_484_1M | alibabaBlock_1M | f010 (+fs) | 0.0826 | 0.1722 | +108.3% |
| alibabaBlock_484_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0826 | 0.1720 | +108.2% |
| alibabaBlock_484_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0826 | 0.1692 | +104.7% |
| alibabaBlock_484_1M | alibabaBlock_1M | f111 (all) | 0.0826 | 0.1706 | +106.5% |
| alibabaBlock_489_1M | alibabaBlock_1M | f001 (+rs) | 0.2545 | 0.3186 | +25.2% |
| alibabaBlock_489_1M | alibabaBlock_1M | f010 (+fs) | 0.2545 | 0.3321 | +30.5% |
| alibabaBlock_489_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2545 | 0.3322 | +30.6% |
| alibabaBlock_489_1M | alibabaBlock_1M | f100 (+fr) | 0.2545 | 0.3459 | +35.9% |
| alibabaBlock_489_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2545 | 0.3309 | +30.0% |
| alibabaBlock_489_1M | alibabaBlock_1M | f111 (all) | 0.2545 | 0.3316 | +30.3% |
| alibabaBlock_48_new | alibabaBlock_new | f010 (+fs) | 0.0999 | 0.2957 | +196.1% |
| alibabaBlock_48_new | alibabaBlock_new | f011 (+fs+rs) | 0.0999 | 0.2915 | +191.8% |
| alibabaBlock_48_new | alibabaBlock_new | f110 (+fr+fs) | 0.0999 | 0.1551 | +55.3% |
| alibabaBlock_48_new | alibabaBlock_new | f111 (all) | 0.0999 | 0.1515 | +51.7% |
| alibabaBlock_491_1M | alibabaBlock_1M | f010 (+fs) | 0.2871 | 0.3481 | +21.2% |
| alibabaBlock_491_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2871 | 0.3481 | +21.3% |
| alibabaBlock_492_1M | alibabaBlock_1M | f010 (+fs) | 0.1638 | 0.2439 | +48.9% |
| alibabaBlock_492_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1638 | 0.2441 | +49.0% |
| alibabaBlock_492_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1638 | 0.2156 | +31.6% |
| alibabaBlock_492_1M | alibabaBlock_1M | f111 (all) | 0.1638 | 0.2118 | +29.3% |
| alibabaBlock_493_1M | alibabaBlock_1M | f010 (+fs) | 0.2517 | 0.3320 | +31.9% |
| alibabaBlock_493_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2517 | 0.3320 | +31.9% |
| alibabaBlock_493_1M | alibabaBlock_1M | f100 (+fr) | 0.2517 | 0.3049 | +21.2% |
| alibabaBlock_493_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2517 | 0.3310 | +31.5% |
| alibabaBlock_493_1M | alibabaBlock_1M | f111 (all) | 0.2517 | 0.3312 | +31.6% |
| alibabaBlock_495_1M | alibabaBlock_1M | f100 (+fr) | 0.3095 | 0.3830 | +23.8% |
| alibabaBlock_496_1M | alibabaBlock_1M | f010 (+fs) | 0.1159 | 0.1698 | +46.5% |
| alibabaBlock_496_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1159 | 0.1695 | +46.2% |
| alibabaBlock_496_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1159 | 0.1657 | +43.0% |
| alibabaBlock_496_1M | alibabaBlock_1M | f111 (all) | 0.1159 | 0.1659 | +43.1% |
| alibabaBlock_498_1M | alibabaBlock_1M | f010 (+fs) | 0.1092 | 0.1317 | +20.6% |
| alibabaBlock_498_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1092 | 0.1316 | +20.6% |
| alibabaBlock_49_1M | alibabaBlock_1M | f010 (+fs) | 0.0686 | 0.0826 | +20.4% |
| alibabaBlock_49_1M | alibabaBlock_1M | f100 (+fr) | 0.0686 | 0.1007 | +46.9% |
| alibabaBlock_49_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.0686 | 0.0825 | +20.2% |
| alibabaBlock_49_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0686 | 0.0957 | +39.6% |
| alibabaBlock_4_new | alibabaBlock_new | f010 (+fs) | 0.0320 | 0.1491 | +366.0% |
| alibabaBlock_4_new | alibabaBlock_new | f011 (+fs+rs) | 0.0320 | 0.1491 | +366.0% |
| alibabaBlock_4_new | alibabaBlock_new | f110 (+fr+fs) | 0.0320 | 0.0461 | +43.9% |
| alibabaBlock_4_new | alibabaBlock_new | f111 (all) | 0.0320 | 0.0461 | +43.9% |
| alibabaBlock_500_1M | alibabaBlock_1M | f001 (+rs) | 0.0584 | 0.1074 | +84.0% |
| alibabaBlock_500_1M | alibabaBlock_1M | f010 (+fs) | 0.0584 | 0.1447 | +147.8% |
| alibabaBlock_500_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0584 | 0.1448 | +148.0% |
| alibabaBlock_500_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0584 | 0.1372 | +135.0% |
| alibabaBlock_500_1M | alibabaBlock_1M | f111 (all) | 0.0584 | 0.1445 | +147.5% |
| alibabaBlock_502_1M | alibabaBlock_1M | f010 (+fs) | 0.0892 | 0.1474 | +65.2% |
| alibabaBlock_502_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0892 | 0.1473 | +65.1% |
| alibabaBlock_502_1M | alibabaBlock_1M | f100 (+fr) | 0.0892 | 0.1126 | +26.2% |
| alibabaBlock_502_1M | alibabaBlock_1M | f111 (all) | 0.0892 | 0.1475 | +65.4% |
| alibabaBlock_506_1M | alibabaBlock_1M | f010 (+fs) | 0.3120 | 0.3844 | +23.2% |
| alibabaBlock_506_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.3120 | 0.3845 | +23.2% |
| alibabaBlock_508_1M | alibabaBlock_1M | f010 (+fs) | 0.3075 | 0.3940 | +28.1% |
| alibabaBlock_508_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.3075 | 0.3941 | +28.2% |
| alibabaBlock_509_new | alibabaBlock_new | f010 (+fs) | 0.0850 | 0.1973 | +132.2% |
| alibabaBlock_509_new | alibabaBlock_new | f011 (+fs+rs) | 0.0850 | 0.1978 | +132.7% |
| alibabaBlock_509_new | alibabaBlock_new | f110 (+fr+fs) | 0.0850 | 0.1936 | +127.8% |
| alibabaBlock_509_new | alibabaBlock_new | f111 (all) | 0.0850 | 0.1933 | +127.5% |
| alibabaBlock_510_1M | alibabaBlock_1M | f010 (+fs) | 0.2470 | 0.3411 | +38.1% |
| alibabaBlock_510_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2470 | 0.3411 | +38.1% |
| alibabaBlock_510_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2470 | 0.3085 | +24.9% |
| alibabaBlock_510_1M | alibabaBlock_1M | f111 (all) | 0.2470 | 0.3044 | +23.2% |
| alibabaBlock_511_1M | alibabaBlock_1M | f010 (+fs) | 0.0810 | 0.2095 | +158.8% |
| alibabaBlock_511_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0810 | 0.2096 | +158.9% |
| alibabaBlock_511_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0810 | 0.2023 | +149.9% |
| alibabaBlock_511_1M | alibabaBlock_1M | f111 (all) | 0.0810 | 0.2040 | +151.9% |
| alibabaBlock_513_new | alibabaBlock_new | f010 (+fs) | 0.0847 | 0.2040 | +140.9% |
| alibabaBlock_513_new | alibabaBlock_new | f011 (+fs+rs) | 0.0847 | 0.2039 | +140.7% |
| alibabaBlock_513_new | alibabaBlock_new | f110 (+fr+fs) | 0.0847 | 0.1993 | +135.3% |
| alibabaBlock_513_new | alibabaBlock_new | f111 (all) | 0.0847 | 0.1979 | +133.6% |
| alibabaBlock_517_1M | alibabaBlock_1M | f100 (+fr) | 0.1168 | 0.2495 | +113.6% |
| alibabaBlock_519_100K | alibabaBlock_100K | f100 (+fr) | 0.2647 | 0.3435 | +29.8% |
| alibabaBlock_522_new | alibabaBlock_new | f010 (+fs) | 0.0566 | 0.1504 | +165.7% |
| alibabaBlock_522_new | alibabaBlock_new | f011 (+fs+rs) | 0.0566 | 0.1505 | +165.8% |
| alibabaBlock_522_new | alibabaBlock_new | f110 (+fr+fs) | 0.0566 | 0.1447 | +155.7% |
| alibabaBlock_522_new | alibabaBlock_new | f111 (all) | 0.0566 | 0.1439 | +154.1% |
| alibabaBlock_525_1M | alibabaBlock_1M | f010 (+fs) | 0.2983 | 0.3726 | +24.9% |
| alibabaBlock_525_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2983 | 0.3726 | +24.9% |
| alibabaBlock_530_100K | alibabaBlock_100K | f100 (+fr) | 0.1562 | 0.1988 | +27.3% |
| alibabaBlock_532_1M | alibabaBlock_1M | f010 (+fs) | 0.2392 | 0.3071 | +28.4% |
| alibabaBlock_532_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2392 | 0.3072 | +28.4% |
| alibabaBlock_532_1M | alibabaBlock_1M | f100 (+fr) | 0.2392 | 0.3696 | +54.5% |
| alibabaBlock_544_1M | alibabaBlock_1M | f010 (+fs) | 0.2910 | 0.3697 | +27.1% |
| alibabaBlock_544_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2910 | 0.3697 | +27.1% |
| alibabaBlock_547_1M | alibabaBlock_1M | f010 (+fs) | 0.0632 | 0.0865 | +37.0% |
| alibabaBlock_547_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0632 | 0.0826 | +30.7% |
| alibabaBlock_548_100K | alibabaBlock_100K | f010 (+fs) | 0.1339 | 0.1756 | +31.1% |
| alibabaBlock_548_100K | alibabaBlock_100K | f011 (+fs+rs) | 0.1339 | 0.1755 | +31.0% |
| alibabaBlock_548_100K | alibabaBlock_100K | f100 (+fr) | 0.1339 | 0.1783 | +33.1% |
| alibabaBlock_548_100K | alibabaBlock_100K | f101 (+fr+rs) | 0.1339 | 0.1760 | +31.4% |
| alibabaBlock_548_100K | alibabaBlock_100K | f110 (+fr+fs) | 0.1339 | 0.1744 | +30.2% |
| alibabaBlock_548_100K | alibabaBlock_100K | f111 (all) | 0.1339 | 0.1746 | +30.4% |
| alibabaBlock_550_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1032 | 0.1247 | +20.9% |
| alibabaBlock_550_1M | alibabaBlock_1M | f100 (+fr) | 0.1032 | 0.1642 | +59.1% |
| alibabaBlock_550_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1032 | 0.1301 | +26.1% |
| alibabaBlock_550_1M | alibabaBlock_1M | f111 (all) | 0.1032 | 0.1261 | +22.2% |
| alibabaBlock_551_100K | alibabaBlock_100K | f010 (+fs) | 0.1830 | 0.2268 | +23.9% |
| alibabaBlock_551_100K | alibabaBlock_100K | f011 (+fs+rs) | 0.1830 | 0.2268 | +23.9% |
| alibabaBlock_551_100K | alibabaBlock_100K | f110 (+fr+fs) | 0.1830 | 0.2266 | +23.8% |
| alibabaBlock_551_100K | alibabaBlock_100K | f111 (all) | 0.1830 | 0.2267 | +23.9% |
| alibabaBlock_554_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1040 | 0.1288 | +23.8% |
| alibabaBlock_554_1M | alibabaBlock_1M | f100 (+fr) | 0.1040 | 0.3169 | +204.7% |
| alibabaBlock_554_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1040 | 0.1300 | +25.0% |
| alibabaBlock_554_1M | alibabaBlock_1M | f111 (all) | 0.1040 | 0.1284 | +23.4% |
| alibabaBlock_556_new | alibabaBlock_new | f010 (+fs) | 0.0850 | 0.2070 | +143.4% |
| alibabaBlock_556_new | alibabaBlock_new | f011 (+fs+rs) | 0.0850 | 0.2067 | +143.1% |
| alibabaBlock_556_new | alibabaBlock_new | f110 (+fr+fs) | 0.0850 | 0.2027 | +138.3% |
| alibabaBlock_556_new | alibabaBlock_new | f111 (all) | 0.0850 | 0.2024 | +138.0% |
| alibabaBlock_558_1M | alibabaBlock_1M | f010 (+fs) | 0.1202 | 0.3394 | +182.3% |
| alibabaBlock_558_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1202 | 0.3392 | +182.1% |
| alibabaBlock_558_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1202 | 0.2497 | +107.6% |
| alibabaBlock_558_1M | alibabaBlock_1M | f111 (all) | 0.1202 | 0.3281 | +172.9% |
| alibabaBlock_560_100K | alibabaBlock_100K | f001 (+rs) | 0.2907 | 0.4126 | +41.9% |
| alibabaBlock_568_1M | alibabaBlock_1M | f010 (+fs) | 0.2680 | 0.3708 | +38.4% |
| alibabaBlock_568_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2680 | 0.3709 | +38.4% |
| alibabaBlock_568_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2680 | 0.3345 | +24.8% |
| alibabaBlock_568_1M | alibabaBlock_1M | f111 (all) | 0.2680 | 0.3307 | +23.4% |
| alibabaBlock_569_1M | alibabaBlock_1M | f010 (+fs) | 0.2681 | 0.3279 | +22.3% |
| alibabaBlock_569_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2681 | 0.3281 | +22.4% |
| alibabaBlock_569_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2681 | 0.3270 | +21.9% |
| alibabaBlock_569_1M | alibabaBlock_1M | f111 (all) | 0.2681 | 0.3266 | +21.8% |
| alibabaBlock_56_new | alibabaBlock_new | f010 (+fs) | 0.0926 | 0.3123 | +237.4% |
| alibabaBlock_56_new | alibabaBlock_new | f011 (+fs+rs) | 0.0926 | 0.3107 | +235.7% |
| alibabaBlock_56_new | alibabaBlock_new | f110 (+fr+fs) | 0.0926 | 0.2339 | +152.7% |
| alibabaBlock_56_new | alibabaBlock_new | f111 (all) | 0.0926 | 0.2338 | +152.6% |
| alibabaBlock_578_1M | alibabaBlock_1M | f010 (+fs) | 0.1402 | 0.2804 | +100.0% |
| alibabaBlock_578_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1402 | 0.2804 | +100.0% |
| alibabaBlock_578_1M | alibabaBlock_1M | f100 (+fr) | 0.1402 | 0.1737 | +23.9% |
| alibabaBlock_578_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1402 | 0.2698 | +92.5% |
| alibabaBlock_578_1M | alibabaBlock_1M | f111 (all) | 0.1402 | 0.2703 | +92.8% |
| alibabaBlock_579_1M | alibabaBlock_1M | f010 (+fs) | 0.1148 | 0.1837 | +60.0% |
| alibabaBlock_579_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1148 | 0.1837 | +60.0% |
| alibabaBlock_579_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1148 | 0.1818 | +58.4% |
| alibabaBlock_579_1M | alibabaBlock_1M | f111 (all) | 0.1148 | 0.1821 | +58.6% |
| alibabaBlock_585_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.1527 | 0.2152 | +41.0% |
| alibabaBlock_588_1M | alibabaBlock_1M | f010 (+fs) | 0.2803 | 0.3686 | +31.5% |
| alibabaBlock_588_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2803 | 0.3686 | +31.5% |
| alibabaBlock_589_100K | alibabaBlock_100K | f100 (+fr) | 0.3593 | 0.4406 | +22.6% |
| alibabaBlock_590_1M | alibabaBlock_1M | f010 (+fs) | 0.1148 | 0.1854 | +61.5% |
| alibabaBlock_590_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1148 | 0.1859 | +61.8% |
| alibabaBlock_590_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1148 | 0.1798 | +56.6% |
| alibabaBlock_590_1M | alibabaBlock_1M | f111 (all) | 0.1148 | 0.1821 | +58.6% |
| alibabaBlock_596_100K | alibabaBlock_100K | f100 (+fr) | 0.1518 | 0.2154 | +41.9% |
| alibabaBlock_596_100K | alibabaBlock_100K | f101 (+fr+rs) | 0.1518 | 0.1833 | +20.8% |
| alibabaBlock_5_new | alibabaBlock_new | f010 (+fs) | 0.0830 | 0.1995 | +140.5% |
| alibabaBlock_5_new | alibabaBlock_new | f011 (+fs+rs) | 0.0830 | 0.1995 | +140.5% |
| alibabaBlock_5_new | alibabaBlock_new | f110 (+fr+fs) | 0.0830 | 0.1933 | +133.0% |
| alibabaBlock_5_new | alibabaBlock_new | f111 (all) | 0.0830 | 0.1951 | +135.2% |
| alibabaBlock_603_1M | alibabaBlock_1M | f010 (+fs) | 0.0678 | 0.1368 | +101.8% |
| alibabaBlock_603_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0678 | 0.1367 | +101.7% |
| alibabaBlock_603_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0678 | 0.1368 | +101.9% |
| alibabaBlock_603_1M | alibabaBlock_1M | f111 (all) | 0.0678 | 0.1341 | +97.9% |
| alibabaBlock_606_1M | alibabaBlock_1M | f001 (+rs) | 0.1423 | 0.1965 | +38.0% |
| alibabaBlock_606_1M | alibabaBlock_1M | f100 (+fr) | 0.1423 | 0.1878 | +31.9% |
| alibabaBlock_613_1M | alibabaBlock_1M | f010 (+fs) | 0.2778 | 0.3692 | +32.9% |
| alibabaBlock_613_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2778 | 0.3691 | +32.9% |
| alibabaBlock_616_1M | alibabaBlock_1M | f010 (+fs) | 0.2765 | 0.3568 | +29.0% |
| alibabaBlock_616_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2765 | 0.3568 | +29.0% |
| alibabaBlock_618_1M | alibabaBlock_1M | f010 (+fs) | 0.0978 | 0.1492 | +52.6% |
| alibabaBlock_618_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0978 | 0.1491 | +52.5% |
| alibabaBlock_618_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0978 | 0.1503 | +53.7% |
| alibabaBlock_618_1M | alibabaBlock_1M | f111 (all) | 0.0978 | 0.1497 | +53.1% |
| alibabaBlock_621_1M | alibabaBlock_1M | f010 (+fs) | 0.0963 | 0.2091 | +117.2% |
| alibabaBlock_621_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0963 | 0.2088 | +116.9% |
| alibabaBlock_621_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.0963 | 0.1295 | +34.5% |
| alibabaBlock_621_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0963 | 0.2056 | +113.6% |
| alibabaBlock_621_1M | alibabaBlock_1M | f111 (all) | 0.0963 | 0.2058 | +113.7% |
| alibabaBlock_622_1M | alibabaBlock_1M | f010 (+fs) | 0.2642 | 0.3285 | +24.3% |
| alibabaBlock_622_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2642 | 0.3283 | +24.3% |
| alibabaBlock_622_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2642 | 0.3204 | +21.3% |
| alibabaBlock_622_1M | alibabaBlock_1M | f111 (all) | 0.2642 | 0.3212 | +21.6% |
| alibabaBlock_624_1M | alibabaBlock_1M | f010 (+fs) | 0.2722 | 0.3439 | +26.4% |
| alibabaBlock_624_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2722 | 0.3446 | +26.6% |
| alibabaBlock_624_1M | alibabaBlock_1M | f100 (+fr) | 0.2722 | 0.4206 | +54.5% |
| alibabaBlock_624_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.2722 | 0.3526 | +29.6% |
| alibabaBlock_624_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2722 | 0.3498 | +28.5% |
| alibabaBlock_624_1M | alibabaBlock_1M | f111 (all) | 0.2722 | 0.3399 | +24.9% |
| alibabaBlock_627_1M | alibabaBlock_1M | f010 (+fs) | 0.0805 | 0.2133 | +165.0% |
| alibabaBlock_627_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0805 | 0.2131 | +164.8% |
| alibabaBlock_627_1M | alibabaBlock_1M | f100 (+fr) | 0.0805 | 0.1078 | +33.9% |
| alibabaBlock_627_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.0805 | 0.0999 | +24.1% |
| alibabaBlock_627_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0805 | 0.2126 | +164.2% |
| alibabaBlock_627_1M | alibabaBlock_1M | f111 (all) | 0.0805 | 0.2074 | +157.8% |
| alibabaBlock_62_new | alibabaBlock_new | f010 (+fs) | 0.0890 | 0.2817 | +216.5% |
| alibabaBlock_62_new | alibabaBlock_new | f011 (+fs+rs) | 0.0890 | 0.2809 | +215.6% |
| alibabaBlock_62_new | alibabaBlock_new | f110 (+fr+fs) | 0.0890 | 0.1470 | +65.2% |
| alibabaBlock_62_new | alibabaBlock_new | f111 (all) | 0.0890 | 0.1515 | +70.2% |
| alibabaBlock_634_1M | alibabaBlock_1M | f100 (+fr) | 0.2986 | 0.3584 | +20.0% |
| alibabaBlock_638_100K | alibabaBlock_100K | f010 (+fs) | 0.2376 | 0.2926 | +23.1% |
| alibabaBlock_638_100K | alibabaBlock_100K | f011 (+fs+rs) | 0.2376 | 0.2926 | +23.1% |
| alibabaBlock_638_100K | alibabaBlock_100K | f110 (+fr+fs) | 0.2376 | 0.2921 | +22.9% |
| alibabaBlock_638_100K | alibabaBlock_100K | f111 (all) | 0.2376 | 0.2921 | +22.9% |
| alibabaBlock_641_1M | alibabaBlock_1M | f010 (+fs) | 0.2551 | 0.3209 | +25.8% |
| alibabaBlock_641_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2551 | 0.3210 | +25.8% |
| alibabaBlock_641_1M | alibabaBlock_1M | f100 (+fr) | 0.2551 | 0.3663 | +43.6% |
| alibabaBlock_641_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2551 | 0.3214 | +26.0% |
| alibabaBlock_641_1M | alibabaBlock_1M | f111 (all) | 0.2551 | 0.3213 | +25.9% |
| alibabaBlock_645_100K | alibabaBlock_100K | f010 (+fs) | 0.1576 | 0.1905 | +20.9% |
| alibabaBlock_645_100K | alibabaBlock_100K | f011 (+fs+rs) | 0.1576 | 0.1904 | +20.8% |
| alibabaBlock_645_100K | alibabaBlock_100K | f110 (+fr+fs) | 0.1576 | 0.1905 | +20.9% |
| alibabaBlock_645_100K | alibabaBlock_100K | f111 (all) | 0.1576 | 0.1905 | +20.8% |
| alibabaBlock_649_1M | alibabaBlock_1M | f010 (+fs) | 0.2840 | 0.3942 | +38.8% |
| alibabaBlock_649_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2840 | 0.3942 | +38.8% |
| alibabaBlock_649_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2840 | 0.3491 | +22.9% |
| alibabaBlock_64_1M | alibabaBlock_1M | f010 (+fs) | 0.0711 | 0.1588 | +123.3% |
| alibabaBlock_64_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0711 | 0.1444 | +103.1% |
| alibabaBlock_64_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0711 | 0.1269 | +78.5% |
| alibabaBlock_64_1M | alibabaBlock_1M | f111 (all) | 0.0711 | 0.1285 | +80.8% |
| alibabaBlock_650_1M | alibabaBlock_1M | f010 (+fs) | 0.1065 | 0.1486 | +39.6% |
| alibabaBlock_650_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1065 | 0.1496 | +40.5% |
| alibabaBlock_651_new | alibabaBlock_new | f010 (+fs) | 0.1044 | 0.2138 | +104.8% |
| alibabaBlock_651_new | alibabaBlock_new | f011 (+fs+rs) | 0.1044 | 0.2134 | +104.4% |
| alibabaBlock_651_new | alibabaBlock_new | f110 (+fr+fs) | 0.1044 | 0.2123 | +103.3% |
| alibabaBlock_651_new | alibabaBlock_new | f111 (all) | 0.1044 | 0.2122 | +103.3% |
| alibabaBlock_652_100K | alibabaBlock_100K | f010 (+fs) | 0.2402 | 0.3276 | +36.4% |
| alibabaBlock_652_100K | alibabaBlock_100K | f011 (+fs+rs) | 0.2402 | 0.3278 | +36.5% |
| alibabaBlock_652_100K | alibabaBlock_100K | f110 (+fr+fs) | 0.2402 | 0.3161 | +31.6% |
| alibabaBlock_652_100K | alibabaBlock_100K | f111 (all) | 0.2402 | 0.3146 | +31.0% |
| alibabaBlock_653_1M | alibabaBlock_1M | f010 (+fs) | 0.0958 | 0.1318 | +37.6% |
| alibabaBlock_653_1M | alibabaBlock_1M | f100 (+fr) | 0.0958 | 0.1357 | +41.6% |
| alibabaBlock_653_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.0958 | 0.1197 | +24.9% |
| alibabaBlock_653_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0958 | 0.1163 | +21.4% |
| alibabaBlock_655_1M | alibabaBlock_1M | f100 (+fr) | 0.2370 | 0.3832 | +61.7% |
| alibabaBlock_655_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.2370 | 0.2953 | +24.6% |
| alibabaBlock_657_1M | alibabaBlock_1M | f010 (+fs) | 0.2412 | 0.2944 | +22.1% |
| alibabaBlock_657_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2412 | 0.2943 | +22.1% |
| alibabaBlock_657_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2412 | 0.2941 | +22.0% |
| alibabaBlock_657_1M | alibabaBlock_1M | f111 (all) | 0.2412 | 0.2941 | +22.0% |
| alibabaBlock_658_1M | alibabaBlock_1M | f010 (+fs) | 0.2627 | 0.3423 | +30.3% |
| alibabaBlock_658_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2627 | 0.3424 | +30.3% |
| alibabaBlock_658_1M | alibabaBlock_1M | f100 (+fr) | 0.2627 | 0.3269 | +24.4% |
| alibabaBlock_658_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.2627 | 0.3243 | +23.4% |
| alibabaBlock_658_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2627 | 0.3408 | +29.7% |
| alibabaBlock_658_1M | alibabaBlock_1M | f111 (all) | 0.2627 | 0.3403 | +29.5% |
| alibabaBlock_659_1M | alibabaBlock_1M | f010 (+fs) | 0.3271 | 0.3962 | +21.1% |
| alibabaBlock_659_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.3271 | 0.3962 | +21.1% |
| alibabaBlock_661_new | alibabaBlock_new | f010 (+fs) | 0.0768 | 0.1429 | +86.1% |
| alibabaBlock_661_new | alibabaBlock_new | f011 (+fs+rs) | 0.0768 | 0.1432 | +86.5% |
| alibabaBlock_661_new | alibabaBlock_new | f110 (+fr+fs) | 0.0768 | 0.1351 | +76.0% |
| alibabaBlock_661_new | alibabaBlock_new | f111 (all) | 0.0768 | 0.1362 | +77.4% |
| alibabaBlock_663_new | alibabaBlock_new | f010 (+fs) | 0.0848 | 0.2060 | +143.0% |
| alibabaBlock_663_new | alibabaBlock_new | f011 (+fs+rs) | 0.0848 | 0.2061 | +143.1% |
| alibabaBlock_663_new | alibabaBlock_new | f110 (+fr+fs) | 0.0848 | 0.1995 | +135.3% |
| alibabaBlock_663_new | alibabaBlock_new | f111 (all) | 0.0848 | 0.1993 | +135.2% |
| alibabaBlock_666_1M | alibabaBlock_1M | f010 (+fs) | 0.0691 | 0.1346 | +94.7% |
| alibabaBlock_666_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0691 | 0.1346 | +94.7% |
| alibabaBlock_666_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0691 | 0.1340 | +93.8% |
| alibabaBlock_666_1M | alibabaBlock_1M | f111 (all) | 0.0691 | 0.1342 | +94.1% |
| alibabaBlock_667_1M | alibabaBlock_1M | f100 (+fr) | 0.1065 | 0.1408 | +32.2% |
| alibabaBlock_669_100K | alibabaBlock_100K | f010 (+fs) | 0.1384 | 0.1744 | +26.0% |
| alibabaBlock_669_100K | alibabaBlock_100K | f011 (+fs+rs) | 0.1384 | 0.1751 | +26.6% |
| alibabaBlock_669_100K | alibabaBlock_100K | f110 (+fr+fs) | 0.1384 | 0.1741 | +25.8% |
| alibabaBlock_669_100K | alibabaBlock_100K | f111 (all) | 0.1384 | 0.1732 | +25.2% |
| alibabaBlock_66_new | alibabaBlock_new | f010 (+fs) | 0.0905 | 0.2873 | +217.4% |
| alibabaBlock_66_new | alibabaBlock_new | f011 (+fs+rs) | 0.0905 | 0.2874 | +217.5% |
| alibabaBlock_66_new | alibabaBlock_new | f110 (+fr+fs) | 0.0905 | 0.1386 | +53.1% |
| alibabaBlock_66_new | alibabaBlock_new | f111 (all) | 0.0905 | 0.1343 | +48.4% |
| alibabaBlock_670_1M | alibabaBlock_1M | f010 (+fs) | 0.1349 | 0.2949 | +118.6% |
| alibabaBlock_670_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1349 | 0.2957 | +119.2% |
| alibabaBlock_670_1M | alibabaBlock_1M | f100 (+fr) | 0.1349 | 0.2334 | +73.0% |
| alibabaBlock_670_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.1349 | 0.1734 | +28.5% |
| alibabaBlock_670_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1349 | 0.2909 | +115.6% |
| alibabaBlock_670_1M | alibabaBlock_1M | f111 (all) | 0.1349 | 0.2859 | +111.9% |
| alibabaBlock_671_100K | alibabaBlock_100K | f010 (+fs) | 0.3353 | 0.4537 | +35.3% |
| alibabaBlock_671_100K | alibabaBlock_100K | f011 (+fs+rs) | 0.3353 | 0.4537 | +35.3% |
| alibabaBlock_671_100K | alibabaBlock_100K | f110 (+fr+fs) | 0.3353 | 0.4533 | +35.2% |
| alibabaBlock_671_100K | alibabaBlock_100K | f111 (all) | 0.3353 | 0.4535 | +35.2% |
| alibabaBlock_672_1M | alibabaBlock_1M | f010 (+fs) | 0.2196 | 0.2715 | +23.6% |
| alibabaBlock_672_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2196 | 0.2715 | +23.6% |
| alibabaBlock_674_1M | alibabaBlock_1M | f010 (+fs) | 0.0807 | 0.2151 | +166.4% |
| alibabaBlock_674_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0807 | 0.2150 | +166.4% |
| alibabaBlock_674_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.0807 | 0.0985 | +22.0% |
| alibabaBlock_674_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0807 | 0.2112 | +161.7% |
| alibabaBlock_674_1M | alibabaBlock_1M | f111 (all) | 0.0807 | 0.2091 | +159.1% |
| alibabaBlock_679_new | alibabaBlock_new | f010 (+fs) | 0.0249 | 0.0762 | +206.5% |
| alibabaBlock_679_new | alibabaBlock_new | f011 (+fs+rs) | 0.0249 | 0.0762 | +206.5% |
| alibabaBlock_679_new | alibabaBlock_new | f110 (+fr+fs) | 0.0249 | 0.0761 | +205.9% |
| alibabaBlock_679_new | alibabaBlock_new | f111 (all) | 0.0249 | 0.0761 | +205.9% |
| alibabaBlock_68_new | alibabaBlock_new | f010 (+fs) | 0.0453 | 0.1793 | +296.0% |
| alibabaBlock_68_new | alibabaBlock_new | f011 (+fs+rs) | 0.0453 | 0.1792 | +295.8% |
| alibabaBlock_68_new | alibabaBlock_new | f110 (+fr+fs) | 0.0453 | 0.1553 | +243.1% |
| alibabaBlock_68_new | alibabaBlock_new | f111 (all) | 0.0453 | 0.1548 | +242.0% |
| alibabaBlock_693_1M | alibabaBlock_1M | f010 (+fs) | 0.0983 | 0.1595 | +62.2% |
| alibabaBlock_693_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0983 | 0.1595 | +62.2% |
| alibabaBlock_693_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0983 | 0.1594 | +62.1% |
| alibabaBlock_693_1M | alibabaBlock_1M | f111 (all) | 0.0983 | 0.1572 | +59.8% |
| alibabaBlock_695_1M | alibabaBlock_1M | f010 (+fs) | 0.1156 | 0.1764 | +52.5% |
| alibabaBlock_695_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1156 | 0.1764 | +52.5% |
| alibabaBlock_695_1M | alibabaBlock_1M | f100 (+fr) | 0.1156 | 0.2179 | +88.4% |
| alibabaBlock_695_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1156 | 0.1632 | +41.1% |
| alibabaBlock_695_1M | alibabaBlock_1M | f111 (all) | 0.1156 | 0.1672 | +44.6% |
| alibabaBlock_698_100K | alibabaBlock_100K | f100 (+fr) | 0.1944 | 0.2363 | +21.5% |
| alibabaBlock_69_new | alibabaBlock_new | f010 (+fs) | 0.0849 | 0.1991 | +134.4% |
| alibabaBlock_69_new | alibabaBlock_new | f011 (+fs+rs) | 0.0849 | 0.1993 | +134.7% |
| alibabaBlock_69_new | alibabaBlock_new | f110 (+fr+fs) | 0.0849 | 0.1929 | +127.1% |
| alibabaBlock_69_new | alibabaBlock_new | f111 (all) | 0.0849 | 0.1958 | +130.6% |
| alibabaBlock_700_1M | alibabaBlock_1M | f010 (+fs) | 0.1276 | 0.1591 | +24.7% |
| alibabaBlock_700_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1276 | 0.1587 | +24.3% |
| alibabaBlock_700_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1276 | 0.1582 | +24.0% |
| alibabaBlock_700_1M | alibabaBlock_1M | f111 (all) | 0.1276 | 0.1551 | +21.6% |
| alibabaBlock_704_1M | alibabaBlock_1M | f001 (+rs) | 0.0963 | 0.1316 | +36.6% |
| alibabaBlock_704_1M | alibabaBlock_1M | f100 (+fr) | 0.0963 | 0.2426 | +151.9% |
| alibabaBlock_704_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.0963 | 0.1486 | +54.3% |
| alibabaBlock_705_100K | alibabaBlock_100K | f010 (+fs) | 0.3247 | 0.4230 | +30.3% |
| alibabaBlock_705_100K | alibabaBlock_100K | f011 (+fs+rs) | 0.3247 | 0.4231 | +30.3% |
| alibabaBlock_705_100K | alibabaBlock_100K | f110 (+fr+fs) | 0.3247 | 0.4219 | +29.9% |
| alibabaBlock_705_100K | alibabaBlock_100K | f111 (all) | 0.3247 | 0.4218 | +29.9% |
| alibabaBlock_707_1M | alibabaBlock_1M | f010 (+fs) | 0.2761 | 0.3590 | +30.0% |
| alibabaBlock_707_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2761 | 0.3590 | +30.0% |
| alibabaBlock_710_1M | alibabaBlock_1M | f010 (+fs) | 0.0847 | 0.1130 | +33.4% |
| alibabaBlock_710_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0847 | 0.1130 | +33.4% |
| alibabaBlock_710_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.0847 | 0.1048 | +23.7% |
| alibabaBlock_711_1M | alibabaBlock_1M | f010 (+fs) | 0.2798 | 0.3444 | +23.1% |
| alibabaBlock_711_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.2798 | 0.3446 | +23.1% |
| alibabaBlock_711_1M | alibabaBlock_1M | f100 (+fr) | 0.2798 | 0.3647 | +30.3% |
| alibabaBlock_711_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.2798 | 0.3419 | +22.2% |
| alibabaBlock_711_1M | alibabaBlock_1M | f111 (all) | 0.2798 | 0.3422 | +22.3% |
| alibabaBlock_715_100K | alibabaBlock_100K | f010 (+fs) | 0.2119 | 0.3544 | +67.3% |
| alibabaBlock_715_100K | alibabaBlock_100K | f011 (+fs+rs) | 0.2119 | 0.3545 | +67.3% |
| alibabaBlock_715_100K | alibabaBlock_100K | f110 (+fr+fs) | 0.2119 | 0.3188 | +50.5% |
| alibabaBlock_715_100K | alibabaBlock_100K | f111 (all) | 0.2119 | 0.3184 | +50.3% |
| alibabaBlock_716_1M | alibabaBlock_1M | f001 (+rs) | 0.0370 | 0.0451 | +21.9% |
| alibabaBlock_716_1M | alibabaBlock_1M | f100 (+fr) | 0.0370 | 0.0446 | +20.6% |
| alibabaBlock_721_1M | alibabaBlock_1M | f001 (+rs) | 0.0402 | 0.0543 | +35.0% |
| alibabaBlock_721_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0402 | 0.0488 | +21.4% |
| alibabaBlock_721_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.0402 | 0.0718 | +78.6% |
| alibabaBlock_72_new | alibabaBlock_new | f010 (+fs) | 0.0895 | 0.3044 | +239.9% |
| alibabaBlock_72_new | alibabaBlock_new | f011 (+fs+rs) | 0.0895 | 0.3031 | +238.6% |
| alibabaBlock_72_new | alibabaBlock_new | f110 (+fr+fs) | 0.0895 | 0.1421 | +58.7% |
| alibabaBlock_72_new | alibabaBlock_new | f111 (all) | 0.0895 | 0.1378 | +53.9% |
| alibabaBlock_732_100K | alibabaBlock_100K | f010 (+fs) | 0.1505 | 0.2322 | +54.3% |
| alibabaBlock_732_100K | alibabaBlock_100K | f011 (+fs+rs) | 0.1505 | 0.2326 | +54.5% |
| alibabaBlock_732_100K | alibabaBlock_100K | f100 (+fr) | 0.1505 | 0.2120 | +40.9% |
| alibabaBlock_732_100K | alibabaBlock_100K | f110 (+fr+fs) | 0.1505 | 0.2328 | +54.7% |
| alibabaBlock_732_100K | alibabaBlock_100K | f111 (all) | 0.1505 | 0.2333 | +55.0% |
| alibabaBlock_734_1M | alibabaBlock_1M | f001 (+rs) | 0.0820 | 0.1089 | +32.8% |
| alibabaBlock_734_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.0820 | 0.1100 | +34.1% |
| alibabaBlock_734_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0820 | 0.1084 | +32.2% |
| alibabaBlock_735_100K | alibabaBlock_100K | f010 (+fs) | 0.1392 | 0.2587 | +85.8% |
| alibabaBlock_735_100K | alibabaBlock_100K | f011 (+fs+rs) | 0.1392 | 0.2582 | +85.5% |
| alibabaBlock_735_100K | alibabaBlock_100K | f110 (+fr+fs) | 0.1392 | 0.2540 | +82.4% |
| alibabaBlock_735_100K | alibabaBlock_100K | f111 (all) | 0.1392 | 0.2595 | +86.4% |
| alibabaBlock_738_1M | alibabaBlock_1M | f010 (+fs) | 0.1190 | 0.1570 | +31.9% |
| alibabaBlock_738_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1190 | 0.1566 | +31.6% |
| alibabaBlock_738_1M | alibabaBlock_1M | f100 (+fr) | 0.1190 | 0.1464 | +23.0% |
| alibabaBlock_738_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1190 | 0.1612 | +35.4% |
| alibabaBlock_738_1M | alibabaBlock_1M | f111 (all) | 0.1190 | 0.1540 | +29.4% |
| alibabaBlock_740_new | alibabaBlock_new | f010 (+fs) | 0.0954 | 0.1389 | +45.7% |
| alibabaBlock_740_new | alibabaBlock_new | f011 (+fs+rs) | 0.0954 | 0.1389 | +45.7% |
| alibabaBlock_740_new | alibabaBlock_new | f110 (+fr+fs) | 0.0954 | 0.1388 | +45.6% |
| alibabaBlock_740_new | alibabaBlock_new | f111 (all) | 0.0954 | 0.1383 | +45.1% |
| alibabaBlock_744_1M | alibabaBlock_1M | f100 (+fr) | 0.5394 | 0.6486 | +20.3% |
| alibabaBlock_750_1M | alibabaBlock_1M | f010 (+fs) | 0.1016 | 0.1932 | +90.1% |
| alibabaBlock_750_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1016 | 0.1939 | +90.8% |
| alibabaBlock_750_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1016 | 0.1844 | +81.4% |
| alibabaBlock_750_1M | alibabaBlock_1M | f111 (all) | 0.1016 | 0.1846 | +81.7% |
| alibabaBlock_76_new | alibabaBlock_new | f010 (+fs) | 0.0853 | 0.2761 | +223.8% |
| alibabaBlock_76_new | alibabaBlock_new | f011 (+fs+rs) | 0.0853 | 0.2768 | +224.6% |
| alibabaBlock_76_new | alibabaBlock_new | f110 (+fr+fs) | 0.0853 | 0.1433 | +68.1% |
| alibabaBlock_76_new | alibabaBlock_new | f111 (all) | 0.0853 | 0.1448 | +69.8% |
| alibabaBlock_772_1M | alibabaBlock_1M | f010 (+fs) | 0.1832 | 0.2277 | +24.2% |
| alibabaBlock_772_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1832 | 0.2276 | +24.2% |
| alibabaBlock_774_1M | alibabaBlock_1M | f010 (+fs) | 0.1271 | 0.1716 | +35.0% |
| alibabaBlock_774_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.1271 | 0.1716 | +35.0% |
| alibabaBlock_774_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.1271 | 0.1612 | +26.8% |
| alibabaBlock_774_1M | alibabaBlock_1M | f111 (all) | 0.1271 | 0.1644 | +29.3% |
| alibabaBlock_77_new | alibabaBlock_new | f010 (+fs) | 0.0784 | 0.1068 | +36.2% |
| alibabaBlock_77_new | alibabaBlock_new | f011 (+fs+rs) | 0.0784 | 0.1100 | +40.3% |
| alibabaBlock_77_new | alibabaBlock_new | f111 (all) | 0.0784 | 0.0999 | +27.3% |
| alibabaBlock_787_100K | alibabaBlock_100K | f100 (+fr) | 0.1816 | 0.2193 | +20.7% |
| alibabaBlock_78_new | alibabaBlock_new | f010 (+fs) | 0.0870 | 0.2964 | +240.6% |
| alibabaBlock_78_new | alibabaBlock_new | f011 (+fs+rs) | 0.0870 | 0.2955 | +239.5% |
| alibabaBlock_78_new | alibabaBlock_new | f110 (+fr+fs) | 0.0870 | 0.1485 | +70.7% |
| alibabaBlock_78_new | alibabaBlock_new | f111 (all) | 0.0870 | 0.1518 | +74.4% |
| alibabaBlock_80_1M | alibabaBlock_1M | f010 (+fs) | 0.0943 | 0.1532 | +62.4% |
| alibabaBlock_80_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0943 | 0.1548 | +64.1% |
| alibabaBlock_80_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0943 | 0.1542 | +63.5% |
| alibabaBlock_80_1M | alibabaBlock_1M | f111 (all) | 0.0943 | 0.1541 | +63.3% |
| alibabaBlock_810_new | alibabaBlock_new | f110 (+fr+fs) | 0.4516 | 0.5437 | +20.4% |
| alibabaBlock_83_new | alibabaBlock_new | f010 (+fs) | 0.0921 | 0.2992 | +225.0% |
| alibabaBlock_83_new | alibabaBlock_new | f011 (+fs+rs) | 0.0921 | 0.3011 | +227.1% |
| alibabaBlock_83_new | alibabaBlock_new | f110 (+fr+fs) | 0.0921 | 0.2462 | +167.4% |
| alibabaBlock_83_new | alibabaBlock_new | f111 (all) | 0.0921 | 0.2478 | +169.1% |
| alibabaBlock_86_new | alibabaBlock_new | f010 (+fs) | 0.0953 | 0.2758 | +189.3% |
| alibabaBlock_86_new | alibabaBlock_new | f011 (+fs+rs) | 0.0953 | 0.2712 | +184.5% |
| alibabaBlock_86_new | alibabaBlock_new | f110 (+fr+fs) | 0.0953 | 0.1498 | +57.2% |
| alibabaBlock_86_new | alibabaBlock_new | f111 (all) | 0.0953 | 0.1414 | +48.3% |
| alibabaBlock_88_new | alibabaBlock_new | f010 (+fs) | 0.0927 | 0.2758 | +197.4% |
| alibabaBlock_88_new | alibabaBlock_new | f011 (+fs+rs) | 0.0927 | 0.2735 | +195.0% |
| alibabaBlock_88_new | alibabaBlock_new | f110 (+fr+fs) | 0.0927 | 0.2172 | +134.3% |
| alibabaBlock_88_new | alibabaBlock_new | f111 (all) | 0.0927 | 0.2170 | +134.1% |
| alibabaBlock_8_new | alibabaBlock_new | f010 (+fs) | 0.0899 | 0.2739 | +204.6% |
| alibabaBlock_8_new | alibabaBlock_new | f011 (+fs+rs) | 0.0899 | 0.2796 | +211.0% |
| alibabaBlock_8_new | alibabaBlock_new | f110 (+fr+fs) | 0.0899 | 0.1557 | +73.1% |
| alibabaBlock_8_new | alibabaBlock_new | f111 (all) | 0.0899 | 0.1557 | +73.2% |
| alibabaBlock_90_1M | alibabaBlock_1M | f010 (+fs) | 0.0644 | 0.1852 | +187.7% |
| alibabaBlock_90_1M | alibabaBlock_1M | f011 (+fs+rs) | 0.0644 | 0.1852 | +187.7% |
| alibabaBlock_90_1M | alibabaBlock_1M | f100 (+fr) | 0.0644 | 0.0871 | +35.2% |
| alibabaBlock_90_1M | alibabaBlock_1M | f101 (+fr+rs) | 0.0644 | 0.1032 | +60.3% |
| alibabaBlock_90_1M | alibabaBlock_1M | f110 (+fr+fs) | 0.0644 | 0.1845 | +186.6% |
| alibabaBlock_90_1M | alibabaBlock_1M | f111 (all) | 0.0644 | 0.1836 | +185.2% |
| alibabaBlock_91_new | alibabaBlock_new | f010 (+fs) | 0.0962 | 0.2853 | +196.5% |
| alibabaBlock_91_new | alibabaBlock_new | f011 (+fs+rs) | 0.0962 | 0.2851 | +196.4% |
| alibabaBlock_91_new | alibabaBlock_new | f110 (+fr+fs) | 0.0962 | 0.1490 | +54.9% |
| alibabaBlock_91_new | alibabaBlock_new | f111 (all) | 0.0962 | 0.1502 | +56.2% |
| alibabaBlock_92_new | alibabaBlock_new | f010 (+fs) | 0.0745 | 0.2734 | +267.2% |
| alibabaBlock_92_new | alibabaBlock_new | f011 (+fs+rs) | 0.0745 | 0.2716 | +264.8% |
| alibabaBlock_92_new | alibabaBlock_new | f110 (+fr+fs) | 0.0745 | 0.1517 | +103.7% |
| alibabaBlock_92_new | alibabaBlock_new | f111 (all) | 0.0745 | 0.1404 | +88.6% |
| w30 | cloudphysics | f010 (+fs) | 0.1268 | 0.1699 | +34.0% |
| w30 | cloudphysics | f011 (+fs+rs) | 0.1268 | 0.1566 | +23.6% |
| w30 | cloudphysics | f100 (+fr) | 0.1268 | 0.1652 | +30.3% |
| w30 | cloudphysics | f110 (+fr+fs) | 0.1268 | 0.1904 | +50.2% |
| w30 | cloudphysics | f111 (all) | 0.1268 | 0.1747 | +37.8% |
| w33 | cloudphysics | f010 (+fs) | 0.1566 | 0.4376 | +179.5% |
| w33 | cloudphysics | f011 (+fs+rs) | 0.1566 | 0.4377 | +179.6% |
| w33 | cloudphysics | f110 (+fr+fs) | 0.1566 | 0.4333 | +176.8% |
| w33 | cloudphysics | f111 (all) | 0.1566 | 0.4330 | +176.6% |
| w36 | cloudphysics | f010 (+fs) | 0.1462 | 0.4389 | +200.1% |
| w36 | cloudphysics | f011 (+fs+rs) | 0.1462 | 0.4391 | +200.3% |
| w36 | cloudphysics | f110 (+fr+fs) | 0.1462 | 0.4349 | +197.4% |
| w36 | cloudphysics | f111 (all) | 0.1462 | 0.4368 | +198.7% |
| w39 | cloudphysics | f010 (+fs) | 0.0820 | 0.5348 | +551.9% |
| w39 | cloudphysics | f011 (+fs+rs) | 0.0820 | 0.5348 | +552.0% |
| w39 | cloudphysics | f110 (+fr+fs) | 0.0820 | 0.5114 | +523.5% |
| w39 | cloudphysics | f111 (all) | 0.0820 | 0.5137 | +526.2% |
| w40 | cloudphysics | f010 (+fs) | 0.1115 | 0.4817 | +332.1% |
| w40 | cloudphysics | f011 (+fs+rs) | 0.1115 | 0.4815 | +331.9% |
| w40 | cloudphysics | f110 (+fr+fs) | 0.1115 | 0.4784 | +329.1% |
| w40 | cloudphysics | f111 (all) | 0.1115 | 0.4786 | +329.3% |
| w41 | cloudphysics | f010 (+fs) | 0.0677 | 0.2389 | +253.1% |
| w41 | cloudphysics | f011 (+fs+rs) | 0.0677 | 0.2396 | +254.0% |
| w41 | cloudphysics | f110 (+fr+fs) | 0.0677 | 0.2333 | +244.9% |
| w41 | cloudphysics | f111 (all) | 0.0677 | 0.2338 | +245.5% |
| w45 | cloudphysics | f010 (+fs) | 0.0808 | 0.5173 | +540.5% |
| w45 | cloudphysics | f011 (+fs+rs) | 0.0808 | 0.5174 | +540.7% |
| w45 | cloudphysics | f110 (+fr+fs) | 0.0808 | 0.5143 | +536.8% |
| w45 | cloudphysics | f111 (all) | 0.0808 | 0.5143 | +536.9% |
| w47 | cloudphysics | f010 (+fs) | 0.0697 | 0.3856 | +453.2% |
| w47 | cloudphysics | f011 (+fs+rs) | 0.0697 | 0.3856 | +453.2% |
| w47 | cloudphysics | f110 (+fr+fs) | 0.0697 | 0.3831 | +449.7% |
| w47 | cloudphysics | f111 (all) | 0.0697 | 0.3834 | +450.1% |
| w66 | cloudphysics | f100 (+fr) | 0.2321 | 0.2893 | +24.6% |

Total anomalies: 993
