# MacBook SMC Charge Limiter (VincentZyu 版)

## 🚀 项目简介
本项目通过直接操作 MacBook A1398 的 SMC (System Management Controller) 端口，强制设定充电阈值。
主要解决在 Linux 环境下，TLP 无法通过常规驱动控制 Mac 电池充电的问题。

### 🛠️ 编译与运行
使用 GCC 编译 C 语言底层程序：
```bash
gcc -O2 smc_control.c -o smc_control
sudo ./smc_control 55  # 设置上限为 55%
```

###🔋 预期电源策略行为

- [0% - 55%]: 充电逻辑激活，MagSafe 橙灯，current_now > 0。

- [> 55%]: 触发截断。SMC 强制切断流向电池的电流。

