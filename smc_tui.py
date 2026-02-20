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

# Load environment variables
load_dotenv()

# Global config variables (will be set in main)
LOG_LEVEL = "info"
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
    }

    #main_container {
        height: 100%;
        margin: 0;
    }

    #left_panel {
        width: 1fr;
        height: 100%;
        border: solid #3498db;
        padding: 0 1;
    }

    #right_panel {
        width: 32;
        height: 100%;
        border: solid #2ecc71;
        padding: 0 1;
        background: #2c3e50;
    }

    .info_label {
        text-style: bold;
        color: #f1c40f;
        margin: 0;
    }

    .info_value {
        color: #ecf0f1;
        margin: 0;
    }

    Log {
        background: transparent;
        color: #bdc3c7;
    }

    #title {
        text-align: center;
        width: 100%;
        background: #2980b9;
        color: white;
        text-style: bold;
    }
    """

    battery_capacity = reactive(0)
    battery_current = reactive(0)
    battery_status = reactive("N/A")
    ac_online = reactive(False)
    
    last_cap = None
    last_status = None
    last_ac = None

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
        min_level = LEVELS.get(LOG_LEVEL, 20)
        level_val = LEVELS.get(level.lower(), 20)
        
        if level_val < min_level:
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "debug": "[cyan]",
            "info": "[green]",
            "warn": "[yellow]",
            "error": "[red]",
        }
        prefix_color = color_map.get(level.lower(), "[white]")
        
        # Emoji logic
        lvl_emoji = I18N[1].get(f"log_{level.lower()}", "")
        content_emoji = I18N[1].get(emoji_key, "") if emoji_key else ""
        
        log_view = self.query_one("#log_view", Log)
        log_view.write_line(f"{lvl_emoji}{prefix_color}[{timestamp}] {level.upper()}: {content_emoji}{msg}[/]")

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


        # Logging Logic
        if self.last_cap is not None:
            # Threshold crossing
            if (self.last_cap <= THRESHOLD and self.battery_capacity > THRESHOLD) or \
               (self.last_cap >= THRESHOLD and self.battery_capacity < THRESHOLD):
                msg = t("threshold_crossed").format(threshold=THRESHOLD, capacity=self.battery_capacity)
                self.log_message(msg, "warn", "threshold_cross")
            elif self.battery_capacity == THRESHOLD and self.last_cap != THRESHOLD:
                msg = t("threshold_reached").format(threshold=THRESHOLD)
                self.log_message(msg, "info", "threshold_reach")

        # Status change logging
        if self.last_status != self.battery_status and self.last_status is not None:
             msg = t("status_changed").format(old=self.last_status, new=self.battery_status)
             self.log_message(msg, "info", "status_change")

        if self.last_ac != self.ac_online and self.last_ac is not None:
            msg = t("ac_connected") if self.ac_online else t("ac_disconnected")
            emoji_key = "ac_connect" if self.ac_online else "ac_disconnect"
            self.log_message(msg, "info", emoji_key)

        self.last_cap = self.battery_capacity
        self.last_status = self.battery_status
        self.last_ac = self.ac_online

if __name__ == "__main__":
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="SMC TUI monitor")
    parser.add_argument("threshold", nargs="?", type=int, help="Initial battery threshold (0-100)")
    parser.add_argument("--lang", default="en", help="Language code (en, zh-cn), default: en")
    parser.add_argument("--disable-emoji", action="store_true", help="Disable emojis in UI")
    args = parser.parse_args()

    # Load Config from .env and CLI
    LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()
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
