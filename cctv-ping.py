import json
import os
import platform
import subprocess
import time
from datetime import datetime

# ==========================================
# CONFIGURATION & CAMERA MANAGEMENT (SRS Scope 1)
# ==========================================
# Configure your camera inventory here.
# Fields required by SRS: Camera Name, IP Address, Location
CAMERAS = [
    {
        "name": "Front Gate Bullet",
        "ip": "192.168.1.50",
        "location": "Main Entrance Gate",
    },
    # {"name": "Backyard Dome", "ip": "192.168.1.51", "location": "Rear Perimeter Wall"},
    # {"name": "Warehouse Corridor", "ip": "192.168.1.52", "location": "Loading Dock A"},
]

# Configurable Interval in seconds (SRS Default: 60 seconds)
CHECK_INTERVAL = 60

# Output reporting file paths
JSON_REPORT_FILE = "camera_status_report.json"


# ==========================================
# SYSTEM CORE FUNCTIONS
# ==========================================


def ping_host(ip_address):
    """
    Monitors network availability using native OS ping execution.
    Returns True if Online, False if Offline.
    """
    current_os = platform.system().lower()

    # Configure low timeout flags to keep checks lightweight
    if current_os == "windows":
        command = ["ping", "-n", "1", "-w", "1000", ip_address]
    else:
        command = ["ping", "-c", "1", "-W", "1", ip_address]

    try:
        result = subprocess.run(
            command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, TimeoutError):
        return False


def run_monitoring_cycle(camera_inventory, track_records):
    """
    Executes a single periodic monitoring cycle across the network scope.
    """
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Initial status metrics tracking variables
    total_cameras = len(camera_inventory)
    online_count = 0
    offline_count = 0

    cycle_results = []

    for cam in camera_inventory:
        ip = cam["ip"]
        name = cam["name"]
        location = cam["location"]

        # Execute network availability ping test
        is_online = ping_host(ip)
        status_label = "Online" if is_online else "Offline"

        # Manage and update persistent "Last Successful Check" tracking data
        if is_online:
            online_count += 1
            track_records[ip] = current_time_str
        else:
            offline_count += 1
            # Maintain existing historical stamp or mark N/A if it hasn't succeeded yet
            if ip not in track_records:
                track_records[ip] = "N/A (Never detected online since script start)"

        # Build individual JSON camera records block
        camera_data = {
            "camera_name": name,
            "ip_address": ip,
            "location": location,
            "status": status_label,
            "last_successful_check": track_records[ip],
        }
        cycle_results.append(camera_data)

    # Compile the final reporting schema structure
    report_payload = {
        "timestamp": current_time_str,
        "summary": {
            "total_cameras_monitored": total_cameras,
            "online_cameras": online_count,
            "offline_cameras": offline_count,
        },
        "cameras": cycle_results,
    }

    # ==========================================
    # DISPLAY & REPORTING EXPORT (SRS Scope 3 & 4)
    # ==========================================

    # 1. Print real-time status output block to standard terminal interface
    print(f"\n==============================================")
    print(f" CCTV MONITORING STATUS DISPLAY: {current_time_str}")
    print(f"==============================================")
    print(f" [SUMMARY VIEW]")
    print(f" Total Monitored : {total_cameras}")
    print(f" 🟢 Online       : {online_count}")
    print(f" 🔴 Offline      : {offline_count}")
    print(f"----------------------------------------------")
    print(
        f" {'CAMERA NAME':<20} {'IP ADDRESS':<15} {'STATUS':<10} {'LAST SUCCESSFUL CHECK'}"
    )
    print(f"----------------------------------------------")
    for cam in cycle_results:
        status_icon = "🟢" if cam["status"] == "Online" else "🔴"
        print(
            f" {cam['camera_name']:<20} {cam['ip_address']:<15} {status_icon} {cam['status']:<7} {cam['last_successful_check']}"
        )
    print(f"==============================================")

    # 2. Export updated JSON data structure safely to file disk space
    try:
        with open(JSON_REPORT_FILE, "w", encoding="utf-8") as json_file:
            json.dump(report_payload, json_file, indent=4)
        print(f"✔️ System monitoring results exported to: '{JSON_REPORT_FILE}'")
    except IOError as e:
        print(f"❌ Error writing status records to JSON target file: {e}")


def main():
    # Cache lookup map runtime container for "Last Successful Check" memory retention
    successful_check_memory = {}

    print("Initializing Automated CCTV Integrity Monitoring System...")
    print(f"Target Check Cycle Interval: {CHECK_INTERVAL} seconds.")
    print("Press Ctrl+C inside terminal loop to abort tracking safely.\n")

    try:
        while True:
            run_monitoring_cycle(CAMERAS, successful_check_memory)
            print(f"\nSleeping for {CHECK_INTERVAL} seconds...")
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print(
            "\nProcess execution terminated safely by user prompt. Closing down monitoring scopes."
        )


if __name__ == "__main__":
    main()
