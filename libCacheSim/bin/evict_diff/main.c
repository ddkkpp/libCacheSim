/**
 * evict_diff: 对比 GDSF 和 LOH 在同一 trace 上的 hit/miss 差异
 *
 * 对每个请求，记录:
 *   - 两者都 hit (common hit)
 *   - 两者都 miss (common miss)
 *   - LOH hit 但 GDSF miss (LOH-only hit)
 *   - GDSF hit 但 LOH miss (GDSF-only hit) ← 这是 LOH 需要改进的部分
 *
 * 对 "GDSF-only hit" 的对象，统计它们的特征分布（size/freq/age等）
 */

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "libCacheSim/cache.h"
#include "libCacheSim/evictionAlgo.h"
#include "libCacheSim/reader.h"
#include "utils/include/mymath.h"
#include "utils/include/mysys.h"

/* 统计桶 */
#define N_SIZE_BUCKETS 10
#define N_FREQ_BUCKETS 10

typedef struct {
  uint64_t common_hit;
  uint64_t common_miss;
  uint64_t gdsf_only_hit; /* GDSF hit, LOH miss */
  uint64_t loh_only_hit;  /* LOH hit, GDSF miss */
  uint64_t total_req;
  uint64_t total_byte;
  uint64_t gdsf_miss_byte;
  uint64_t loh_miss_byte;

  /* GDSF-only hit 的对象特征分布 */
  uint64_t gdsf_adv_size_hist[N_SIZE_BUCKETS]; /* 按 size 分桶 */
  uint64_t gdsf_adv_total_size;
  uint64_t gdsf_adv_total_freq; /* 累计 freq (用于算平均) */

  /* LOH-only hit 的对象特征分布 */
  uint64_t loh_adv_size_hist[N_SIZE_BUCKETS];
  uint64_t loh_adv_total_size;
  uint64_t loh_adv_total_freq;
} diff_stats_t;

static const uint64_t size_boundaries[] = {
    512, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216, 67108864};

static int size_to_bucket(uint64_t size) {
  for (int i = 0; i < N_SIZE_BUCKETS - 1; i++) {
    if (size <= size_boundaries[i]) return i;
  }
  return N_SIZE_BUCKETS - 1;
}

static const char *size_bucket_label(int i) {
  static const char *labels[] = {"<=512B",  "<=4KB", "<=16KB", "<=64KB",
                                 "<=256KB", "<=1MB", "<=4MB",  "<=16MB",
                                 "<=64MB",  ">64MB"};
  return labels[i];
}

int main(int argc, char *argv[]) {
  if (argc < 5) {
    fprintf(
        stderr,
        "Usage: %s <trace_path> <trace_type> <cache_size_or_ratio> <num_req>\n"
        "  trace_type: oracleGeneral etc.\n"
        "  cache_size_or_ratio: if < 1.0 treat as WSS ratio; if >= 1 treat as "
        "absolute bytes\n"
        "  num_req: max requests (0 = all)\n"
        "\n"
        "Environment vars:\n"
        "  LOH_FIXED_WEIGHTS, LOH_SCORE_USE_IRT, etc.\n",
        argv[0]);
    return 1;
  }

  const char *trace_path = argv[1];
  const char *trace_type_str = argv[2];
  double cache_size_arg = atof(argv[3]);
  int64_t max_req = atoll(argv[4]);

  /* Open reader to compute working set size */
  reader_init_param_t reader_params = {.obj_id_is_num = true};
  trace_type_e trace_type = ORACLE_GENERAL_TRACE;
  if (strcasecmp(trace_type_str, "csv") == 0) trace_type = CSV_TRACE;

  reader_t *reader = setup_reader(trace_path, trace_type, &reader_params);
  if (reader == NULL) {
    fprintf(stderr, "Cannot open trace: %s\n", trace_path);
    return 1;
  }

  /* Calculate working set size for cache_ratio */
  uint64_t wss_byte = 0;
  request_t *req = new_request();
  uint64_t total_req_count = 0;
  uint64_t cache_size;
  double cache_ratio;

  if (cache_size_arg >= 1.0) {
    /* Absolute cache size in bytes - skip WSS scan */
    cache_size = (uint64_t)cache_size_arg;
    cache_ratio = 0.0; /* unknown */
    fprintf(stderr,
            "Using absolute cache_size: %lu bytes (skipping WSS scan)\n",
            (unsigned long)cache_size);
  } else {
    /* Ratio mode - need to scan for WSS (limited to max_req, matching cachesim
     * behavior) */
    cache_ratio = cache_size_arg;

    /* Count how many requests to scan for WSS (same as cachesim's
     * cal_working_set_size) */
    int64_t wss_scan_limit = max_req > 0 ? max_req : 0; /* 0 means all */

    fprintf(stderr, "Scanning trace for WSS (limited to %ld requests)...\n",
            (long)wss_scan_limit);

    /* Apply same sampling logic as cachesim's cli_reader_utils.c */
    int scaling_factor = 1;
    if (reader->file_size > (int64_t)5 * 1024 * 1024 * 1024LL) {
      scaling_factor = 101;
    } else if (reader->file_size > (int64_t)1 * 1024 * 1024 * 1024LL) {
      scaling_factor = 11;
    }
    fprintf(stderr, "File size: %ld, sampling factor: %d\n",
            (long)reader->file_size, scaling_factor);

    /* Use hash table to count unique objects + total bytes */
    GHashTable *obj_sizes = g_hash_table_new(g_direct_hash, g_direct_equal);
    uint64_t unique_objs = 0;
    int64_t n_scanned = 0;
    while (read_one_req(reader, req) == 0 && req->valid) {
      n_scanned++;
      if (wss_scan_limit > 0 && n_scanned > wss_scan_limit) break;

      if (scaling_factor > 1 && req->obj_id % scaling_factor != 0) {
        continue;
      }

      gpointer key = GSIZE_TO_POINTER(req->obj_id);
      if (!g_hash_table_contains(obj_sizes, key)) {
        g_hash_table_insert(obj_sizes, key, GSIZE_TO_POINTER(req->obj_size));
        wss_byte += req->obj_size;
        unique_objs++;
      }
    }
    g_hash_table_destroy(obj_sizes);

    unique_objs *= scaling_factor;
    wss_byte *= scaling_factor;

    cache_size = (uint64_t)(wss_byte * cache_ratio);
    fprintf(stderr,
            "WSS (scanned %ld req, sample 1/%d): %lu bytes (%lu objects), "
            "cache_size: %lu bytes (ratio=%.2f)\n",
            (long)n_scanned, scaling_factor, (unsigned long)wss_byte,
            (unsigned long)unique_objs, (unsigned long)cache_size, cache_ratio);
  }

  /* Init two caches */
  common_cache_params_t cc_params = {
      .cache_size = cache_size,
      .default_ttl = 86400 * 300,
      .hashpower = 24,
      .consider_obj_metadata = false,
  };

  cache_t *cache_gdsf = GDSF_init(cc_params, NULL);
  cache_t *cache_loh = LOH_init(cc_params, "miss-ratio-weight=1.0");

  fprintf(stderr, "GDSF cache size: %lu, LOH cache size: %lu\n",
          (unsigned long)cache_gdsf->cache_size,
          (unsigned long)cache_loh->cache_size);

  /* Run simulation */
  diff_stats_t stats = {0};
  reset_reader(reader);
  uint64_t req_cnt = 0;

  while (read_one_req(reader, req) == 0 && req->valid) {
    if (max_req > 0 && (int64_t)req_cnt >= max_req) break;

    bool hit_gdsf = cache_gdsf->get(cache_gdsf, req);
    bool hit_loh = cache_loh->get(cache_loh, req);

    stats.total_req++;
    stats.total_byte += req->obj_size;

    if (hit_gdsf && hit_loh) {
      stats.common_hit++;
    } else if (!hit_gdsf && !hit_loh) {
      stats.common_miss++;
      stats.gdsf_miss_byte += req->obj_size;
      stats.loh_miss_byte += req->obj_size;
    } else if (hit_gdsf && !hit_loh) {
      stats.gdsf_only_hit++;
      stats.loh_miss_byte += req->obj_size;
      stats.gdsf_adv_size_hist[size_to_bucket(req->obj_size)]++;
      stats.gdsf_adv_total_size += req->obj_size;
      /* freq not directly available from request, skip for now */
    } else { /* hit_loh && !hit_gdsf */
      stats.loh_only_hit++;
      stats.gdsf_miss_byte += req->obj_size;
      stats.loh_adv_size_hist[size_to_bucket(req->obj_size)]++;
      stats.loh_adv_total_size += req->obj_size;
    }

    req_cnt++;
    if (req_cnt % 500000 == 0) {
      fprintf(stderr, "  processed %lu req, GDSF mr=%.4f, LOH mr=%.4f\n",
              (unsigned long)req_cnt,
              (double)(stats.common_miss + stats.loh_only_hit) / req_cnt,
              (double)(stats.common_miss + stats.gdsf_only_hit) / req_cnt);
    }
  }

  /* Print results */
  uint64_t gdsf_miss = stats.common_miss + stats.loh_only_hit;
  uint64_t loh_miss = stats.common_miss + stats.gdsf_only_hit;
  double gdsf_mr = (double)gdsf_miss / stats.total_req;
  double loh_mr = (double)loh_miss / stats.total_req;

  printf("=== GDSF vs LOH Eviction Diff Analysis ===\n");
  printf("Trace: %s\n", trace_path);
  printf("Total requests: %lu\n", (unsigned long)stats.total_req);
  printf("Cache size: %lu bytes (ratio=%.3f)\n", (unsigned long)cache_size,
         cache_ratio);
  printf("\n");

  printf("--- Hit/Miss Breakdown ---\n");
  printf("Common hit:      %10lu (%.4f)\n", (unsigned long)stats.common_hit,
         (double)stats.common_hit / stats.total_req);
  printf("Common miss:     %10lu (%.4f)\n", (unsigned long)stats.common_miss,
         (double)stats.common_miss / stats.total_req);
  printf("GDSF-only hit:   %10lu (%.4f) ← LOH 需要学习的\n",
         (unsigned long)stats.gdsf_only_hit,
         (double)stats.gdsf_only_hit / stats.total_req);
  printf("LOH-only hit:    %10lu (%.4f) ← LOH 的优势\n",
         (unsigned long)stats.loh_only_hit,
         (double)stats.loh_only_hit / stats.total_req);
  printf("\n");

  printf("--- Miss Ratio Comparison ---\n");
  printf("GDSF miss ratio: %.6f  (byte: %.6f)\n", gdsf_mr,
         (double)stats.gdsf_miss_byte / stats.total_byte);
  printf("LOH  miss ratio: %.6f  (byte: %.6f)\n", loh_mr,
         (double)stats.loh_miss_byte / stats.total_byte);
  printf("Gap (LOH - GDSF): %.6f  (%.1f%% relative)\n", loh_mr - gdsf_mr,
         (loh_mr - gdsf_mr) / gdsf_mr * 100.0);
  printf("\n");

  printf("--- GDSF-only Hit Object Size Distribution ---\n");
  printf("(These are requests GDSF serves but LOH misses)\n");
  for (int i = 0; i < N_SIZE_BUCKETS; i++) {
    if (stats.gdsf_adv_size_hist[i] > 0) {
      printf("  %10s: %8lu (%.2f%%)\n", size_bucket_label(i),
             (unsigned long)stats.gdsf_adv_size_hist[i],
             (double)stats.gdsf_adv_size_hist[i] / stats.gdsf_only_hit * 100.0);
    }
  }
  if (stats.gdsf_only_hit > 0) {
    printf("  Avg size: %.0f bytes\n",
           (double)stats.gdsf_adv_total_size / stats.gdsf_only_hit);
  }
  printf("\n");

  printf("--- LOH-only Hit Object Size Distribution ---\n");
  printf("(These are requests LOH serves but GDSF misses)\n");
  for (int i = 0; i < N_SIZE_BUCKETS; i++) {
    if (stats.loh_adv_size_hist[i] > 0) {
      printf("  %10s: %8lu (%.2f%%)\n", size_bucket_label(i),
             (unsigned long)stats.loh_adv_size_hist[i],
             (double)stats.loh_adv_size_hist[i] / stats.loh_only_hit * 100.0);
    }
  }
  if (stats.loh_only_hit > 0) {
    printf("  Avg size: %.0f bytes\n",
           (double)stats.loh_adv_total_size / stats.loh_only_hit);
  }

  /* Cleanup */
  free_request(req);
  cache_gdsf->cache_free(cache_gdsf);
  cache_loh->cache_free(cache_loh);
  close_reader(reader);

  return 0;
}
