# 20260423 Missing Baseline Coverage (auto-compound cache0001)

- total_missing_rows: 4313
- groups_with_missing: 3
- groups_without_missing: cloudphysics, metaCDN, tencentPhoto, wiki

## Global Missing Algorithms (affected trace count)
- LeCaR: 4126
- LRB-BMR: 379
- GLCache: 362
- Cacheus: 2
- GDSF: 2
- LHD: 2
- S3FIFO-0.1000-2: 2
- Sieve: 2
- ThreeLCache-BMR: 2
- WTinyLFU-w0.01-SLRU: 2
- ARC: 1
- LRU: 1

## Group Summary
- alibabaBlock: traces_with_missing=59
  - GLCache: 59
- cloudphysics: traces_with_missing=0
- metaCDN: traces_with_missing=0
- metaKV: traces_with_missing=2
  - ARC,Cacheus,GDSF,GLCache,LHD,LRB-BMR,LRU,LeCaR,S3FIFO-0.1000-2,Sieve,ThreeLCache-BMR,WTinyLFU-w0.01-SLRU: 1
  - Cacheus,GDSF,GLCache,LHD,LRB-BMR,LeCaR,S3FIFO-0.1000-2,Sieve,ThreeLCache-BMR,WTinyLFU-w0.01-SLRU: 1
- tencentBlock: traces_with_missing=4252
  - LeCaR: 3574
  - LRB-BMR,LeCaR: 377
  - GLCache,LeCaR: 173
  - GLCache: 128
- tencentPhoto: traces_with_missing=0
- wiki: traces_with_missing=0
