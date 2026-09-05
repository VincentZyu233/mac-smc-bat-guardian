![mac-smc-bat-guardian](https://socialify.git.ci/VincentZyu233/mac-smc-bat-guardian/image?custom_description=%F0%9F%94%8B+Intel+CPU+MacBook+Power+Management+%26+SMC+BCLM+Controller+for+Linux.+A+sophisticated+TUI+to+monitor+real-time+battery+health%2C+current+flow%2C+and+set+charge+thresholds.+&custom_language=Python&description=1&forks=1&issues=1&language=1&logo=https%3A%2F%2Fraw.githubusercontent.com%2FVincentZyu233%2Fmac-smc-bat-guardian%2Fabf88fb5b555d81f75dc4503150815d152da33e1%2Fassets%2Fmerged_logo.svg&name=1&owner=1&pulls=1&stargazers=1&theme=Light)

<div align="center">
  <a href="https://github.com/VincentZyu233/mac-smc-bat-guardian"><img src="https://img.shields.io/badge/GitHub-VincentZyu233/mac--smc--bat--guardian-181717?style=flat-square&logo=github" alt="GitHub"></a>
  <a href="https://gitee.com/vincent-zyu/mac-smc-bat-guardian"><img src="https://img.shields.io/badge/Gitee-vincent--zyu/mac--smc--bat--guardian-C71D23?style=flat-square&logo=gitee" alt="Gitee"></a>
</div>

# 🛡️ mac-smc-bat-guardian

> [📖English](readme.md)
> [📖中文说明](readme.zh-cn.md)

## 🚀 项目简介
本项目提供一个 Python/Textual TUI，用于在 Linux 上实时监控 MacBook 的电池、电源、风扇和事件日志。
项目还包含一个可选的 C 原型程序，用于尝试写入 SMC `BCLM` 键，实验性探索充电阈值控制。

> [!IMPORTANT]
>
> ⚠️ **当前状态：充电阈值控制仍是实验性功能，并且在作者的测试设备上未能实际生效。**
>
> `smc_control` 显示“成功写入”只代表程序完成了 I/O 端口写入，不能证明 SMC 已接受或执行 `BCLM`，也不能证明充电电流已被限制。
>
> 可靠控制可能依赖尚未公开的固件协议或 macOS 专有电源管理组件；目前没有足够证据确认具体原因，因此本项目不保证 Linux 下的充电阈值控制有效。

### 💻 设备兼容性 (Compatibility)
监控界面主要适用于能通过 Linux sysfs 和 `applesmc` 暴露电池与风扇数据的 **Intel x86_64** MacBook。
> 我的测试设备：
>
> ![my_device_macbook_pro_11_4_A1398.png](docs/images/my_device_macbook_pro_11_4_A1398.png)
>
- **监控验证通过**：MacBook Pro 11,4 A1398 (Mid 2015)。
- **控制实验目标**：能暴露 `applesmc` 和 `BCLM` 键的 Intel MacBook Pro/Air；存在这些接口并不代表阈值控制能够生效。
- **本原型不支持**：
  - 使用不同电源管理架构的 Apple Silicon 设备。
  - 缺少所需 Linux sysfs 电池数据或 `applesmc` 接口的设备。

<div align="center" style="background:#f5f5f7;padding:18px 0 10px 0;border-radius:12px;margin-bottom:8px;">
  <img src="assets/apple-173-svgrepo-com.svg" alt="Apple" width="45" style="vertical-align:middle;margin:0 10px;"/>
  <img src="assets/intel-icon.svg" alt="Intel" width="60" style="vertical-align:middle;margin:0 10px;"/>
  <img src="assets/linux-svgrepo-com.svg" alt="Linux" width="60" style="vertical-align:middle;margin:0 10px;"/>
  <img src="assets/apple-laptop-computer-svgrepo-com.svg" alt="Apple Laptop" width="60" style="vertical-align:middle;margin:0 10px;"/>
</div>

### 🛠️ 编译实验性 C 辅助程序
使用 GCC 编译可选的底层辅助程序：
```bash
gcc -O2 smc_control.c -o smc_control
sudo ./smc_control 55  # 尝试写入 55% 的 BCLM 阈值
```

辅助程序需要 root 权限才能直接访问 I/O 端口。请仅在理解该写入尚属实验且程序无法验证结果的情况下运行。

### 🖥️ TUI 监控界面
本项目提供一个基于 Textual 的实时系统信息与事件日志界面。

> [!TIP]
>
> 💡 Python/Textual TUI 的电池、电源、风扇状态监控和日志记录可以独立使用。
>
> 如果只需要监控，建议添加 `--no-charge-control`，或在 `.env` 中设置 `CHARGE_CONTROL_ENABLED=false`，避免执行实验性的 SMC 写入。

1. **安装依赖**：
   ```bash
   # https://gitee.com/wangnov/uv-custom/releases
   curl -LsSf https://gitee.com/wangnov/uv-custom/releases/download/0.10.4/uv-installer-custom.sh | sh
   uv venv # --python <版本号>
   uv pip install -r requirements.txt
   ```

2. **配置**：
   复制 `.env.example` 为 `.env` 并根据需要修改：
   ```bash
   cp .env.example .env
   ```
   可配置项包括 `BATTERY_THRESHOLD`、`CHARGE_CONTROL_ENABLED` 以及控制台和文件日志等级。

3. **以纯监控模式运行**：
   ```bash
   uv run ./smc_tui.py --lang zh-cn --no-charge-control
   ```

只有在明确要以 root 权限测试实验性控制链路时，才移除 `--no-charge-control`。

### 🔋 实验目标行为（尚未验证）

以下行为描述的是实验目标，而不是已经确认的能力：

- 电量低于设定阈值时，连接电源后系统应继续正常充电。
- 电量达到或超过阈值时，辅助程序会尝试通过 sysfs 或 C 程序写入 `BCLM`。
- 固件可能忽略或覆盖该写入，因此即使程序报告尝试成功，设备也可能继续充电。

### ⚙️ 为什么控制实验使用 C

C 辅助程序（`smc_control.c`）使用特权 I/O 操作，与位于 `0x300` 和 `0x304` 的传统 Apple SMC 端口通信。

- `ioperm`、`inb` 和 `outb` 提供该原型所需的底层端口访问能力。
- Linux 要求以 root 权限执行这些操作。

**为什么端口写入成功不能证明控制生效：**
- 辅助程序不会读回 `BCLM`，也不会验证 SMC 是否接受该值。
- SMC 协议细节、时序、数据编码或不同设备的行为可能与当前原型的假设不同。
- 固件或操作系统的电源管理可能拒绝、忽略或随后覆盖该设置尝试。

**总结：**
- C 使直接端口实验成为可能，但尚未证明它足以实现充电控制；Python TUI 仍可独立用于监控和日志记录。

### 🔍 TUI 中可以观察到什么

在纯监控模式下，TUI 只展示可观察到的 sysfs 和 `applesmc` 数据，不会尝试改变充电行为。

- **电池放电时：**
  - 右侧面板显示电量、电流、本地化电池状态、电源连接状态和风扇转速。
  - 事件日志记录检测到的电池状态和电源连接变化。

- **连接电源时：**
  - TUI 会报告连接事件，并显示 Linux 电池驱动提供的状态。
  - 电流、充电状态和主板供电均为观察结果，而不是 TUI 发出的控制命令。

- **电量达到设定阈值时：**
  - 纯监控模式可以记录阈值事件，但不会写入充电限制。
  - 实验性控制模式会尝试执行配置的 sysfs 或 SMC 写入，但不保证生效。

- **评估控制实验时：**
  - 电池电流、驱动状态和 MagSafe 指示灯都是有用信号，但任何单一信号都不能证明 `BCLM` 已生效。
  - 测试时应结合多次测量和系统日志，不要将该原型作为有保证的电池保护机制。

本项目受支持且推荐的用途是实时 TUI 监控和日志记录；充电阈值控制仍是未经验证的实验。
