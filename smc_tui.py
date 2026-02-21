
import os
import time
import argparse
import subprocess
import sys
import yaml
from datetime import datetime
from dotenv import load_dotenv
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Log, Label
from textual.reactive import reactive

# 日志目录和文件名
LOG_DIR = "./logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
start_time_str = datetime.now().strftime("%Y%m%d-%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"{start_time_str}_power.log")

# Load environment variables
load_dotenv()


# Global config variables (will be set in main)
CONSOLE_LOG_LEVEL = "info"
FILE_LOG_LEVEL = "info"
LOG_LEVEL = "info"  # 兼容旧变量名
THRESHOLD = 55
BAT_PATH = ""
AC_PATH = ""
I18N = {}
USE_EMOJI = True

LEVELS = {
    "debug": 10,
    "info": 20,
    "warn": 30,
    "error": 40,
    "silent": 50
}

def load_i18n(lang_code, disable_emoji):
    try:
        with open("i18n.yml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: i18n.yml not found.")
        sys.exit(1)

    # Fallback to 'en' if lang_code not found
    if lang_code not in data:
        print(f"Warning: Language '{lang_code}' not found, falling back to 'en'.")
        lang_code = "en"
    
    strings = data[lang_code]
    emojis = data.get("emojis", {}) if not disable_emoji else {}
    
    return strings, emojis

def t(key):
    """Translate key to string, prepending emoji if enabled."""
    text = I18N[0].get(key, key)
    icon = I18N[1].get(key, "")
    return f"{icon}{text}"

class SMCTui(App):
    CSS = """
    Screen {
        background: #1a1a1b;
        overflow: hidden;
        layout: vertical; /* 明确指定 Screen 的布局方式 */
    }

    #title {
        text-align: center;
        width: 100%;
        background: #2980b9;
        color: white;
        text-style: bold;
        height: 1;
        min-height: 1;
        max-height: 1;
    }

    #main_container {
        layout: horizontal; /* 明确主容器是横向排列左右面板 */
        height: 1fr;
        width: 100%;
    }

    #left_panel {
        width: 1fr;
        height: 100%;
        border: solid #3498db;
        padding: 0 1;
        overflow-y: auto;
        /* scrollbar-gutter: stable; */
    }

    #right_panel {
        width: 32;
        height: 100%;
        border: solid #2ecc71;
        padding: 0 1;
        background: #2c3e50;
        overflow-y: auto;
        scrollbar-size: 1 1;
        /* scrollbar-gutter: stable; */
    }

    .info_label {
        text-style: bold;
        color: #f1c40f;
        margin: 0;
        margin-top: 1; /* 增加一点间距感 */
    }

    .info_value {
        color: #ecf0f1;
        /* margin: 0; */
    }

    Log {
        background: transparent;
        color: #bdc3c7;
        height: 1fr; /* 强制填满左侧 */
        border-top: dashed #3498db; /* 给日志加个小分隔线 */
    }
    """

    battery_capacity = reactive(0)
    battery_current = reactive(0)
    battery_status = reactive("N/A")
    ac_online = reactive(False)
    
    last_cap = None
    last_status = None
    last_ac = None
    charging_override_active = False  # True when we've actively stopped charging due to threshold

    def compose(self) -> ComposeResult:
        yield Static(t("title"), id="title")
        with Horizontal(id="main_container"):
            with Vertical(id="left_panel"):
                yield Label(t("realtime_logs"))
                yield Log(id="log_view")
            with Vertical(id="right_panel"):
                yield Label(t("system_info"), classes="info_label")
                yield Label(id="cap_val", classes="info_value")
                yield Label(id="curr_val", classes="info_value")
                yield Label(id="status_val", classes="info_value")
                yield Label(id="ac_val", classes="info_value")
                
                yield Label(t("power_details"), classes="info_label")
                yield Label(id="char_bat", classes="info_value")
                yield Label(id="char_mb", classes="info_value")
                yield Label(id="bat_supp", classes="info_value")

        yield Footer()

    def on_mount(self) -> None:
        msg = t("monitor_started").format(threshold=THRESHOLD)
        self.log_message(msg, "info", "monitor_start")
        self.update_stats() # Populate initial values
        self.set_interval(2.0, self.update_stats)


    def log_message(self, msg: str, level: str = "info", emoji_key: str = None):
        # 控制台日志
        min_level = LEVELS.get(CONSOLE_LOG_LEVEL, 20)
        level_val = LEVELS.get(level.lower(), 20)
        if level_val >= min_level:
            timestamp = datetime.now().strftime("%H:%M:%S")
            color_map = {
                "debug": "[cyan]",
                "info": "[green]",
                "warn": "[yellow]",
                "error": "[red]",
            }
            prefix_color = color_map.get(level.lower(), "[white]")
            lvl_emoji = I18N[1].get(f"log_{level.lower()}", "")
            content_emoji = I18N[1].get(emoji_key, "") if emoji_key else ""
            log_view = self.query_one("#log_view", Log)
            log_view.write_line(f"{lvl_emoji}{prefix_color}[{timestamp}] {level.upper()}: {content_emoji}{msg}[/]")
        # 文件日志
        self.log_message_file(msg, level)

    def log_message_file(self, msg: str, level: str = "info"):
        min_level = LEVELS.get(FILE_LOG_LEVEL, 20)
        level_val = LEVELS.get(level.lower(), 20)
        if level_val < min_level:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level.upper()}: {msg}\n"
        try:
            with open(LOG_FILE, "a") as f:
                f.write(log_entry)
        except Exception:
            pass

    def get_sys_val(self, path, file):
        try:
            full_path = os.path.join(path, file)
            if not os.path.exists(full_path):
                return None
            with open(full_path, 'r') as f:
                return f.read().strip()
        except Exception:
            return None

    def update_stats(self) -> None:
        cap_str = self.get_sys_val(BAT_PATH, "capacity")
        curr_str = self.get_sys_val(BAT_PATH, "current_now")
        stat_str = self.get_sys_val(BAT_PATH, "status")
        ac_str = self.get_sys_val(AC_PATH, "online")

        if cap_str is not None:
            self.battery_capacity = int(cap_str)
        if curr_str is not None:
            # current_now is typically in microamperes
            self.battery_current = abs(int(curr_str)) // 1000
        if stat_str is not None:
            self.battery_status = stat_str
        if ac_str is not None:
            self.ac_online = ac_str == "1"

        # Update UI Labels
        self.query_one("#cap_val", Label).update(f"{t('capacity')} {self.battery_capacity}%")
        self.query_one("#curr_val", Label).update(f"{t('current')} {self.battery_current} mA")
        self.query_one("#status_val", Label).update(f"{t('status')} {self.battery_status}")
        
        ac_text = t("connected") if self.ac_online else t("disconnected")
        self.query_one("#ac_val", Label).update(f"{t('ac_power')} {ac_text}")
        
        # Power source details
        charging_bat = self.battery_status == "Charging"
        charging_mb = self.ac_online
        bat_supplying = self.battery_status == "Discharging"

        yes = t("yes")
        no = t("no")
        
        # Icons for boolean states
        cb_icon = I18N[1].get("char_bat_yes" if charging_bat else "char_bat_no", "")
        cmb_icon = I18N[1].get("char_mb_yes" if charging_mb else "char_mb_no", "")
        bs_icon = I18N[1].get("bat_supp_yes" if bat_supplying else "bat_supp_no", "")

        self.query_one("#char_bat", Label).update(f"{I18N[0].get('char_bat_label', '')} {cb_icon}{yes if charging_bat else no}")
        self.query_one("#char_mb", Label).update(f"{I18N[0].get('char_mb_label', '')} {cmb_icon}{yes if charging_mb else no}")
        self.query_one("#bat_supp", Label).update(f"{I18N[0].get('bat_supp_label', '')} {bs_icon}{yes if bat_supplying else no}")



        # Active Charge Control Logic
        if self.ac_online and self.battery_status == "Charging" and self.battery_capacity >= THRESHOLD:
            if not self.charging_override_active:
                msg = t("threshold_crossed").format(threshold=THRESHOLD, capacity=self.battery_capacity)
                self.log_message(msg, "warn", "threshold_cross")
                self.log_message_file(f"电量跨越阈值! 当前电量: {self.battery_capacity}%", "warn")
                self._stop_charging()
                self.charging_override_active = True
        elif self.battery_capacity < THRESHOLD - 3 and self.charging_override_active:
            self._start_charging()
            self.charging_override_active = False
            self.log_message_file(f"电量回落至阈值以下，恢复充电: {self.battery_capacity}%", "info")

        # Logging Logic
        if self.last_cap is not None:
            if self.battery_capacity == THRESHOLD and self.last_cap != THRESHOLD:
                msg = t("threshold_reached").format(threshold=THRESHOLD)
                self.log_message(msg, "info", "threshold_reach")

        # 关键事件文件日志
        if self.last_status != self.battery_status and self.last_status is not None:
            msg = t("status_changed").format(old=self.last_status, new=self.battery_status)
            self.log_message(msg, "info", "status_change")
            self.log_message_file(f"充电状态变更: {self.last_status} -> {self.battery_status}", "info")

        if self.last_ac != self.ac_online and self.last_ac is not None:
            msg = t("ac_connected") if self.ac_online else t("ac_disconnected")
            emoji_key = "ac_connect" if self.ac_online else "ac_disconnect"
            self.log_message(msg, "info", emoji_key)
            self.log_message_file(f"外部电源{'接入' if self.ac_online else '断开'}", "info")

        # 主板/电池供电切换
        if self.last_status is not None and self.last_status != self.battery_status:
            if self.battery_status == "Discharging":
                self.log_message_file("电池供电开始", "info")
            elif self.battery_status == "Charging":
                self.log_message_file("主板供电开始（充电）", "info")
            elif self.battery_status == "Full" or self.battery_status == "Not charging":
                self.log_message_file("主板供电（不充电）", "info")

        self.last_cap = self.battery_capacity
        self.last_status = self.battery_status
        self.last_ac = self.ac_online

    def _stop_charging(self) -> None:
        """Stop battery charging by enforcing THRESHOLD via sysfs or SMC binary."""
        # Method 1: sysfs charge_control_end_threshold (supported by some kernels/drivers)
        end_threshold_path = os.path.join(BAT_PATH, "charge_control_end_threshold")
        if os.path.exists(end_threshold_path):
            try:
                with open(end_threshold_path, 'w') as f:
                    f.write(str(THRESHOLD))
                self.log_message(f"已通过 sysfs 设置充电上限: {THRESHOLD}%", "info")
                return
            except Exception as e:
                self.log_message(f"sysfs 写入失败: {e}，尝试 SMC 二进制", "warn")

        # Method 2: smc_control binary (writes Apple SMC BCLM key)
        bin_path = os.path.join(os.path.dirname(__file__), "smc_control")
        if os.path.exists(bin_path) and os.access(bin_path, os.X_OK):
            try:
                subprocess.run([bin_path, str(THRESHOLD)], check=True)
                self.log_message(f"已通过 SMC 写入 BCLM={THRESHOLD}，充电已限制", "info")
            except subprocess.CalledProcessError as e:
                self.log_message(f"SMC 写入失败: {e}", "error")
        else:
            self.log_message("smc_control 未找到或不可执行，无法停止充电！", "error")

    def _start_charging(self) -> None:
        """Resume normal charging by resetting the charge limit to 100%."""
        # Method 1: sysfs
        end_threshold_path = os.path.join(BAT_PATH, "charge_control_end_threshold")
        if os.path.exists(end_threshold_path):
            try:
                with open(end_threshold_path, 'w') as f:
                    f.write("100")
                self.log_message("已通过 sysfs 恢复充电 (上限 100%)", "info")
                return
            except Exception as e:
                self.log_message(f"sysfs 恢复失败: {e}，尝试 SMC 二进制", "warn")

        # Method 2: smc_control binary
        bin_path = os.path.join(os.path.dirname(__file__), "smc_control")
        if os.path.exists(bin_path) and os.access(bin_path, os.X_OK):
            try:
                subprocess.run([bin_path, "100"], check=True)
                self.log_message("已通过 SMC 写入 BCLM=100，充电已恢复", "info")
            except subprocess.CalledProcessError as e:
                self.log_message(f"SMC 恢复失败: {e}", "error")

if __name__ == "__main__":
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="SMC TUI monitor")
    parser.add_argument("threshold", nargs="?", type=int, help="Initial battery threshold (0-100)")
    parser.add_argument("--lang", default="en", help="Language code (en, zh-cn), default: en")
    parser.add_argument("--disable-emoji", action="store_true", help="Disable emojis in UI")
    args = parser.parse_args()


    # Load Config from .env and CLI
    CONSOLE_LOG_LEVEL = os.getenv("CONSOLE_LOG_LEVEL", os.getenv("LOG_LEVEL", "info")).lower()
    FILE_LOG_LEVEL = os.getenv("FILE_LOG_LEVEL", os.getenv("LOG_LEVEL", "info")).lower()
    LOG_LEVEL = CONSOLE_LOG_LEVEL  # 兼容旧变量名
    BAT_PATH = os.getenv("BAT_PATH", "/sys/class/power_supply/BAT0")
    AC_PATH = os.getenv("AC_PATH", "/sys/class/power_supply/ADP1")
    # Threshold Logic: CLI arg > .env > default 55
    cli_threshold = args.threshold
    env_threshold = int(os.getenv("BATTERY_THRESHOLD", "55"))
    chosen_threshold = cli_threshold if cli_threshold is not None else env_threshold
    THRESHOLD = chosen_threshold
    # Load I18N
    I18N = load_i18n(args.lang.lower(), args.disable_emoji)
    USE_EMOJI = not args.disable_emoji

    # Root check
    if os.name != 'nt':
        try:
            if os.geteuid() != 0:
                print("Error: this script must be run as root (sudo).")
                sys.exit(1)
        except AttributeError:
            pass

    # Call binary
    bin_path = os.path.join(os.path.dirname(__file__), "smc_control")
    if os.path.exists(bin_path) and os.access(bin_path, os.X_OK):
        try:
            subprocess.run([bin_path, str(chosen_threshold)], check=True)
            print(f"Called {bin_path} {chosen_threshold}")
        except subprocess.CalledProcessError as e:
            print(f"Error: calling {bin_path} failed: {e}")
    else:
        print(f"Warning: binary '{bin_path}' not found or not executable.")

    app = SMCTui()
    app.run()
