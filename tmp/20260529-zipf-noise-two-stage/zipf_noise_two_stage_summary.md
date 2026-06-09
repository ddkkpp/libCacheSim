# Two-stage Zipf + noise trace

- Stage 1 (base): Zipf normal workload
- Stage 2 (noise): post-injected noise requests

Trace: `tmp/20260529-zipf-noise-two-stage/zipf_noise_two_stage.csv`

Metadata: `tmp/20260529-zipf-noise-two-stage/zipf_noise_two_stage_metadata.csv`

## Parameters

- num_objects: 65536
- num_requests: 300000
- alpha: 1.1
- obj_size: 4096
- noise_pool: 32768
- noise_every: 64
- noise_burst: 8
- seed: 20260529

## Request Mix

- base_zipf requests: 300000
- noise requests: 37496
- total requests: 337496
- noise ratio: 0.1111
