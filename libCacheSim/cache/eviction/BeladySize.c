//
//  BeladySize.c
//  libCacheSim
//
//  sample object and compare reuse_distance * size, then evict the greatest one
//
//
/* todo: change to BeladySize */

#include "dataStructure/hashtable/hashtable.h"
#include "libCacheSim/evictionAlgo.h"

#ifdef __cplusplus
extern "C" {
#endif

static const char *DEFAULT_PARAMS = "exact=1,n-sample=128";

typedef struct {
  // whether to scan all cached objects at each eviction
  bool exact;
  // how many samples to take at each eviction
  int n_sample;
} BeladySize_params_t; /* BeladySize parameters */

// ***********************************************************************
// ****                                                               ****
// ****                   function declarations                       ****
// ****                                                               ****
// ***********************************************************************

static void BeladySize_parse_params(cache_t *cache,
                                    const char *cache_specific_params);
static void BeladySize_free(cache_t *cache);
static bool BeladySize_get(cache_t *cache, const request_t *req);
static cache_obj_t *BeladySize_find(cache_t *cache, const request_t *req,
                                    const bool update_cache);
static cache_obj_t *BeladySize_insert(cache_t *cache, const request_t *req);
static cache_obj_t *BeladySize_to_evict(cache_t *cache, const request_t *req);
static void BeladySize_evict(cache_t *cache, const request_t *req);
static bool BeladySize_remove(cache_t *cache, const obj_id_t obj_id);
static void BeladySize_remove_obj(cache_t *cache, cache_obj_t *obj);

// ***********************************************************************
// ****                                                               ****
// ****                   end user facing functions                   ****
// ****                                                               ****
// ****                       init, free, get                         ****
// ***********************************************************************

/**
 * @brief initialize a BeladySize cache
 *
 * @param ccache_params some common cache parameters
 * @param cache_specific_params BeladySize specific parameters, see parse_params
 * function or use -e "print" with the cachesim binary
 */
cache_t *BeladySize_init(const common_cache_params_t ccache_params,
                         const char *cache_specific_params) {
  cache_t *cache =
      cache_struct_init("BeladySize", ccache_params, cache_specific_params);

  cache->cache_init = BeladySize_init;
  cache->cache_free = BeladySize_free;
  cache->get = BeladySize_get;
  cache->find = BeladySize_find;
  cache->insert = BeladySize_insert;
  cache->evict = BeladySize_evict;
  cache->remove = BeladySize_remove;
  cache->to_evict = BeladySize_to_evict;

  BeladySize_params_t *params =
      (BeladySize_params_t *)malloc(sizeof(BeladySize_params_t));
  cache->eviction_params = params;

  BeladySize_parse_params(cache, DEFAULT_PARAMS);
  if (cache_specific_params != NULL) {
    BeladySize_parse_params(cache, cache_specific_params);
  }

  return cache;
}

/**
 * free resources used by this cache
 *
 * @param cache
 */
static void BeladySize_free(cache_t *cache) {
  free(cache->eviction_params);
  cache_struct_free(cache);
}

/**
 * @brief this function is the user facing API
 * it performs the following logic
 *
 * ```
 * if obj in cache:
 *    update_metadata
 *    return true
 * else:
 *    if cache does not have enough space:
 *        evict until it has space to insert
 *    insert the object
 *    return false
 * ```
 *
 * @param cache
 * @param req
 * @return true if cache hit, false if cache miss
 */
static bool BeladySize_get(cache_t *cache, const request_t *req) {
  return cache_get_base(cache, req);
}

// ***********************************************************************
// ****                                                               ****
// ****       developer facing APIs (used by cache developer)         ****
// ****                                                               ****
// ***********************************************************************

/**
 * @brief find an object in the cache
 *
 * @param cache
 * @param req
 * @param update_cache whether to update the cache,
 *  if true, the object is promoted
 *  and if the object is expired, it is removed from the cache
 * @return the object or NULL if not found
 */
static cache_obj_t *BeladySize_find(cache_t *cache, const request_t *req,
                                    const bool update_cache) {
  cache_obj_t *obj = cache_find_base(cache, req, update_cache);

  if (!update_cache) {
    return obj;
  }

  if (update_cache && obj != NULL) {
    if (req->next_access_vtime == -1 || req->next_access_vtime == INT64_MAX) {
      BeladySize_remove(cache, obj->obj_id);
    } else {
      obj->Belady.next_access_vtime = req->next_access_vtime;
    }
  }

  return obj;
}

/**
 * @brief insert an object into the cache,
 * update the hash table and cache metadata
 * this function assumes the cache has enough space
 * and eviction is not part of this function
 *
 * @param cache
 * @param req
 * @return the inserted object
 */
static cache_obj_t *BeladySize_insert(cache_t *cache, const request_t *req) {
  if (req->next_access_vtime == -1 || req->next_access_vtime == INT64_MAX) {
    return NULL;
  }

  cache_obj_t *obj = cache_insert_base(cache, req);
  obj->Belady.next_access_vtime = req->next_access_vtime;

  return obj;
}

struct hash_iter_user_data {
  uint64_t curr_vtime;
  cache_obj_t *to_evict_obj;
  double max_score;
  bool found_stale;
};

static inline void hashtable_iter_Belady_size(cache_obj_t *cache_obj,
                                              void *userdata) {
  struct hash_iter_user_data *iter_userdata =
      (struct hash_iter_user_data *)userdata;
  if (iter_userdata->found_stale) return;

  int64_t dt = (int64_t)(cache_obj->Belady.next_access_vtime -
                         (int64_t)iter_userdata->curr_vtime);
  if (dt <= 0) {
    iter_userdata->to_evict_obj = cache_obj;
    iter_userdata->found_stale = true;
    return;
  }

  int64_t obj_size = cache_obj->obj_size > 0 ? cache_obj->obj_size : 1;
  double obj_score = log((double)obj_size) + log((double)dt);
  if (iter_userdata->to_evict_obj == NULL ||
      obj_score > iter_userdata->max_score) {
    iter_userdata->to_evict_obj = cache_obj;
    iter_userdata->max_score = obj_score;
  }
}

/**
 * @brief find the object to be evicted
 * this function does not actually evict the object or update metadata
 * not all eviction algorithms support this function
 * because the eviction logic cannot be decoupled from finding eviction
 * candidate, so use assert(false) if you cannot support this function
 *
 * @param cache the cache
 * @return the object to be evicted
 */
static cache_obj_t *BeladySize_exact_to_evict(cache_t *cache,
                                              const request_t *req) {
  struct hash_iter_user_data iter_userdata;
  iter_userdata.curr_vtime = cache->n_req;
  iter_userdata.max_score = -1;
  iter_userdata.to_evict_obj = NULL;
  iter_userdata.found_stale = false;

  hashtable_foreach(cache->hashtable, hashtable_iter_Belady_size,
                    &iter_userdata);

  if (iter_userdata.to_evict_obj == NULL) {
    WARN(
        "BeladySize_to_evict: exact scan found no victim, "
        "current hash table size %llu, n_obj %llu, cache size %lld, request "
        "size %lld\n",
        (unsigned long long)hashsize(cache->hashtable->hashpower),
        (unsigned long long)cache->hashtable->n_obj,
        (long long)cache->cache_size, (long long)req->obj_size);
    return hashtable_rand_obj(cache->hashtable);
  }

  return iter_userdata.to_evict_obj;
}

static cache_obj_t *BeladySize_sample_to_evict(cache_t *cache,
                                               const request_t *req) {
  BeladySize_params_t *params = (BeladySize_params_t *)cache->eviction_params;
  cache_obj_t *obj_to_evict = NULL, *sampled_obj;
  double obj_to_evict_score = -1, sampled_obj_score = -1;
  for (int i = 0; i < params->n_sample; i++) {
    sampled_obj = hashtable_rand_obj(cache->hashtable);
    int64_t dt = sampled_obj->Belady.next_access_vtime - cache->n_req;
    if (dt <= 0) {
      /* object is stale (past its expected next access): evict immediately */
      obj_to_evict = sampled_obj;
      break;
    }
    sampled_obj_score = log((double)sampled_obj->obj_size) + log((double)dt);
    if (obj_to_evict_score < sampled_obj_score) {
      obj_to_evict = sampled_obj;
      obj_to_evict_score = sampled_obj_score;
    }
  }
  if (obj_to_evict == NULL) {
    WARN(
        "BeladySize_to_evict: obj_to_evict is NULL, "
        "maybe cache size is too small or hash power too large, "
        "current hash table size %llu, n_obj %llu, cache size %lld, request "
        "size "
        "%lld, and %d samples "
        "obj_to_evict_score %.4lf sampled_obj_score %.4lf\n",
        (unsigned long long)hashsize(cache->hashtable->hashpower),
        (unsigned long long)cache->hashtable->n_obj,
        (long long)cache->cache_size, (long long)req->obj_size,
        params->n_sample, obj_to_evict_score, sampled_obj_score);
    /* fallback: return a random object to avoid infinite recursion */
    return hashtable_rand_obj(cache->hashtable);
  }

  return obj_to_evict;
}

static cache_obj_t *BeladySize_to_evict(cache_t *cache, const request_t *req) {
  BeladySize_params_t *params = (BeladySize_params_t *)cache->eviction_params;
  if (params->exact) {
    return BeladySize_exact_to_evict(cache, req);
  }
  return BeladySize_sample_to_evict(cache, req);
}

/**
 * @brief evict an object from the cache
 * it needs to call cache_evict_base before returning
 * which updates some metadata such as n_obj, occupied size, and hash table
 *
 * @param cache
 * @param req not used
 * @param evicted_obj if not NULL, return the evicted object to caller
 */
static void BeladySize_evict(cache_t *cache, const request_t *req) {
  cache_obj_t *obj_to_evict = BeladySize_to_evict(cache, req);
  /* Re-verify the candidate is still in the hashtable after potential
   * shrink/expand operations that happened inside BeladySize_to_evict.
   * If the pointer is stale (obj_id moved to another slot), find the
   * correct pointer; if the object was already removed, skip. */
  cache_obj_t *verified =
      hashtable_find_obj_id(cache->hashtable, obj_to_evict->obj_id);
  if (verified == NULL) {
    /* object was already evicted or removed; try again */
    obj_to_evict = BeladySize_to_evict(cache, req);
    verified = hashtable_find_obj_id(cache->hashtable, obj_to_evict->obj_id);
    if (verified == NULL) return; /* give up to avoid crash */
  }
  obj_to_evict = verified;
  cache_evict_base(cache, obj_to_evict, true);
}

bool BeladySize_remove(cache_t *cache, const obj_id_t obj_id) {
  cache_obj_t *obj = hashtable_find_obj_id(cache->hashtable, obj_id);
  if (obj == NULL) {
    return false;
  }
  cache_remove_obj_base(cache, obj, true);
  return true;
}

// ***********************************************************************
// ****                                                               ****
// ****                  parameter set up functions                   ****
// ****                                                               ****
// ***********************************************************************
/**
 * @brief print the default parameters
 *
 */
static const char *BeladySize_current_params(BeladySize_params_t *params) {
  static __thread char params_str[128];
  snprintf(params_str, 128, "exact=%d,n-sample=%d\n", params->exact,
           params->n_sample);
  return params_str;
}

static bool BeladySize_parse_bool(const char *value) {
  return strcasecmp(value, "1") == 0 || strcasecmp(value, "true") == 0 ||
         strcasecmp(value, "yes") == 0 || strcasecmp(value, "on") == 0;
}

/**
 * parse the given parameters
 * input parameter is a string,
 * to see the default parameters, use current_params()
 * or use -e "print" with cachesim
 */
static void BeladySize_parse_params(cache_t *cache,
                                    const char *cache_specific_params) {
  BeladySize_params_t *params = (BeladySize_params_t *)cache->eviction_params;
  char *params_str = strdup(cache_specific_params);
  char *old_params_str = params_str;
  char *end;

  while (params_str != NULL && params_str[0] != '\0') {
    /* different parameters are separated by comma,
     * key and value are separated by '=' */
    char *key = strsep((char **)&params_str, "=");
    char *value = strsep((char **)&params_str, ",");

    // skip the white space
    while (params_str != NULL && *params_str == ' ') {
      params_str++;
    }

    if (strcasecmp(key, "exact") == 0) {
      params->exact = BeladySize_parse_bool(value);
    } else if (strcasecmp(key, "n-sample") == 0) {
      params->n_sample = (int)strtol(value, &end, 0);
      if (strlen(end) > 2) {
        ERROR("param parsing error, find string \"%s\" after number\n", end);
      }
    } else if (strcasecmp(key, "print") == 0) {
      printf("current parameters: %s\n", BeladySize_current_params(params));
      exit(0);
    } else {
      ERROR("%s does not have parameter %s, support %s\n", cache->cache_name,
            key, BeladySize_current_params(params));
      exit(1);
    }
  }

  free(old_params_str);
}

#ifdef __cplusplus
}
#endif
