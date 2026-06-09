# alibabaBlock_10 四配置复跑

目标 trace

- trace: /mnt/serverpool/dingkp_trace/alibabaBlock/new/alibabaBlock_10.oracleGeneral.zst
- cache size: 0.1
- 目标配置: f000, f001, f010, f011

配置位定义

- f000 = freq_rec=0, freq_size=0, rec_size=0
- f001 = freq_rec=0, freq_size=0, rec_size=1
- f010 = freq_rec=0, freq_size=1, rec_size=0
- f011 = freq_rec=0, freq_size=1, rec_size=1

运行口径

- 直接调用 _build_rel/bin/cachesim
- 不重编译
- CMA-ES only: LOH_ENABLE_CMAES=1, LOH_ENABLE_RL=0
- 显式关闭自动 compound: LOH_AUTO_COMPOUND=0
- compound on, IRT off
- 结构候选 16，随机候选 256
- 使用干净 shell，避免残留 LOH_* 环境变量污染
- 四个配置并行运行，脚本内部 wait 所有子进程结束

待启动脚本

- 脚本: tmp/20260421-alibabaBlock_10-rerun-f4/run.sh
- 日志目录: tmp/20260421-alibabaBlock_10-rerun-f4/logs
- 结果目录: tmp/20260421-alibabaBlock_10-rerun-f4/results

启动方式

- 等待用户口令后，再后台执行 bash tmp/20260421-alibabaBlock_10-rerun-f4/run.sh
