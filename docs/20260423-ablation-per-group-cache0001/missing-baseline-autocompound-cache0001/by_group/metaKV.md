# metaKV missing baseline by trace

- traces_with_missing: 2

| trace | missing_mr | missing_bmr | missing_union |
|---|---|---|---|
| 202206_kv_traces_all | Cacheus,GDSF,GLCache,LHD,LeCaR,S3FIFO-0.1000-2,Sieve,WTinyLFU-w0.01-SLRU,LRB-BMR,ThreeLCache-BMR | Cacheus,GDSF,GLCache,LHD,LeCaR,S3FIFO-0.1000-2,Sieve,WTinyLFU-w0.01-SLRU,LRB-BMR,ThreeLCache-BMR | Cacheus,GDSF,GLCache,LHD,LRB-BMR,LeCaR,S3FIFO-0.1000-2,Sieve,ThreeLCache-BMR,WTinyLFU-w0.01-SLRU |
| 202210_kv_traces_all_sort | ARC,Cacheus,GDSF,GLCache,LHD,LRU,LeCaR,S3FIFO-0.1000-2,Sieve,WTinyLFU-w0.01-SLRU,LRB-BMR,ThreeLCache-BMR | ARC,Cacheus,GDSF,GLCache,LHD,LRU,LeCaR,S3FIFO-0.1000-2,Sieve,WTinyLFU-w0.01-SLRU,LRB-BMR,ThreeLCache-BMR | ARC,Cacheus,GDSF,GLCache,LHD,LRB-BMR,LRU,LeCaR,S3FIFO-0.1000-2,Sieve,ThreeLCache-BMR,WTinyLFU-w0.01-SLRU |
