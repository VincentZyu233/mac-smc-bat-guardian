#!/usr/bin/env python3
import os
import sys
import subprocess

# 颜色定义
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
END = "\033[0m"

# 配置文件路径
TURBO_PATH = "/sys/devices/system/cpu/intel_pstate/no_turbo"

def check_root():
    if os.geteuid() != 0:
        print(f"{RED}{BOLD}❌ 错误:{END} 此脚本需要修改系统文件，请使用 {YELLOW}sudo{END} 运行！")
        sys.exit(1)

def run_cmd(cmd):
    try:
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        pass # 部分环境可能不支持某些 cpupower 参数，跳过

def print_help():
    help_text = f"""
{CYAN}{BOLD}💻 MacBook Pro 动力调度管理器{END}
{CYAN}--------------------------------------------------{END}
{BOLD}用法:{END}
    sudo python3 mac_power.py {YELLOW}[参数]{END}

{BOLD}参数说明:{END}
    {GREEN}quiet{END} (conservative) : {BOLD}保守模式{END}
        - 禁用 Intel 睿频 (Turbo Boost)
        - 限制频率区间: 0.9GHz - 2.0GHz
        - 强制 TLP 进入电池模式 (压制功耗与发热)
        - {CYAN}适用场景: 办公、下载、MagSafe 接口发烫严重时{END}

    {RED}beast{END} (crazy) : {BOLD}性能模式{END}
        - 开启 Intel 睿频
        - 恢复频率上限: 0.9GHz - 3.4GHz
        - 强制 TLP 进入交流电模式
        - {CYAN}适用场景: 编译代码、渲染、电池电量充足且环境凉快时{END}

    {CYAN}status{END} (s) : {BOLD}查看当前硬件状态{END}
        - 显示睿频开关、实时主频、核心温差

{CYAN}--------------------------------------------------{END}
    """
    print(help_text)

def get_status():
    print(f"\n{BOLD}🔍 当前硬件监控数据:{END}")
    print(f"{CYAN}--------------------------------------------------{END}")

    # 睿频状态
    with open(TURBO_PATH, 'r') as f:
        status = f.read().strip()
        turbo_str = f"{RED}已开启 (高热){END}" if status == '0' else f"{GREEN}已禁用 (冷静){END}"
    print(f"🚀 Intel 睿频状态: {turbo_str}")

    # 实时频率
    print(f"📊 实时主频详情:")
    subprocess.run("cpupower frequency-info | grep 'current CPU frequency'", shell=True)

    # 核心温度与温差
    print(f"🌡️ 核心温度 (注意温差):")
    subprocess.run("sensors | grep -E 'Core|TC[0-9]C'", shell=True)
    print(f"{CYAN}--------------------------------------------------{END}\n")

def set_mode(mode):
    if mode == "quiet":
        print(f"\n{GREEN}🍃 正在切换至 [保守模式]...{END}")
        # 1. 禁用睿频
        with open(TURBO_PATH, 'w') as f:
            f.write('1')
        # 2. 限制频率上限
        run_cmd("cpupower frequency-set -d 0.9GHz -u 2.0GHz")
        # 3. 切换 TLP
        run_cmd("tlp bat")
        print(f"{GREEN}✅ 降温策略已生效！{END}")

    elif mode == "beast":
        print(f"\n{RED}🔥 正在切换至 [疯狂模式]...{END}")
        # 1. 开启睿频
        with open(TURBO_PATH, 'w') as f:
            f.write('0')
        # 2. 解锁频率
        run_cmd("cpupower frequency-set -d 0.9GHz -u 3.4GHz")
        # 3. 切换 TLP
        run_cmd("tlp ac")
        print(f"{RED}🚀 性能已释放！请注意监控 MagSafe 接口温度。{END}")

    # 切换完后自动打印一次状态
    get_status()

if __name__ == "__main__":
    check_root()

    if len(sys.argv) < 2 or sys.argv[1] in ["--help", "-h", "help"]:
        print_help()
        sys.exit(0)

    arg = sys.argv[1].lower()
    if arg in ["quiet", "conservative"]:
        set_mode("quiet")
    elif arg in ["beast", "crazy"]:
        set_mode("beast")
    elif arg in ["status", "s"]:
        get_status()
    else:
        print(f"{RED}❓ 未知参数: {arg}{END}")
        print_help()