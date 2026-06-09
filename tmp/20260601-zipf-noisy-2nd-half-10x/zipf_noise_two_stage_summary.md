# Two-stage Zipf + noise trace

- Stage 1 (base): Zipf normal workload
- Stage 2 (noise): post-injected noise requests

Trace: `/home/丁坤鹏/libcachesim_new/tmp/20260601-zipf-noisy-2nd-half-10x/zipf_noise_two_stage.csv`

Metadata: `/home/丁坤鹏/libcachesim_new/tmp/20260601-zipf-noisy-2nd-half-10x/zipf_noise_two_stage_metadata.csv`

## Parameters

- num_objects: 4096
- num_requests: 2000000
- alpha: 1.6
- obj_size: 4096
- noise_pool: 2048
- noise_every: 64
- noise_burst: 2
- noise_start_frac: 0.5
- seed: 20260529

## Request Mix

- base_zipf requests: 2000000
- noise requests: 31250
- total requests: 2031250
- noise ratio: 0.0154
