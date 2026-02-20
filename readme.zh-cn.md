# 🛡️ mac-smc-bat-guardian

## 🚀 项目简介
本项目通过直接操作 MacBook 的 SMC (System Management Controller) 端口，强制设定充电阈值（BCLM），并提供实时电源监控。
主要解决在 Linux 环境下，TLP 无法通过常规驱动控制 Mac 电池充电的问题。

### 💻 设备兼容性 (Compatibility)
本工具主要适用于通过 **SMC** 管理电源的 **Intel x86_64** 架构 MacBook 设备。
- **验证通过**: MacBook Pro 11,4 (Mid 2015)
- **理论支持**: 大多数 2006 年至 2020 年间的 MacBook Pro/Air (Intel 芯片)。这些设备通常包含 `applesmc` 驱动并支持 `BCLM` 键值。
- **不支持**: 
  - M1/M2/M3 (Apple Silicon) 芯片设备（它们使用不同的电源管理机制）。
  - 非常老旧的、不具备电池充电阈值控制能力的 Mac。

### 🛠️ 编译与运行
使用 GCC 编译 C 语言底层程序：
```bash
gcc -O2 smc_control.c -o smc_control
sudo ./smc_control 55  # 设置上限为 55%
```

### 🖥️ TUI 监控界面
本项目提供了一个基于 Textual 的精美 TUI 监控界面。

1. **安装依赖**:
   ```bash
   # https://gitee.com/wangnov/uv-custom/releases
   curl -LsSf https://gitee.com/wangnov/uv-custom/releases/download/0.10.4/uv-installer-custom.sh | sh
   uv venv # --python <版本号>
   uv pip install -r requirements.txt
   ```

2. **配置**:
   复制 `.env.example` 为 `.env` 并根据需要修改：
   ```bash
   cp .env.example .env
   ```
   你可以设置 `LOG_LEVEL` (debug, info, warn, error, silent) 和 `BATTERY_THRESHOLD`。

3. **运行**:
   ```bash
   uv python run smc_tui.py
   ```

### 🔋 预期电源策略行为

- [0% - 55%]: 充电逻辑激活，MagSafe 橙灯，current_now > 0。

- [> 55%]: 触发截断。SMC 强制切断流向电池的电流。

