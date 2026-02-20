#!/usr/bin/env python3
import time
import os
from datetime import datetime

# --- 配置区 ---
THRESHOLD = 55
BAT_PATH = "/sys/class/power_supply/BAT0"
LOG_DIR = "./logs"

# 确保日志目录存在
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 每次启动生成带时间戳的新日志文件名
# 格式: YYYYMMDD-HHMMSS_power.log
start_time_str = datetime.now().strftime("%Y%m%d-%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"{start_time_str}_power.log")

def get_val(file):
    try:
        with open(f"{BAT_PATH}/{file}", 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "N/A"

def log_event(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {msg}\n"
    with open(LOG_FILE, "a") as f:
        f.write(log_entry)
    print(f"\n📝 日志更新: {msg}")

# 初始化状态
try:
    current_cap = int(get_val("capacity"))
    current_status = get_val("status")
except ValueError:
    print("❌ 错误: 无法读取电池信息，请检查驱动。")
    exit(1)

last_cap = current_cap
last_status = current_status

print(f"🚀 监控已启动")
print(f"📂 日志文件: {LOG_FILE}")
print(f"🎯 养生阈值: {THRESHOLD}%")
print(f"-------------------------------------------")

try:
    while True:
        cap = int(get_val("capacity"))
        # current_now 在部分内核可能需要转换为正数
        curr = abs(int(get_val("current_now"))) 
        status = get_val("status")

        # 逻辑 1: 监控电量跨越阈值点 (Critical Cross)
        if (last_cap <= THRESHOLD and cap > THRESHOLD) or (last_cap >= THRESHOLD and cap < THRESHOLD):
            log_event(f"⚠️ 电量跨越阈值点! 当前电量: {cap}%")

        # 逻辑 2: 监控充电状态切换 (Mode Switch)
        if status != last_status:
            # 如果电流为 0，说明进入了直供电模式
            mode_desc = "直供模式/充满" if curr == 0 else ("充电中" if "Charg" in status else "放电中")
            log_event(f"🔋 状态变更: {last_status} -> {status} | 电流: {curr}mA | 模式: {mode_desc}")

        # 实时 CLI 刷新输出
        # \r 让输出保持在同一行
        print(f"\r[实时] 电量: {cap}% | 电流: {curr:5}mA | 状态: {status:12}", end="", flush=True)

        last_cap = cap
        last_status = status
        
        time.sleep(5) # 每 5 秒巡检一次
except KeyboardInterrupt:
    log_event("🛑 监控脚本由用户停止。")
    print("\n再见！")
