#ifndef LOH_CMAES_BRIDGE_H
#define LOH_CMAES_BRIDGE_H

#ifdef __cplusplus
extern "C" {
#endif

void *loh_cmaes_create(int dim, int lambda, double init_mean,
                       double init_sigma);
void *loh_cmaes_create_bounded(int dim, int lambda, double init_mean,
                               double init_sigma, double lower_bound,
                               double upper_bound);
// 向量化初始均值版本：x0_vec[0..dim-1] 指定每个维度的起始中心
void *loh_cmaes_create_bounded_v(int dim, int lambda, const double *x0_vec,
                                 double init_sigma, double lower_bound,
                                 double upper_bound);
void loh_cmaes_destroy(void *handle);

int loh_cmaes_ask(void *handle, double *out_w, int out_dim);
int loh_cmaes_tell(void *handle, double fitness);

int loh_cmaes_get_generation(const void *handle);
double loh_cmaes_get_last_best_fitness(const void *handle);
void loh_cmaes_reset_sigma(void *handle, double sigma);
void loh_cmaes_full_restart(void *handle, double init_mean, double init_sigma);
int loh_cmaes_get_last_tell_timing(const void *handle, double *assign,
                                   double *prepare_solutions,
                                   double *optimizer_tell, double *inc_iter,
                                   double *refill, double *total);
// 获取 CMA-ES 当前 step-size σ（返回 <0 表示无效）
double loh_cmaes_get_sigma(const void *handle);
// 获取 CMA-ES 当前均值向量 xmean（phenotype 空间），返回写入维度数
int loh_cmaes_get_mean(const void *handle, double *out_mean, int out_dim);

#ifdef __cplusplus
}
#endif

#endif
