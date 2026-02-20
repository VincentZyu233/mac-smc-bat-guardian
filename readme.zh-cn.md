# 🛡️ mac-smc-bat-guardian

[English](readme.md) | [中文说明](readme.zh-cn.md)

## 🚀 项目简介
本项目通过直接操作 MacBook 的 SMC (System Management Controller) 端口，强制设定充电阈值（BCLM），并提供实时电源监控。
主要解决在 Linux 环境下，TLP 无法通过常规驱动控制 Mac 电池充电的问题。

### 💻 设备兼容性 (Compatibility)
本工具主要适用于通过 **SMC** 管理电源的 **Intel x86_64** 架构 MacBook 设备。
- **验证通过**: MacBook Pro 11,4 A1398(Mid 2015)
> 我的设备信息:
![my_device_macbook_pro_11_4_A1398.png](my_device_macbook_pro_11_4_A1398.png)
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

### 🔍 预期现象：TUI输出与MagSafe充电灯

以默认阈值（55）运行时：

- **电量低于55%时：**
  - TUI 日志区会出现类似：
    > [yellow][时间] WARN: ⚠️ 电量越过阈值 55%！当前: 50%
  - 右侧状态区显示：
    - 当前电量：50%
    - 电池状态：Discharging（放电中）
    - 正在充电：❌ no
    - 电池供电：✅ yes

- **低于55%插上充电器时：**
  - TUI 日志区出现“电源已连接”，状态变为 Charging。
  - 右侧状态区显示：
    - 电池状态：Charging
    - 正在充电：✅ yes
    - 主板供电：✅ yes
    - 电池供电：❌ no
    - 当前电流：为正（如 2000 mA）
  - **MagSafe 灯变为橙色**（正在充电）

- **电量充到/超过55%时：**
  - TUI 日志区出现：
    > [yellow][时间] WARN: ⚠️ 电量越过阈值 55%！当前: 55%
    > [green][时间] INFO: 🎯 电量达到阈值: 55%
  - 右侧状态区显示：
    - 电池状态：Not Charging 或 Idle
    - 正在充电：❌ no
    - 主板供电：✅ yes
    - 电池供电：❌ no
    - 当前电流：0 或接近0
  - **MagSafe 灯变为绿色**（SMC 截断充电）

如出现上述现象，说明 SMC 控制与 TUI 监控均工作正常。

### ⚙️ 为什么必须用C代码？

C 代码（`smc_control.c`）之所以不可或缺，是因为它直接通过 I/O 端口（如 0x300/0x304）对 MacBook 的 SMC（系统管理控制器）进行底层硬件访问，从而设置电池充电上限（BCLM）。这一操作无法用纯 Python 或大多数高级语言实现。只有 C（或等价的底层语言）才能：

- 使用 `ioperm`、`inb`、`outb` 等特权指令与硬件端口通信；
- 以 root 权限在系统级别直接向 SMC 芯片发送命令。

**为什么 Python 或其他高级语言做不到？**
- Python 及大多数高级语言出于安全和可移植性考虑，不允许直接访问 CPU I/O 端口；
- 即使用 Python 的 `ctypes` 或 `cffi`，本质上也需要 C 扩展或库来实现这些特权操作；
- 所有已知的开源 SMC 工具（如 smcFanControl、smc-util）底层都是用 C/C++ 实现。

**总结：**
- C 代码对于直接 SMC 控制是不可替代的。Python 适合做 UI、自动化和监控，但实际的硬件指令必须由以 root 权限运行的 C 代码完成。

