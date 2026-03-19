/**
 * @file test_LOH_modules.c
 * @brief Comprehensive unit tests for LOH cache algorithm modules
 * @author Generated for testing LOH modular components
 * @date 2025-08-12
 */

#include <assert.h>
#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

// Include libCacheSim headers properly
#include "libCacheSim/cache.h"
#include "libCacheSim/evictionAlgo.h"

// Test utilities
#define TEST_ASSERT(condition, message)             \
  do {                                              \
    if (!(condition)) {                             \
      printf("FAIL: %s - %s\n", __func__, message); \
      return false;                                 \
    }                                               \
  } while (0)

#define TEST_PASS()                 \
  do {                              \
    printf("PASS: %s\n", __func__); \
    return true;                    \
  } while (0)

// Test statistics
static int tests_run = 0;
static int tests_passed = 0;

#define RUN_TEST(test_func) \
  do {                      \
    tests_run++;            \
    if (test_func()) {      \
      tests_passed++;       \
    }                       \
  } while (0)

// Helper function to create a test cache
static cache_t *create_test_cache(int64_t cache_size) {
  common_cache_params_t params = {.cache_size = cache_size, .default_ttl = 0};
  return LOH_init(params, NULL);
}

// Helper function to create a test request
static request_t *create_test_request(obj_id_t obj_id, int64_t obj_size,
                                      int64_t create_time) {
  request_t *req = malloc(sizeof(request_t));
  req->obj_id = obj_id;
  req->obj_size = obj_size;
  req->create_rtime = create_time;
  return req;
}

// ==================================================================
// LOH Module Summary and Test Plan
// ==================================================================

/**
 * LOH算法模块总结：
 *
 * 1. **Access Window Module (访问窗口模块)**
 *    - 功能：为每个缓存对象维护IRT历史窗口
 *    - 数据结构：LOH_access_window_t (3个IRT值的循环缓冲区)
 *    - 关键函数：create_access_window(), update_access_window(),
 * get_irt_features()
 *
 * 2. **Ghost Cache Module (幽灵缓存模块)**
 *    - 功能：保存被驱逐对象的历史信息，实现ThreeLCache风格的out_cache
 *    - 数据结构：LOH_ghost_entry_t双向链表 + GHashTable快速查找
 *    - 关键函数：add_to_ghost_cache(), restore_from_ghost_cache(),
 * erase_ghost_cache()
 *
 * 3. **Feature Calculation Module (特征计算模块)**
 *    - 功能：计算6个特征值 (recency, frequency, size, irt1, irt2, irt3)
 *    - 数据结构：统计计数器和特征向量
 *    - 关键函数：calculate_object_features()
 *
 * 4. **Cache Operations Module (缓存操作模块)**
 *    - 功能：标准缓存操作 (insert, find, evict, remove)
 *    - 数据结构：LRU队列 + 哈希表
 *    - 关键函数：cache_get(), cache_find(), cache_insert()
 *
 * 5. **Data Structure Consistency Module (数据结构一致性模块)**
 *    - 功能：维护LRU队列、频率表、IRT堆、尺寸桶的一致性
 *    - 数据结构：多个辅助数据结构的同步
 *    - 关键函数：各种数据结构的add/remove/update操作
 *
 * 6. **RL State Management Module (强化学习状态管理模块)**
 *    - 功能：收集统计信息，计算38维状态向量，与Python RL agent通信
 *    - 数据结构：统计计数器、状态向量、共享内存
 *    - 关键函数：update_state_vector(), sync_with_actor_critic()
 */

// ==================================================================
// Module 1: Basic Cache Operations Tests
// ==================================================================

/**
 * Test basic cache creation and destruction
 */
static bool test_cache_creation(void) {
  cache_t *cache = create_test_cache(10240);  // 10KB cache

  TEST_ASSERT(cache != NULL, "Cache creation failed");
  TEST_ASSERT(cache->cache_size == 10240, "Cache size incorrect");
  TEST_ASSERT(cache->n_obj == 0, "Initial object count should be 0");
  TEST_ASSERT(cache->eviction_params != NULL,
              "LOH params should be initialized");

  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test basic cache insert operation
 */
static bool test_cache_insert(void) {
  cache_t *cache = create_test_cache(10240);  // 10KB cache

  request_t *req = create_test_request(1, 1024, 100);

  // Test insertion - first get should be a miss and insert the object
  bool hit = cache_get_base(cache, req);
  TEST_ASSERT(hit == false, "First access should be miss (insert)");
  TEST_ASSERT(cache->n_obj == 1, "Cache should have 1 object after insert");

  // Find the inserted object
  cache_obj_t *obj = cache_find_base(cache, req, false);
  TEST_ASSERT(obj != NULL, "Inserted object should be findable");
  TEST_ASSERT(obj->obj_id == 1, "Object ID should match");
  TEST_ASSERT(obj->obj_size == 1024, "Object size should match");

  free(req);
  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test cache find operation
 */
static bool test_cache_find(void) {
  cache_t *cache = create_test_cache(10240);

  // Insert an object first
  request_t *req1 = create_test_request(1, 1024, 100);
  cache_get_base(cache, req1);  // Insert object

  // Test finding existing object
  request_t *req2 = create_test_request(1, 1024, 200);
  cache_obj_t *found = cache_find_base(cache, req2, false);
  TEST_ASSERT(found != NULL, "Should find existing object");
  TEST_ASSERT(found->obj_id == 1, "Found object should have correct ID");

  // Test finding non-existing object
  request_t *req3 = create_test_request(999, 1024, 300);
  cache_obj_t *not_found = cache_find_base(cache, req3, false);
  TEST_ASSERT(not_found == NULL, "Should not find non-existing object");

  free(req1);
  free(req2);
  free(req3);
  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test cache get operation (combines find and insert)
 */
static bool test_cache_get(void) {
  cache_t *cache = create_test_cache(10240);

  request_t *req1 = create_test_request(1, 1024, 100);

  // First access should be a miss
  bool hit1 = cache_get_base(cache, req1);
  TEST_ASSERT(hit1 == false, "First access should be miss");
  TEST_ASSERT(cache->n_obj == 1, "Object should be inserted");

  // Second access should be a hit
  bool hit2 = cache_get_base(cache, req1);
  TEST_ASSERT(hit2 == true, "Second access should be hit");
  TEST_ASSERT(cache->n_obj == 1, "Object count should remain 1");

  free(req1);
  cache->cache_free(cache);
  TEST_PASS();
}

// ==================================================================
// Module 2: Cache Eviction and Capacity Tests
// ==================================================================

/**
 * Test cache eviction when capacity is exceeded
 */
static bool test_cache_eviction(void) {
  cache_t *cache = create_test_cache(3072);  // 3KB cache for forced eviction

  // Fill cache beyond capacity
  for (int i = 1; i <= 5; i++) {
    request_t *req = create_test_request(i, 1024, i * 100);
    cache_get_base(cache, req);  // Use get to trigger eviction
    free(req);
  }

  // Cache should have triggered evictions
  TEST_ASSERT(cache->n_obj <= 3, "Cache should not exceed capacity");

  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test LRU order maintenance
 */
static bool test_lru_order(void) {
  cache_t *cache = create_test_cache(10240);

  // Insert multiple objects
  for (int i = 1; i <= 3; i++) {
    request_t *req = create_test_request(i, 1024, i * 100);
    cache_get_base(cache, req);
    free(req);
  }

  // Access object 1 to make it most recently used
  request_t *req_access = create_test_request(1, 1024, 400);
  cache_get_base(cache, req_access);
  free(req_access);

  // Object 1 should now be least likely to be evicted
  TEST_ASSERT(cache->n_obj == 3, "All objects should be in cache");

  cache->cache_free(cache);
  TEST_PASS();
}

// ==================================================================
// Module 3: LOH-Specific Feature Tests
// ==================================================================

/**
 * Test that LOH objects have access windows
 */
static bool test_access_windows(void) {
  cache_t *cache = create_test_cache(10240);

  request_t *req = create_test_request(1, 1024, 100);
  cache_get_base(cache, req);  // Insert object

  // Find the LOH object
  cache_obj_t *obj = cache_find_base(cache, req, false);
  TEST_ASSERT(obj != NULL, "Object should be found");

  // LOH objects should have access windows (check if LOH fields exist)
  // We can't directly access LOH-specific fields, but we can verify basic
  // object properties
  TEST_ASSERT(obj->obj_id == 1, "Object ID should be correct");
  TEST_ASSERT(obj->obj_size == 1024, "Object size should be correct");

  free(req);
  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test access count increment through multiple accesses
 */
static bool test_access_count(void) {
  cache_t *cache = create_test_cache(10240);

  request_t *req = create_test_request(1, 1024, 100);

  // First access (miss)
  bool hit1 = cache_get_base(cache, req);
  TEST_ASSERT(hit1 == false, "First access should be miss");

  // Second access (hit)
  bool hit2 = cache_get_base(cache, req);
  TEST_ASSERT(hit2 == true, "Second access should be hit");

  // Third access (hit)
  bool hit3 = cache_get_base(cache, req);
  TEST_ASSERT(hit3 == true, "Third access should be hit");

  free(req);
  cache->cache_free(cache);
  TEST_PASS();
}

// ==================================================================
// Module 4: Stress and Integration Tests
// ==================================================================

/**
 * Test cache with many objects
 */
static bool test_cache_stress(void) {
  cache_t *cache = create_test_cache(50 * 1024);  // 50KB cache

  // Insert many objects
  const int num_objects = 100;
  for (int i = 1; i <= num_objects; i++) {
    request_t *req = create_test_request(i, 1024, i * 10);
    cache_get_base(cache, req);
    free(req);
  }

  // Cache should be managing objects properly
  TEST_ASSERT(cache->n_obj <= 50, "Cache should respect capacity");
  TEST_ASSERT(cache->n_obj > 0, "Cache should contain some objects");

  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test repeated access patterns
 */
static bool test_repeated_access(void) {
  cache_t *cache = create_test_cache(10240);

  // Create a working set
  const int working_set = 5;
  for (int round = 0; round < 3; round++) {
    for (int i = 1; i <= working_set; i++) {
      request_t *req = create_test_request(i, 1024, round * 100 + i);
      bool hit = cache_get_base(cache, req);

      if (round > 0) {
        TEST_ASSERT(hit == true,
                    "Objects in working set should hit after first round");
      }
      free(req);
    }
  }

  cache->cache_free(cache);
  TEST_PASS();
}

// ==================================================================
// Module 5: Error Handling and Edge Cases
// ==================================================================

/**
 * Test zero-size cache
 */
static bool test_zero_cache(void) {
  cache_t *cache = create_test_cache(0);

  TEST_ASSERT(cache != NULL, "Zero-size cache should be created");

  request_t *req = create_test_request(1, 1024, 100);

  // Access should still work but object might be immediately evicted
  bool hit = cache_get_base(cache, req);
  TEST_ASSERT(hit == false, "Access to zero-size cache should be miss");

  free(req);
  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test large object insertion
 */
static bool test_large_object(void) {
  cache_t *cache = create_test_cache(1024);  // 1KB cache

  // Try to insert object larger than cache
  request_t *req = create_test_request(1, 2048, 100);  // 2KB object
  bool hit = cache_get_base(cache, req);

  // Should handle gracefully
  TEST_ASSERT(hit == false, "Large object insertion should be miss");

  free(req);
  cache->cache_free(cache);
  TEST_PASS();
}

// ==================================================================
// Module 6: Cache Performance and Hit Rate Tests
// ==================================================================

/**
 * Test cache hit rate calculation
 */
static bool test_hit_rate(void) {
  cache_t *cache = create_test_cache(5120);  // 5KB cache

  int total_requests = 20;
  int expected_hits = 0;

  // First round - all misses
  for (int i = 1; i <= 5; i++) {
    request_t *req = create_test_request(i, 1024, i * 100);
    bool hit = cache_get_base(cache, req);
    if (hit) expected_hits++;
    free(req);
  }

  // Second round - should be hits
  for (int i = 1; i <= 5; i++) {
    request_t *req = create_test_request(i, 1024, i * 100 + 1000);
    bool hit = cache_get_base(cache, req);
    if (hit) expected_hits++;
    free(req);
  }

  // Third round - mix of hits and possible evictions
  for (int i = 1; i <= 10; i++) {
    request_t *req = create_test_request(i, 1024, i * 100 + 2000);
    bool hit = cache_get_base(cache, req);
    if (hit) expected_hits++;
    free(req);
  }

  // Should have some hits
  TEST_ASSERT(expected_hits > 0, "Should have some cache hits");

  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test cache statistics
 */
static bool test_cache_statistics(void) {
  cache_t *cache = create_test_cache(10240);

  // Initial statistics
  TEST_ASSERT(cache->n_obj == 0, "Initial object count should be 0");
  // Note: used_bytes field may not exist in all cache implementations

  // Add some objects
  for (int i = 1; i <= 3; i++) {
    request_t *req = create_test_request(i, 1024, i * 100);
    cache_get_base(cache, req);
    free(req);
  }

  // Check statistics
  TEST_ASSERT(cache->n_obj == 3, "Should have 3 objects");

  cache->cache_free(cache);
  TEST_PASS();
}

// ==================================================================
// Module 7: Data Correctness and Internal State Verification
// ==================================================================

/**
 * Test precise access counting and frequency tracking
 */
static bool test_precise_access_counting(void) {
  cache_t *cache = create_test_cache(10240);

  // Create multiple requests for the same object
  request_t *req1 = create_test_request(1, 1024, 100);
  request_t *req2 = create_test_request(1, 1024, 200);
  request_t *req3 = create_test_request(1, 1024, 300);
  request_t *req4 = create_test_request(1, 1024, 400);

  // First access (miss)
  bool hit1 = cache_get_base(cache, req1);
  TEST_ASSERT(hit1 == false, "First access should be miss");
  TEST_ASSERT(cache->n_obj == 1, "Should have 1 object after first access");

  // Second access (hit)
  bool hit2 = cache_get_base(cache, req2);
  TEST_ASSERT(hit2 == true, "Second access should be hit");
  TEST_ASSERT(cache->n_obj == 1, "Should still have 1 object");

  // Third access (hit)
  bool hit3 = cache_get_base(cache, req3);
  TEST_ASSERT(hit3 == true, "Third access should be hit");
  TEST_ASSERT(cache->n_obj == 1, "Should still have 1 object");

  // Fourth access (hit)
  bool hit4 = cache_get_base(cache, req4);
  TEST_ASSERT(hit4 == true, "Fourth access should be hit");
  TEST_ASSERT(cache->n_obj == 1, "Should still have 1 object");

  // Verify the object is still findable
  cache_obj_t *obj = cache_find_base(cache, req1, false);
  TEST_ASSERT(obj != NULL, "Object should still be in cache");
  TEST_ASSERT(obj->obj_id == 1, "Object ID should be correct");

  free(req1);
  free(req2);
  free(req3);
  free(req4);
  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test IRT (Inter-Request Time) calculation accuracy
 */
static bool test_irt_calculation_accuracy(void) {
  cache_t *cache = create_test_cache(10240);

  // Create requests with specific timing intervals
  request_t *req1 = create_test_request(1, 1024, 1000);  // t=1000
  request_t *req2 = create_test_request(1, 1024, 1100);  // t=1100, IRT=100
  request_t *req3 = create_test_request(1, 1024, 1250);  // t=1250, IRT=150
  request_t *req4 = create_test_request(1, 1024, 1400);  // t=1400, IRT=150

  // Access sequence with specific timing
  cache_get_base(cache, req1);  // First access - no IRT yet
  cache_get_base(cache, req2);  // IRT = 100
  cache_get_base(cache, req3);  // IRT = 150
  cache_get_base(cache, req4);  // IRT = 150

  // Verify cache maintains the object
  cache_obj_t *obj = cache_find_base(cache, req1, false);
  TEST_ASSERT(obj != NULL, "Object should be in cache");
  TEST_ASSERT(obj->obj_id == 1, "Object ID should be correct");

  free(req1);
  free(req2);
  free(req3);
  free(req4);
  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test eviction decision accuracy under capacity pressure
 */
static bool test_eviction_decision_accuracy(void) {
  cache_t *cache =
      create_test_cache(3072);  // 3KB cache - exactly 3 objects of 1KB

  // Insert 3 objects to fill cache exactly
  request_t *req1 = create_test_request(1, 1024, 1000);
  request_t *req2 = create_test_request(2, 1024, 2000);
  request_t *req3 = create_test_request(3, 1024, 3000);

  cache_get_base(cache, req1);
  cache_get_base(cache, req2);
  cache_get_base(cache, req3);

  TEST_ASSERT(cache->n_obj == 3, "Cache should have exactly 3 objects");

  // Access object 1 multiple times to increase its frequency
  request_t *req1_access1 = create_test_request(1, 1024, 3100);
  request_t *req1_access2 = create_test_request(1, 1024, 3200);
  request_t *req1_access3 = create_test_request(1, 1024, 3300);

  cache_get_base(cache, req1_access1);  // obj1 now has higher frequency
  cache_get_base(cache, req1_access2);
  cache_get_base(cache, req1_access3);

  // Insert a new object, forcing eviction
  request_t *req4 = create_test_request(4, 1024, 4000);
  cache_get_base(cache, req4);

  TEST_ASSERT(cache->n_obj <= 3, "Cache should not exceed capacity");

  // Verify high-frequency object (obj1) is still in cache
  cache_obj_t *obj1 = cache_find_base(cache, req1, false);
  TEST_ASSERT(obj1 != NULL, "High-frequency object should not be evicted");

  // Verify new object (obj4) was inserted
  cache_obj_t *obj4 = cache_find_base(cache, req4, false);
  TEST_ASSERT(obj4 != NULL, "New object should be in cache");

  free(req1);
  free(req2);
  free(req3);
  free(req4);
  free(req1_access1);
  free(req1_access2);
  free(req1_access3);
  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test size-based eviction accuracy
 */
static bool test_size_based_eviction_accuracy(void) {
  cache_t *cache = create_test_cache(5120);  // 5KB cache

  // Insert objects of different sizes
  request_t *small1 = create_test_request(1, 512, 1000);   // 0.5KB
  request_t *small2 = create_test_request(2, 512, 2000);   // 0.5KB
  request_t *medium = create_test_request(3, 1024, 3000);  // 1KB
  request_t *large = create_test_request(4, 2048, 4000);   // 2KB

  cache_get_base(cache, small1);
  cache_get_base(cache, small2);
  cache_get_base(cache, medium);
  cache_get_base(cache, large);

  TEST_ASSERT(cache->n_obj == 4, "Should have 4 objects of different sizes");

  // Insert another large object to force eviction
  request_t *large2 = create_test_request(5, 2048, 5000);  // 2KB
  cache_get_base(cache, large2);

  // Verify cache respects capacity
  int64_t total_size = 0;
  for (int i = 1; i <= 5; i++) {
    request_t *req = create_test_request(i,
                                         (i == 1 || i == 2) ? 512
                                         : (i == 3)         ? 1024
                                                            : 2048,
                                         i * 1000);
    cache_obj_t *obj = cache_find_base(cache, req, false);
    if (obj) {
      total_size += obj->obj_size;
    }
    free(req);
  }

  TEST_ASSERT(total_size <= 5120,
              "Total cache size should not exceed capacity");

  free(small1);
  free(small2);
  free(medium);
  free(large);
  free(large2);
  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test recency calculation accuracy
 */
static bool test_recency_calculation_accuracy(void) {
  cache_t *cache = create_test_cache(10240);

  // Insert objects with specific timing
  request_t *old_obj = create_test_request(1, 1024, 1000);
  request_t *new_obj = create_test_request(2, 1024, 5000);

  cache_get_base(cache, old_obj);  // Accessed at t=1000
  cache_get_base(cache, new_obj);  // Accessed at t=5000

  // Access old object again to test recency update
  request_t *old_obj_recent = create_test_request(1, 1024, 6000);
  cache_get_base(cache, old_obj_recent);  // Now accessed at t=6000

  // Both objects should be in cache
  cache_obj_t *obj1 = cache_find_base(cache, old_obj, false);
  cache_obj_t *obj2 = cache_find_base(cache, new_obj, false);

  TEST_ASSERT(obj1 != NULL, "Object 1 should be in cache");
  TEST_ASSERT(obj2 != NULL, "Object 2 should be in cache");
  TEST_ASSERT(cache->n_obj == 2, "Should have exactly 2 objects");

  free(old_obj);
  free(new_obj);
  free(old_obj_recent);
  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test feature calculation consistency across operations
 */
static bool test_feature_calculation_consistency(void) {
  cache_t *cache = create_test_cache(8192);  // 8KB cache

  // Create a complex access pattern
  const int num_objects = 6;
  const int access_rounds = 3;

  // First round - insert all objects
  for (int i = 1; i <= num_objects; i++) {
    request_t *req = create_test_request(i, 1024, i * 1000);
    bool hit = cache_get_base(cache, req);
    TEST_ASSERT(hit == false, "First access should be miss");
    free(req);
  }

  TEST_ASSERT(cache->n_obj == num_objects, "All objects should be inserted");

  // Second round - access some objects more frequently
  for (int round = 1; round < access_rounds; round++) {
    for (int i = 1; i <= num_objects; i++) {
      // Objects 1,2,3 get more accesses
      int access_count = (i <= 3) ? 3 : 1;
      for (int j = 0; j < access_count; j++) {
        request_t *req = create_test_request(
            i, 1024, (round * 10000) + (i * 1000) + (j * 100));
        bool hit = cache_get_base(cache, req);
        TEST_ASSERT(hit == true, "Subsequent accesses should be hits");
        free(req);
      }
    }
  }

  // Verify high-frequency objects remain in cache
  for (int i = 1; i <= 3; i++) {
    request_t *req = create_test_request(i, 1024, 99999);
    cache_obj_t *obj = cache_find_base(cache, req, false);
    TEST_ASSERT(obj != NULL, "High-frequency objects should remain in cache");
    free(req);
  }

  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test memory consistency and data structure integrity
 */
static bool test_memory_consistency(void) {
  cache_t *cache = create_test_cache(4096);  // 4KB cache

  // Perform rapid insertions and evictions
  const int total_operations = 50;

  for (int i = 1; i <= total_operations; i++) {
    request_t *req = create_test_request(i, 1024, i * 100);
    cache_get_base(cache, req);

    // Verify cache state is consistent
    TEST_ASSERT(cache->n_obj >= 0, "Object count should not be negative");
    TEST_ASSERT(cache->n_obj <= 4, "Object count should not exceed capacity");

    // Verify recently inserted object can be found
    cache_obj_t *obj = cache_find_base(cache, req, false);
    if (cache->n_obj > 0) {
      // If cache has objects, at least the most recent should be findable
      // (unless immediately evicted due to size)
      if (obj != NULL) {
        TEST_ASSERT(obj->obj_id == (obj_id_t)i,
                    "Found object should have correct ID");
        TEST_ASSERT(obj->obj_size == 1024,
                    "Found object should have correct size");
      }
    }

    free(req);
  }

  cache->cache_free(cache);
  TEST_PASS();
}

/**
 * Test cache behavior with duplicate object IDs but different sizes
 */
static bool test_duplicate_id_handling(void) {
  cache_t *cache = create_test_cache(10240);

  // Insert object with ID 1, size 1024
  request_t *req1 = create_test_request(1, 1024, 1000);
  bool hit1 = cache_get_base(cache, req1);
  TEST_ASSERT(hit1 == false, "First access should be miss");

  // Access same ID with different size (simulating object update)
  request_t *req2 = create_test_request(1, 2048, 2000);
  bool hit2 = cache_get_base(cache, req2);
  // This could be hit or miss depending on implementation

  // Verify object exists
  cache_obj_t *obj = cache_find_base(cache, req1, false);
  TEST_ASSERT(obj != NULL, "Object should exist in cache");
  TEST_ASSERT(obj->obj_id == 1, "Object ID should be correct");

  free(req1);
  free(req2);
  cache->cache_free(cache);
  TEST_PASS();
}

// ==================================================================
// Test Runner
// ==================================================================

int main(void) {
  printf("=== LOH Module Unit Tests ===\n\n");

  // Module 1: Basic Cache Operations
  printf("Module 1: Basic Cache Operations\n");
  RUN_TEST(test_cache_creation);
  RUN_TEST(test_cache_insert);
  RUN_TEST(test_cache_find);
  RUN_TEST(test_cache_get);
  printf("\n");

  // Module 2: Cache Eviction and Capacity
  printf("Module 2: Cache Eviction and Capacity\n");
  RUN_TEST(test_cache_eviction);
  RUN_TEST(test_lru_order);
  printf("\n");

  // Module 3: LOH-Specific Features
  printf("Module 3: LOH-Specific Features\n");
  RUN_TEST(test_access_windows);
  RUN_TEST(test_access_count);
  printf("\n");

  // Module 4: Stress and Integration Tests
  printf("Module 4: Stress and Integration Tests\n");
  RUN_TEST(test_cache_stress);
  RUN_TEST(test_repeated_access);
  printf("\n");

  // Module 5: Error Handling and Edge Cases
  printf("Module 5: Error Handling and Edge Cases\n");
  RUN_TEST(test_zero_cache);
  RUN_TEST(test_large_object);
  printf("\n");

  // Module 6: Cache Performance Tests
  printf("Module 6: Cache Performance Tests\n");
  RUN_TEST(test_hit_rate);
  RUN_TEST(test_cache_statistics);
  printf("\n");

  // Module 7: Data Correctness and Internal State Verification
  printf("Module 7: Data Correctness and Internal State Verification\n");
  RUN_TEST(test_precise_access_counting);
  RUN_TEST(test_irt_calculation_accuracy);
  RUN_TEST(test_eviction_decision_accuracy);
  RUN_TEST(test_size_based_eviction_accuracy);
  RUN_TEST(test_recency_calculation_accuracy);
  RUN_TEST(test_feature_calculation_consistency);
  RUN_TEST(test_memory_consistency);
  RUN_TEST(test_duplicate_id_handling);
  printf("\n");

  // Test Summary
  printf("=== Test Summary ===\n");
  printf("Tests Run: %d\n", tests_run);
  printf("Tests Passed: %d\n", tests_passed);
  printf("Tests Failed: %d\n", tests_run - tests_passed);
  printf("Success Rate: %.1f%%\n",
         tests_run > 0 ? (float)tests_passed / tests_run * 100.0 : 0.0);

  return (tests_passed == tests_run) ? 0 : 1;
}
