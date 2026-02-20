# 🛡️ mac-smc-bat-guardian

[English](readme.md) | [中文说明](readme.zh-cn.md)

## 🚀 Project Introduction
This project manages the battery charging threshold (BCLM) by directly interacting with the SMC (System Management Controller) ports of a MacBook, while providing real-time power monitoring. 
It primarily addresses the issue where TLP cannot control the charging threshold of MacBooks through standard drivers in a Linux environment.

### 💻 Device Compatibility
This tool is primarily intended for **Intel x86_64** architecture MacBook devices that manage power via **SMC**.
- **Verified**: MacBook Pro 11,4 A1398(Mid 2015)
> My Device Info:
![my_device_macbook_pro_11_4_A1398.png](my_device_macbook_pro_11_4_A1398.png)
- **Theoretical Support**: Most MacBook Pro/Air models from 2006 to 2020 (Intel chips). These devices typically include the `applesmc` driver and support the `BCLM` key.
- **Unsupported**: 
  - M1/M2/M3 (Apple Silicon) devices (they use a different, proprietary power management mechanism).
  - Very old MacBooks that do not have battery charging threshold control capabilities.

### 🛠️ Build and Run
Compile the low-level C program using GCC:
```bash
gcc -O2 smc_control.c -o smc_control
sudo ./smc_control 55  # Set limit to 55%
```

### 🖥️ TUI Monitoring Interface
The project includes a sophisticated TUI monitoring interface built with Textual.

1. **Install Dependencies**:
   ```bash
   # https://gitee.com/wangnov/uv-custom/releases
   curl -LsSf https://raw.githubusercontent.com/astral-sh/uv/main/install.sh | sh
   uv venv # --python <version>
   uv pip install -r requirements.txt
   ```

2. **Configuration**:
   Copy `.env.example` to `.env` and modify as needed:
   ```bash
   cp .env.example .env
   ```
   You can configure `LOG_LEVEL` (debug, info, warn, error, silent) and `BATTERY_THRESHOLD`.

3. **Run**:
   ```bash
   uv run python smc_tui.py
   ```

### 🔋 Expected Power Delivery Behavior

- [0% - 55%]: Charging logic active, MagSafe light is orange, `current_now` > 0.
- [> 55%]: Cut-off triggered. SMC forcibly cuts off the current flowing to the battery.
