#include "cache/eviction/loh_cmaes_bridge.h"

#include <algorithm>
#include <atomic>
#include <cctype>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <memory>
#include <mutex>
#include <random>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

#ifdef LOH_USE_LIBCMAES
#include <libcmaes/cmaes.h>
#include <libcmaes/eo_matrix.h>
#include <libcmaes/esoptimizer.h>
#include <libcmaes/pwq_bound_strategy.h>
#else
#include <eigen3/Eigen/Dense>
#endif

namespace {

constexpr double kSigmaFloor = 0.01;
constexpr double kDefaultWeight = 0.5;
// sigma 超过此值视为 aIPOP 失控，可通过 LOH_CMAES_SIGMA_CEILING 覆盖（默认50）
static double g_sigma_ceiling = 0.0;  // 0=disable sigma-fix by default
// sigma-fix 重启时使用的 init_sigma，可通过 LOH_CMAES_RESTART_SIGMA
// 覆盖（默认0.3，实测 c50/s0.3 最优）
static double g_restart_sigma = 0.3;

static bool env_flag_enabled(const char *key, bool fallback = false) {
  const char *raw = std::getenv(key);
  if (!raw || raw[0] == '\0') return fallback;
  std::string s(raw);
  std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
    return static_cast<char>(std::tolower(c));
  });
  if (s == "1" || s == "true" || s == "yes" || s == "on") return true;
  if (s == "0" || s == "false" || s == "no" || s == "off") return false;
  return fallback;
}

static double clip01(double x) {
  if (!std::isfinite(x)) return kDefaultWeight;
  if (x < 0.0) return 0.0;
  if (x > 1.0) return 1.0;
  return x;
}

#ifdef LOH_USE_LIBCMAES

using libcmaes::ACovarianceUpdate;
using libcmaes::CMAParameters;
using libcmaes::CMASolutions;
using libcmaes::CMAStrategy;
using libcmaes::CovarianceUpdate;
using libcmaes::ESOptimizer;
using libcmaes::FitFunc;
using libcmaes::GenoPheno;
using libcmaes::VDCMAUpdate;
using dMat = Eigen::MatrixXd;

class IOptimizerWrap {
 public:
  virtual ~IOptimizerWrap() = default;
  virtual dMat ask() = 0;
  virtual void tell() = 0;
  virtual void inc_iter() = 0;
  virtual CMASolutions &solutions() = 0;
};

template <typename TOptimizer>
class OptimizerWrap final : public IOptimizerWrap {
 public:
  using BoundGenoPheno = GenoPheno<libcmaes::pwqBoundStrategy>;
  using ParamsT = CMAParameters<BoundGenoPheno>;

  OptimizerWrap(FitFunc &fit, ParamsT &params) : optimizer_(fit, params) {}

  dMat ask() override { return optimizer_.ask(); }
  void tell() override { optimizer_.tell(); }
  void inc_iter() override { optimizer_.inc_iter(); }
  CMASolutions &solutions() override { return optimizer_.get_solutions(); }

 private:
  TOptimizer optimizer_;
};

using BoundGenoPheno = GenoPheno<libcmaes::pwqBoundStrategy>;
using ParamsT = CMAParameters<BoundGenoPheno>;

static int parse_algo_id(const char *raw_algo) {
  if (!raw_algo || raw_algo[0] == '\0') return aIPOP_CMAES;

  std::string s(raw_algo);
  std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
    return static_cast<char>(std::tolower(c));
  });

  if (s == "0" || s == "cmaes" || s == "default") return CMAES_DEFAULT;
  if (s == "1" || s == "ipop" || s == "pop" || s == "ipop-cma-es" ||
      s == "pop-cma-es")
    return IPOP_CMAES;
  if (s == "2" || s == "bipop" || s == "bipop-cma-es") return BIPOP_CMAES;
  if (s == "3" || s == "acmaes" || s == "active" || s == "active-cma-es")
    return aCMAES;
  if (s == "4" || s == "aipop" || s == "active-ipop" ||
      s == "active-ipop-cma-es")
    return aIPOP_CMAES;
  if (s == "5" || s == "abipop" || s == "active-bipop" ||
      s == "active-bipop-cma-es")
    return aBIPOP_CMAES;
  if (s == "6" || s == "sep" || s == "sepcmaes" || s == "sep-cma-es")
    return sepCMAES;
  if (s == "7" || s == "sepipop" || s == "sep-ipop" || s == "sep-ipop-cma-es")
    return sepIPOP_CMAES;
  if (s == "8" || s == "sepbipop" || s == "sep-bipop" ||
      s == "sep-bipop-cma-es")
    return sepBIPOP_CMAES;
  if (s == "9" || s == "sepacmaes" || s == "active-sep" ||
      s == "active-sep-cma-es")
    return sepaCMAES;
  if (s == "10" || s == "sepaipop" || s == "active-sep-ipop" ||
      s == "active-sep-ipop-cma-es")
    return sepaIPOP_CMAES;
  if (s == "11" || s == "sepabipop" || s == "active-sep-bipop" ||
      s == "active-sep-bipop-cma-es")
    return sepaBIPOP_CMAES;
  if (s == "12" || s == "vd" || s == "vdcma" || s == "vd-cma-es")
    return VD_CMAES;
  if (s == "13" || s == "vdipop" || s == "vd-ipop" || s == "vd-ipop-cma-es")
    return VD_IPOP_CMAES;
  if (s == "14" || s == "vdbipop" || s == "vd-bipop" || s == "vd-bipop-cma-es")
    return VD_BIPOP_CMAES;

  char *endptr = nullptr;
  long as_num = std::strtol(raw_algo, &endptr, 10);
  if (endptr && *endptr == '\0' && as_num >= 0 && as_num <= 14) {
    return static_cast<int>(as_num);
  }

  return aIPOP_CMAES;
}

static bool is_sep_algo(int algo) {
  return algo == sepCMAES || algo == sepIPOP_CMAES || algo == sepBIPOP_CMAES ||
         algo == sepaCMAES || algo == sepaIPOP_CMAES || algo == sepaBIPOP_CMAES;
}

static bool is_vd_algo(int algo) {
  return algo == VD_CMAES || algo == VD_IPOP_CMAES || algo == VD_BIPOP_CMAES;
}

static bool is_active_algo(int algo) {
  return algo == aCMAES || algo == aIPOP_CMAES || algo == aBIPOP_CMAES ||
         algo == sepaCMAES || algo == sepaIPOP_CMAES || algo == sepaBIPOP_CMAES;
}

class OnlineCMAES {
 public:
#if LOH_PERF_PROFILING
  using SteadyClock = std::chrono::steady_clock;
#endif

  OnlineCMAES(int dim, int lambda, double init_mean, double init_sigma,
              double lower_bound = 0.0, double upper_bound = 1.0)
      : dim_(std::max(1, dim)),
        lambda_(std::max(2, lambda)),
        init_mean_(std::clamp(init_mean, lower_bound, upper_bound)),
        init_sigma_(std::max(kSigmaFloor, init_sigma)),
        lower_bound_(lower_bound),
        upper_bound_(upper_bound),
        trace_range_(env_flag_enabled("LOH_CMAES_TRACE_RANGE", false)),
        algo_id_(parse_algo_id(std::getenv("LOH_CMAES_ALGO"))),
        async_enabled_(env_flag_enabled("LOH_CMAES_ASYNC", true)),
        fit_func_([](const double *, const int &) { return 0.0; }) {
    // 解析 sigma-fix 可调参数（一次性初始化全局值）
    {
      const char *env_sc = std::getenv("LOH_CMAES_SIGMA_CEILING");
      if (env_sc && env_sc[0]) {
        double v = std::atof(env_sc);
        if (v > 1.0 || v == 0.0) g_sigma_ceiling = v;  // >1=ceiling, 0=disable
      }
      const char *env_rs = std::getenv("LOH_CMAES_RESTART_SIGMA");
      if (env_rs && env_rs[0]) {
        double v = std::atof(env_rs);
        if (v > kSigmaFloor && v < 2.0)
          g_restart_sigma = v;  // 合理范围: (0.01, 2)
      }
      std::fprintf(stderr, "[CMAES] sigma_ceiling=%.4g restart_sigma=%s\n",
                   g_sigma_ceiling,
                   g_restart_sigma < 0
                       ? "init_sigma"
                       : std::to_string(g_restart_sigma).c_str());
    }
    lower_bounds_.assign(dim_, lower_bound_);
    upper_bounds_.assign(dim_, upper_bound_);
    gp_ = BoundGenoPheno(lower_bounds_.data(), upper_bounds_.data(), dim_);
    params_ = ParamsT(std::vector<double>(dim_, init_mean_), init_sigma_,
                      lambda_, 0, gp_);

    params_.set_algo(algo_id_);
    if (is_sep_algo(algo_id_)) params_.set_sep();
    if (is_vd_algo(algo_id_)) params_.set_vd();

    build_optimizer();
    refill_population();

    if (async_enabled_) {
      worker_ = std::thread(&OnlineCMAES::worker_loop, this);
      std::fprintf(stderr, "[CMAES] async worker thread started\n");
    }
  }

  // 向量化初始均值构造函数：每个维度可以有不同的起始中心
  OnlineCMAES(int dim, int lambda, const double *x0_vec, double init_sigma,
              double lower_bound = 0.0, double upper_bound = 1.0)
      : dim_(std::max(1, dim)),
        lambda_(std::max(2, lambda)),
        init_mean_(0.5),  // fallback, not used
        init_sigma_(std::max(kSigmaFloor, init_sigma)),
        lower_bound_(lower_bound),
        upper_bound_(upper_bound),
        trace_range_(env_flag_enabled("LOH_CMAES_TRACE_RANGE", false)),
        algo_id_(parse_algo_id(std::getenv("LOH_CMAES_ALGO"))),
        async_enabled_(env_flag_enabled("LOH_CMAES_ASYNC", true)),
        fit_func_([](const double *, const int &) { return 0.0; }) {
    lower_bounds_.assign(dim_, lower_bound_);
    upper_bounds_.assign(dim_, upper_bound_);
    gp_ = BoundGenoPheno(lower_bounds_.data(), upper_bounds_.data(), dim_);

    // 构建 per-dimension 初始均值向量，clamp 到 bounds
    std::vector<double> x0(dim_);
    for (int i = 0; i < dim_; ++i) {
      x0[i] = std::clamp(x0_vec[i], lower_bound_, upper_bound_);
    }
    params_ = ParamsT(x0, init_sigma_, lambda_, 0, gp_);

    params_.set_algo(algo_id_);
    if (is_sep_algo(algo_id_)) params_.set_sep();
    if (is_vd_algo(algo_id_)) params_.set_vd();

    build_optimizer();
    refill_population();

    if (async_enabled_) {
      worker_ = std::thread(&OnlineCMAES::worker_loop, this);
      std::fprintf(stderr, "[CMAES] async worker thread started (vec x0)\n");
    }
  }

  ~OnlineCMAES() {
    if (async_enabled_) {
      {
        std::lock_guard<std::mutex> lock(worker_mtx_);
        worker_shutdown_ = true;
      }
      worker_cv_.notify_one();
      if (worker_.joinable()) worker_.join();
    }
  }

  // Non-copyable, non-movable (owns a thread)
  OnlineCMAES(const OnlineCMAES &) = delete;
  OnlineCMAES &operator=(const OnlineCMAES &) = delete;

  bool ask(double *out_w, int out_dim) {
    if (!out_w || out_dim <= 0) return false;
    // If async worker is still computing new population, not ready
    if (worker_busy_.load(std::memory_order_acquire)) return false;
    if (pending_idx_ >= 0) return false;
    if (next_idx_ >= static_cast<int>(fitness_.size())) return false;

    pending_idx_ = next_idx_;
    const int n = std::min(dim_, out_dim);
    for (int i = 0; i < n; ++i) {
      out_w[i] = pheno_candidates_(i, pending_idx_);
    }
    for (int i = n; i < out_dim; ++i) {
      out_w[i] = 0.0;
    }
    return true;
  }

  int tell(double fit) {
#if LOH_PERF_PROFILING
    using namespace std::chrono;
    const auto t_total_begin = SteadyClock::now();
#endif

    last_tell_assign_ = 0.0;
    last_tell_prepare_solutions_ = 0.0;
    last_tell_optimizer_ = 0.0;
    last_tell_inc_iter_ = 0.0;
    last_tell_refill_ = 0.0;
    last_tell_total_ = 0.0;

    // If async worker is still computing, drop this feedback
    if (worker_busy_.load(std::memory_order_acquire)) {
#if LOH_PERF_PROFILING
      last_tell_total_ =
          duration<double>(SteadyClock::now() - t_total_begin).count();
#endif
      return generation_;
    }

    if (pending_idx_ < 0 || pending_idx_ >= static_cast<int>(fitness_.size())) {
      return generation_;
    }

#if LOH_PERF_PROFILING
    const auto t_assign_begin = SteadyClock::now();
#endif
    if (!std::isfinite(fit)) {
      fit = std::isfinite(last_best_) ? last_best_ : 1.0;
    }
    fitness_[pending_idx_] = fit;
    pending_idx_ = -1;
    ++next_idx_;
#if LOH_PERF_PROFILING
    const auto t_assign_end = SteadyClock::now();
    last_tell_assign_ = duration<double>(t_assign_end - t_assign_begin).count();
#endif

    if (next_idx_ < static_cast<int>(fitness_.size())) {
#if LOH_PERF_PROFILING
      last_tell_total_ =
          duration<double>(SteadyClock::now() - t_total_begin).count();
#endif
      return generation_;
    }

    // All lambda candidates evaluated — generation update needed
    if (async_enabled_) {
      // Submit to worker thread, return immediately
      worker_busy_.store(true, std::memory_order_release);
      {
        std::lock_guard<std::mutex> lock(worker_mtx_);
      }
      worker_cv_.notify_one();
#if LOH_PERF_PROFILING
      last_tell_total_ =
          duration<double>(SteadyClock::now() - t_total_begin).count();
#endif
      return generation_;
    }

    // Synchronous path (fallback)
    do_generation_update_sync(
#if LOH_PERF_PROFILING
        t_total_begin
#endif
    );
    return generation_;
  }

  int generation() const { return generation_; }
  double last_best_fitness() const { return last_best_; }

  void reset_sigma(double sigma) {
    wait_for_worker();
    init_sigma_ = std::max(kSigmaFloor, sigma);
    std::vector<double> x0_pheno(dim_, init_mean_);
    try {
      auto best = optimizer_->solutions().best_candidate().get_x();
      if (static_cast<int>(best.size()) == dim_) {
        dVec best_vec(dim_);
        for (int i = 0; i < dim_; ++i)
          best_vec(i) = best[static_cast<size_t>(i)];
        dVec best_pheno = gp_.pheno(best_vec);
        x0_pheno.assign(best_pheno.data(),
                        best_pheno.data() + best_pheno.size());
      }
    } catch (...) {
    }
    params_ = ParamsT(x0_pheno, init_sigma_, lambda_, 0, gp_);
    params_.set_algo(algo_id_);
    if (is_sep_algo(algo_id_)) params_.set_sep();
    if (is_vd_algo(algo_id_)) params_.set_vd();

    build_optimizer();
    refill_population();
  }

  // Cold restart: discard all history, start from init_mean with fresh sigma.
  void full_restart(double new_mean, double new_sigma) {
    wait_for_worker();
    init_mean_ = std::clamp(new_mean, lower_bound_, upper_bound_);
    init_sigma_ = std::max(kSigmaFloor, new_sigma);
    generation_ = 0;
    last_best_ = 1.0;
    params_ = ParamsT(std::vector<double>(dim_, init_mean_), init_sigma_,
                      lambda_, 0, gp_);
    params_.set_algo(algo_id_);
    if (is_sep_algo(algo_id_)) params_.set_sep();
    if (is_vd_algo(algo_id_)) params_.set_vd();
    build_optimizer();
    refill_population();
    std::fprintf(stderr, "[CMAES] full_restart: mean=%.4f sigma=%.4f\n",
                 init_mean_, init_sigma_);
  }

  void get_last_tell_timing(double *assign, double *prepare_solutions,
                            double *optimizer_tell, double *inc_iter,
                            double *refill, double *total) const {
    if (assign) *assign = last_tell_assign_;
    if (prepare_solutions) *prepare_solutions = last_tell_prepare_solutions_;
    if (optimizer_tell) *optimizer_tell = last_tell_optimizer_;
    if (inc_iter) *inc_iter = last_tell_inc_iter_;
    if (refill) *refill = last_tell_refill_;
    if (total) *total = last_tell_total_;
  }

  // 获取 CMA-ES 当前 step-size σ
  double get_sigma() const {
    if (!optimizer_) return init_sigma_;
    return optimizer_->solutions().sigma();
  }

  // 获取 CMA-ES 当前均值向量 xmean（phenotype 空间）
  // 返回实际写入的维度数
  int get_mean(double *out_mean, int out_dim) const {
    if (!optimizer_ || out_dim <= 0) return 0;
    auto &sol = optimizer_->solutions();
    dVec xm = gp_.pheno(sol.xmean());
    int n = std::min(out_dim, static_cast<int>(xm.size()));
    for (int i = 0; i < n; ++i) out_mean[i] = xm(i);
    return n;
  }

 private:
  void wait_for_worker() {
    if (!async_enabled_) return;
    while (worker_busy_.load(std::memory_order_acquire)) {
      // Spin briefly then yield
      std::this_thread::yield();
    }
  }

  void worker_loop() {
    while (true) {
      {
        std::unique_lock<std::mutex> lock(worker_mtx_);
        worker_cv_.wait(lock, [this] {
          return worker_busy_.load(std::memory_order_relaxed) ||
                 worker_shutdown_;
        });
        if (worker_shutdown_) return;
      }
      // Do the expensive generation update (mutex NOT held)
      do_generation_update_core();
      worker_busy_.store(false, std::memory_order_release);
    }
  }

  // Core generation update — called by worker thread (async) or by tell()
  // (sync)
  void do_generation_update_core() {
    auto &sol = optimizer_->solutions();
    for (int i = 0; i < static_cast<int>(fitness_.size()); ++i) {
      sol.get_candidate(i).set_x(internal_candidates_.col(i));
      sol.get_candidate(i).set_fvalue(fitness_[i]);
    }
    optimizer_->tell();
    optimizer_->inc_iter();
    ++generation_;
    last_best_ = sol.best_candidate().get_fvalue();
    maybe_update_best_ever();
    if (check_sigma_overflow()) return;  // already did restart+refill
    refill_population();
  }

  // Synchronous generation update with profiling
  void do_generation_update_sync(
#if LOH_PERF_PROFILING
      std::chrono::steady_clock::time_point t_total_begin
#endif
  ) {
    using namespace std::chrono;
#if LOH_PERF_PROFILING
    const auto t_prepare_begin = SteadyClock::now();
#endif
    auto &sol = optimizer_->solutions();
    for (int i = 0; i < static_cast<int>(fitness_.size()); ++i) {
      sol.get_candidate(i).set_x(internal_candidates_.col(i));
      sol.get_candidate(i).set_fvalue(fitness_[i]);
    }
#if LOH_PERF_PROFILING
    const auto t_prepare_end = SteadyClock::now();
    last_tell_prepare_solutions_ =
        duration<double>(t_prepare_end - t_prepare_begin).count();
    const auto t_opt_tell_begin = SteadyClock::now();
#endif
    optimizer_->tell();
#if LOH_PERF_PROFILING
    const auto t_opt_tell_end = SteadyClock::now();
    last_tell_optimizer_ =
        duration<double>(t_opt_tell_end - t_opt_tell_begin).count();
    const auto t_inc_iter_begin = SteadyClock::now();
#endif
    optimizer_->inc_iter();
    ++generation_;
    last_best_ = sol.best_candidate().get_fvalue();
    maybe_update_best_ever();
#if LOH_PERF_PROFILING
    const auto t_inc_iter_end = SteadyClock::now();
    last_tell_inc_iter_ =
        duration<double>(t_inc_iter_end - t_inc_iter_begin).count();
    const auto t_refill_begin = SteadyClock::now();
#endif
    if (!check_sigma_overflow()) {
      refill_population();
    }
#if LOH_PERF_PROFILING
    const auto t_refill_end = SteadyClock::now();
    last_tell_refill_ = duration<double>(t_refill_end - t_refill_begin).count();
    last_tell_total_ =
        duration<double>(SteadyClock::now() - t_total_begin).count();
#endif
  }

  void build_optimizer() {
    using Vanilla =
        ESOptimizer<CMAStrategy<CovarianceUpdate, BoundGenoPheno>, ParamsT>;
    using Active =
        ESOptimizer<CMAStrategy<ACovarianceUpdate, BoundGenoPheno>, ParamsT>;
    using Vd = ESOptimizer<CMAStrategy<VDCMAUpdate, BoundGenoPheno>, ParamsT>;

    if (is_vd_algo(algo_id_)) {
      optimizer_ = std::make_unique<OptimizerWrap<Vd>>(fit_func_, params_);
      return;
    }
    if (is_active_algo(algo_id_)) {
      optimizer_ = std::make_unique<OptimizerWrap<Active>>(fit_func_, params_);
      return;
    }
    optimizer_ = std::make_unique<OptimizerWrap<Vanilla>>(fit_func_, params_);
  }

  void refill_population() {
    internal_candidates_ = optimizer_->ask();
    if (internal_candidates_.cols() <= 0 || internal_candidates_.rows() <= 0) {
      throw std::runtime_error("libcmaes ask() produced empty population");
    }

    if (trace_range_) {
      // trace 打开时才统计范围与越界分布；常态路径仅保留必要 finite 修复。
      double raw_min = std::numeric_limits<double>::infinity();
      double raw_max = -std::numeric_limits<double>::infinity();
      int nonfinite_count = 0;
      int below_lower = 0;
      int above_upper = 0;

      for (int c = 0; c < internal_candidates_.cols(); ++c) {
        for (int r = 0; r < internal_candidates_.rows(); ++r) {
          const double raw = internal_candidates_(r, c);
          if (std::isfinite(raw)) {
            if (raw < raw_min) raw_min = raw;
            if (raw > raw_max) raw_max = raw;
            if (raw < 0.0) ++below_lower;
            if (raw > 1.0) ++above_upper;
          } else {
            ++nonfinite_count;
            internal_candidates_(r, c) = kDefaultWeight;
          }
        }
      }

      if (!std::isfinite(raw_min)) raw_min = kDefaultWeight;
      if (!std::isfinite(raw_max)) raw_max = kDefaultWeight;
      std::fprintf(stderr,
                   "[CMAES RANGE] gen=%d algo=%d raw_min=%.6g raw_max=%.6g "
                   "nonfinite=%d below_lower=%d above_upper=%d\n",
                   generation_, algo_id_, raw_min, raw_max, nonfinite_count,
                   below_lower, above_upper);
    } else {
      for (int c = 0; c < internal_candidates_.cols(); ++c) {
        for (int r = 0; r < internal_candidates_.rows(); ++r) {
          if (!std::isfinite(internal_candidates_(r, c))) {
            internal_candidates_(r, c) = kDefaultWeight;
          }
        }
      }
    }

    pheno_candidates_ = gp_.pheno(internal_candidates_);

    for (int c = 0; c < pheno_candidates_.cols(); ++c) {
      for (int r = 0; r < pheno_candidates_.rows(); ++r) {
        if (!std::isfinite(pheno_candidates_(r, c))) {
          pheno_candidates_(r, c) = kDefaultWeight;
        }
      }
    }

    fitness_.assign(static_cast<size_t>(pheno_candidates_.cols()), 0.0);
    next_idx_ = 0;
    pending_idx_ = -1;
  }

 private:
  int dim_;
  int lambda_;
  double init_mean_;
  double init_sigma_;
  double lower_bound_;
  double upper_bound_;
  bool trace_range_;
  int algo_id_;
  bool async_enabled_;
  std::vector<double> lower_bounds_;
  std::vector<double> upper_bounds_;
  BoundGenoPheno gp_;

  int generation_ = 0;
  double last_best_ = 1.0;

  // 方案 D: 历史最优解缓存 —— 用于 sigma 溢出后 restart 的起点
  std::vector<double> best_ever_pheno_;  // phenotype 空间最优解
  double best_ever_fitness_ = std::numeric_limits<double>::infinity();
  int sigma_overflow_restarts_ = 0;  // sigma 溢出触发的 restart 计数

  FitFunc fit_func_;
  ParamsT params_;
  std::unique_ptr<IOptimizerWrap> optimizer_;

  dMat internal_candidates_;
  dMat pheno_candidates_;
  std::vector<double> fitness_;
  int next_idx_ = 0;
  int pending_idx_ = -1;

  double last_tell_assign_ = 0.0;
  double last_tell_prepare_solutions_ = 0.0;
  double last_tell_optimizer_ = 0.0;
  double last_tell_inc_iter_ = 0.0;
  double last_tell_refill_ = 0.0;
  double last_tell_total_ = 0.0;

  // 更新历史最优解
  void maybe_update_best_ever() {
    if (!optimizer_) return;
    try {
      auto &sol = optimizer_->solutions();
      double f = sol.best_candidate().get_fvalue();
      if (!std::isfinite(f)) return;
      if (f < best_ever_fitness_) {
        best_ever_fitness_ = f;
        auto best_geno = sol.best_candidate().get_x();
        if (static_cast<int>(best_geno.size()) == dim_) {
          dVec bv(dim_);
          for (int i = 0; i < dim_; ++i)
            bv(i) = best_geno[static_cast<size_t>(i)];
          dVec bp = gp_.pheno(bv);
          best_ever_pheno_.assign(bp.data(), bp.data() + bp.size());
        }
      }
    } catch (...) {
    }
  }

  // 检测 sigma 溢出并自动 restart。返回 true 表示已执行 restart+refill。
  bool check_sigma_overflow() {
    if (g_sigma_ceiling <= 0.0) return false; // Disable flag

    double sigma = get_sigma();
    if (std::isfinite(sigma) && sigma <= g_sigma_ceiling) return false;

    ++sigma_overflow_restarts_;
    double restart_s = (g_restart_sigma > 0) ? g_restart_sigma : init_sigma_;
    if (!best_ever_pheno_.empty() && std::isfinite(best_ever_fitness_)) {
      // 用历史最优解作为新起点 restart
      std::fprintf(
          stderr,
          "[CMAES SIGMA-FIX] gen=%d sigma=%.4g overflow (#%d), "
          "restart from best_ever (fitness=%.6f, restart_sigma=%.4g)\n",
          generation_, sigma, sigma_overflow_restarts_, best_ever_fitness_,
          restart_s);
      params_ = ParamsT(best_ever_pheno_, restart_s, lambda_, 0, gp_);
    } else {
      // 没有有效历史最优，回退到 init_mean
      std::fprintf(
          stderr,
          "[CMAES SIGMA-FIX] gen=%d sigma=%.4g overflow (#%d), "
          "restart from init_mean=%.4f (no best_ever, restart_sigma=%.4g)\n",
          generation_, sigma, sigma_overflow_restarts_, init_mean_, restart_s);
      params_ = ParamsT(std::vector<double>(dim_, init_mean_), restart_s,
                        lambda_, 0, gp_);
    }
    params_.set_algo(algo_id_);
    if (is_sep_algo(algo_id_)) params_.set_sep();
    if (is_vd_algo(algo_id_)) params_.set_vd();
    build_optimizer();
    refill_population();
    return true;
  }

  // Async worker thread
  std::thread worker_;
  std::mutex worker_mtx_;
  std::condition_variable worker_cv_;
  std::atomic<bool> worker_busy_{false};
  bool worker_shutdown_ = false;
};

#else
#error "LOH CMA-ES now requires LOH_USE_LIBCMAES=ON (Eigen fallback removed)"
#endif

}  // namespace

extern "C" {

void *loh_cmaes_create(int dim, int lambda, double init_mean,
                       double init_sigma) {
  try {
    auto *opt = new OnlineCMAES(dim, lambda, init_mean, init_sigma);
    return static_cast<void *>(opt);
  } catch (...) {
    return nullptr;
  }
}

void *loh_cmaes_create_bounded(int dim, int lambda, double init_mean,
                               double init_sigma, double lower_bound,
                               double upper_bound) {
  try {
    auto *opt = new OnlineCMAES(dim, lambda, init_mean, init_sigma, lower_bound,
                                upper_bound);
    return static_cast<void *>(opt);
  } catch (...) {
    return nullptr;
  }
}

void *loh_cmaes_create_bounded_v(int dim, int lambda, const double *x0_vec,
                                 double init_sigma, double lower_bound,
                                 double upper_bound) {
  try {
    auto *opt = new OnlineCMAES(dim, lambda, x0_vec, init_sigma, lower_bound,
                                upper_bound);
    return static_cast<void *>(opt);
  } catch (...) {
    return nullptr;
  }
}

void loh_cmaes_destroy(void *handle) {
  if (!handle) return;
  auto *opt = static_cast<OnlineCMAES *>(handle);
  delete opt;
}

int loh_cmaes_ask(void *handle, double *out_w, int out_dim) {
  if (!handle) return 0;
  auto *opt = static_cast<OnlineCMAES *>(handle);
  return opt->ask(out_w, out_dim) ? 1 : 0;
}

int loh_cmaes_tell(void *handle, double fitness) {
  if (!handle) return -1;
  auto *opt = static_cast<OnlineCMAES *>(handle);
  return opt->tell(fitness);
}

int loh_cmaes_get_generation(const void *handle) {
  if (!handle) return -1;
  const auto *opt = static_cast<const OnlineCMAES *>(handle);
  return opt->generation();
}

double loh_cmaes_get_last_best_fitness(const void *handle) {
  if (!handle) return 1.0;
  const auto *opt = static_cast<const OnlineCMAES *>(handle);
  return opt->last_best_fitness();
}

void loh_cmaes_reset_sigma(void *handle, double sigma) {
  if (!handle) return;
  auto *opt = static_cast<OnlineCMAES *>(handle);
  opt->reset_sigma(sigma);
}

void loh_cmaes_full_restart(void *handle, double init_mean, double init_sigma) {
  if (!handle) return;
  auto *opt = static_cast<OnlineCMAES *>(handle);
  opt->full_restart(init_mean, init_sigma);
}

int loh_cmaes_get_last_tell_timing(const void *handle, double *assign,
                                   double *prepare_solutions,
                                   double *optimizer_tell, double *inc_iter,
                                   double *refill, double *total) {
  if (!handle) return 0;
  const auto *opt = static_cast<const OnlineCMAES *>(handle);
  opt->get_last_tell_timing(assign, prepare_solutions, optimizer_tell, inc_iter,
                            refill, total);
  return 1;
}

double loh_cmaes_get_sigma(const void *handle) {
  if (!handle) return -1.0;
  return static_cast<const OnlineCMAES *>(handle)->get_sigma();
}

int loh_cmaes_get_mean(const void *handle, double *out_mean, int out_dim) {
  if (!handle) return 0;
  return static_cast<const OnlineCMAES *>(handle)->get_mean(out_mean, out_dim);
}

}  // extern "C"
