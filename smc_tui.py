import os
import time
import argparse
import subprocess
import sys
from datetime import datetime
from dotenv import load_dotenv
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Log, Label
from textual.reactive import reactive

# Load environment variables
load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()
THRESHOLD = int(os.getenv("BATTERY_THRESHOLD", "55"))
BAT_PATH = os.getenv("BAT_PATH", "/sys/class/power_supply/BAT0")
AC_PATH = os.getenv("AC_PATH", "/sys/class/power_supply/ADP1")

LEVELS = {
    "debug": 10,
    "info": 20,
    "warn": 30,
    "error": 40,
    "silent": 50
}
MIN_LOG_LEVEL = LEVELS.get(LOG_LEVEL, 20)

class SMCTui(App):
    CSS = """
    Screen {
        background: #1a1a1b;
    }

    #main_container {
        height: 100%;
        margin: 1;
    }

    #left_panel {
        width: 61.8%;
        height: 100%;
        border: solid #3498db;
        padding: 1;
    }

    #right_panel {
        width: 38.2%;
        height: 100%;
        border: solid #2ecc71;
        padding: 1;
        background: #2c3e50;
    }

    .info_label {
        text-style: bold;
        color: #f1c40f;
        margin-bottom: 1;
    }

    .info_value {
        color: #ecf0f1;
        margin-bottom: 1;
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
        padding: 1;
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
        yield Header()
        yield Static("SMC Control & Battery Monitor", id="title")
        with Horizontal(id="main_container"):
            with Vertical(id="left_panel"):
                yield Label("Real-time Logs")
                yield Log(id="log_view")
            with Vertical(id="right_panel"):
                yield Label("System Info", classes="info_label")
                yield Label("Capacity:", classes="info_label")
                yield Label("0%", id="cap_val", classes="info_value")
                yield Label("Current:", classes="info_label")
                yield Label("0 mA", id="curr_val", classes="info_value")
                yield Label("Status:", classes="info_label")
                yield Label("N/A", id="status_val", classes="info_value")
                yield Label("AC Power:", classes="info_label")
                yield Label("Disconnected", id="ac_val", classes="info_value")
                
                yield Label("\nPower Details:", classes="info_label")
                yield Label("- Charging Battery: No", id="char_bat", classes="info_value")
                yield Label("- Charging Motherboard: No", id="char_mb", classes="info_value")
                yield Label("- Battery Supplying: No", id="bat_supp", classes="info_value")
        yield Footer()

    def on_mount(self) -> None:
        self.log_message(f"Monitor started (Threshold: {THRESHOLD}%)", "info")
        self.set_interval(2.0, self.update_stats)

    def log_message(self, msg: str, level: str = "info"):
        level_val = LEVELS.get(level.lower(), 20)
        if level_val < MIN_LOG_LEVEL:
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "debug": "[cyan]",
            "info": "[green]",
            "warn": "[yellow]",
            "error": "[red]",
        }
        prefix = color_map.get(level.lower(), "[white]")
        log_view = self.query_one("#log_view", Log)
        log_view.write_line(f"{prefix}[{timestamp}] {level.upper()}: {msg}[/]")

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
        self.query_one("#cap_val", Label).update(f"{self.battery_capacity}%")
        self.query_one("#curr_val", Label).update(f"{self.battery_current} mA")
        self.query_one("#status_val", Label).update(self.battery_status)
        self.query_one("#ac_val", Label).update("Connected" if self.ac_online else "Disconnected")
        
        # Power source details
        charging_bat = self.battery_status == "Charging"
        charging_mb = self.ac_online
        bat_supplying = self.battery_status == "Discharging"

        self.query_one("#char_bat", Label).update(f"- Charging Battery: {'Yes' if charging_bat else 'No'}")
        self.query_one("#char_mb", Label).update(f"- Charging Motherboard: {'Yes' if charging_mb else 'No'}")
        self.query_one("#bat_supp", Label).update(f"- Battery Supplying: {'Yes' if bat_supplying else 'No'}")

        # Logging Logic
        if self.last_cap is not None:
            # Threshold crossing
            if (self.last_cap <= THRESHOLD and self.battery_capacity > THRESHOLD) or \
               (self.last_cap >= THRESHOLD and self.battery_capacity < THRESHOLD):
                self.log_message(f"⚠️ Battery threshold {THRESHOLD}% crossed! Current: {self.battery_capacity}%", "warn")
            elif self.battery_capacity == THRESHOLD and self.last_cap != THRESHOLD:
                self.log_message(f"🎯 Battery reached threshold: {THRESHOLD}%", "info")

        # Status change logging
        if self.last_status != self.battery_status and self.last_status is not None:
            self.log_message(f"🔋 Status changed: {self.last_status} -> {self.battery_status}", "info")
            self.log_message(f"Detail: Charging Bat: {charging_bat}, Supplying: {bat_supplying}", "debug")

        if self.last_ac != self.ac_online and self.last_ac is not None:
            self.log_message(f"🔌 AC Power {'Connected' if self.ac_online else 'Disconnected'}", "info")
            self.log_message(f"Charging Motherboard: {charging_mb}", "debug")

        self.last_cap = self.battery_capacity
        self.last_status = self.battery_status
        self.last_ac = self.ac_online

if __name__ == "__main__":
    # Parse optional threshold argument: `python smc_tui.py 55`
    parser = argparse.ArgumentParser(description="SMC TUI monitor (optionally set initial threshold)")
    parser.add_argument("threshold", nargs="?", type=int, help="Initial battery threshold to set (0-100)")
    args = parser.parse_args()

    # Determine threshold: CLI arg > .env > default 55
    cli_threshold = args.threshold
    env_threshold = int(os.getenv("BATTERY_THRESHOLD", "55"))
    chosen_threshold = cli_threshold if cli_threshold is not None else env_threshold

    # Ensure running as root on Unix-like systems
    if os.name != 'nt':
        try:
            if os.geteuid() != 0:
                print("Error: this script must be run as root (sudo).")
                sys.exit(1)
        except AttributeError:
            pass

    # Attempt to call the compiled C helper if present
    bin_path = os.path.join(os.path.dirname(__file__), "smc_control")
    if os.path.exists(bin_path) and os.access(bin_path, os.X_OK):
        try:
            subprocess.run([bin_path, str(chosen_threshold)], check=True)
            print(f"Called {bin_path} {chosen_threshold}")
        except subprocess.CalledProcessError as e:
            print(f"Error: calling {bin_path} failed: {e}")
    else:
        print(f"Warning: binary '{bin_path}' not found or not executable. Please compile it manually:\n  gcc -O2 smc_control.c -o smc_control")

    # Override runtime threshold used by the app
    THRESHOLD = chosen_threshold

    app = SMCTui()
    app.run()
