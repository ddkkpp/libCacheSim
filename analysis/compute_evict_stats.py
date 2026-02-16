#!/usr/bin/env python3
import sys
import numpy as np
from collections import Counter
p='analysis/evict_vals.txt'
try:
    with open(p) as f:
        vals=[int(x.strip()) for x in f if x.strip()]
except FileNotFoundError:
    print('File not found:', p)
    sys.exit(1)
if not vals:
    print('No values found in', p)
    sys.exit(0)
arr=np.array(vals)
out=[]
out.append(f"count={len(arr)}")
out.append(f"min={int(arr.min())}")
out.append(f"max={int(arr.max())}")
out.append(f"mean={arr.mean():.3f}")
out.append(f"median={int(np.median(arr))}")
for pctl in (50,75,90,95,99,99.9):
    out.append(f"p{pctl}={int(np.percentile(arr,pctl))}")
out.append('\nTop 20 largest evict_to_access values:')
for v in sorted(arr, reverse=True)[:20]:
    out.append(str(v))
# bucket counts
bins=[0,1,5,10,20,50,100,200,500,1000,2000,5000,10000,20000,50000,100000]
out.append('\nBucket counts:')
for i in range(1,len(bins)):
    low=bins[i-1]+1
    high=bins[i]
    cnt=((arr>=low)&(arr<=high)).sum()
    out.append(f'  ({low}-{high}): {cnt}')
# save
with open('analysis/evict_stats.txt','w') as fo:
    fo.write('\n'.join(out))
print('\n'.join(out))
print('\nSaved analysis/evict_stats.txt')
