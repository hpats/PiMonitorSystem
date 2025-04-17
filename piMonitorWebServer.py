import os
import re
import csv
import time
import json
import threading
import subprocess
from datetime import datetime
import socket
from datetime import timedelta

import requests
from flask import Flask, render_template, jsonify

MAX_LINES = 2560

def get_absolute_template_folder_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

app = Flask(__name__, template_folder=get_absolute_template_folder_path())


# =======================
# System Data Collection
# =======================

def get_cpu_core_count():
    try:
        return os.cpu_count()
    except Exception:
        return 1  # safe default

def run_subprocess(command):
    try:
        return subprocess.check_output(command, text=True)
    except Exception as e:
        return f"Error: {e}"

def get_cpu_temperature():
    result = run_subprocess(["/usr/bin/vcgencmd", "measure_temp"])
    if "Error" in result: return result
    return float(result.strip().replace("temp=", "").replace("'C", ""))

def get_ram_usage():
    result = run_subprocess(["free", "-m"])
    if "Error" in result: return result
    values = result.split('\n')[1].split()
    return int(values[2]), int(values[1])

def get_cpu_usage():
    result = run_subprocess(["top", "-bn1"])
    if "Error" in result: return result

    cpu_line = next((line for line in result.split('\n') if '%Cpu(s):' in line), None)
    if not cpu_line: return "Error: '%Cpu(s):' line not found"

    match = re.search(r'%Cpu\(s\):\s+([\d.]+)\s+us,\s+([\d.]+)\s+sy', cpu_line)
    if match:
        return float(match.group(1)) + float(match.group(2))
    return "Error: CPU usage values not found"

def get_disk_space():
    result = run_subprocess(["df", "-h", "/"])
    if "Error" in result: return result
    values = result.split('\n')[1].split()
    used, total = map(lambda x: float(x.replace('G', '')), (values[2], values[1]))
    percentage = f"{(used / total) * 100:.2f}" if total else "0.00"
    return used, total, percentage

def get_wireguard_stats():
    try:
        output = subprocess.check_output(["ifconfig", "wg0"], stderr=subprocess.PIPE, text=True)
        rx = re.search(r'RX packets.*?bytes (\d+) \(', output)
        tx = re.search(r'TX packets.*?bytes (\d+) \(', output)
        return int(tx.group(1)) if tx else 0, int(rx.group(1)) if rx else 0
    except Exception:
        return 0, 0

def get_hostname():
    return socket.gethostname()

def get_local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "Unavailable"


def get_public_ip():
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        return r.json().get("ip", "Unavailable")
    except Exception:
        return "Unavailable"

def get_online_status():
    try:
        requests.get("https://1.1.1.1", timeout=3)
        return "Online"
    except Exception:
        return "Offline"

def get_system_info():
    one, five, fifteen = get_load_average()
    cores = get_cpu_core_count()
    load_percent = (one / cores) * 100 if cores else 0

    return {
        "hostname": get_hostname(),
        "local_ip": get_local_ip(),
        "public_ip": get_public_ip(),
        "status": get_online_status(),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "uptime": get_uptime(),
        "load_1": f"{one:.2f}",
        "load_5": f"{five:.2f}",
        "load_15": f"{fifteen:.2f}",
        "cores": cores,
        "load_percent": f"{load_percent:.1f}%",
        "ping": get_ping_latency(),
        "packet_loss": get_packet_loss(),
        "gateway": get_gateway(),
        "dns": get_dns_servers()
    }


def get_uptime():
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        return str(timedelta(seconds=int(uptime_seconds)))
    except Exception:
        return "Unavailable"

def get_load_average():
    try:
        with open('/proc/loadavg', 'r') as f:
            one, five, fifteen = map(float, f.read().strip().split()[:3])
        return one, five, fifteen
    except Exception:
        return 0.0, 0.0, 0.0

def get_ping_latency(host="8.8.8.8"):
    try:
        output = subprocess.check_output(["ping", "-c", "1", host], stderr=subprocess.DEVNULL, text=True)
        match = re.search(r'time=(\d+\.\d+)', output)
        return float(match.group(1)) if match else None
    except Exception:
        return None

def get_packet_loss(host="8.8.8.8", count=4):
    try:
        output = subprocess.check_output(["ping", "-c", str(count), host], stderr=subprocess.DEVNULL, text=True)
        match = re.search(r'(\d+)% packet loss', output)
        return int(match.group(1)) if match else None
    except Exception:
        return None

def get_gateway():
    try:
        output = subprocess.check_output(["ip", "route", "show", "default"], text=True)
        return output.split()[2] if "default" in output else "Unavailable"
    except Exception:
        return "Unavailable"

def get_dns_servers():
    try:
        with open("/etc/resolv.conf", "r") as f:
            return [line.split()[1] for line in f if line.startswith("nameserver")]
    except Exception:
        return []



# =========================
# External Sensor + Weather
# =========================

def get_sensor_data():
    try:
        r = requests.get("http://192.168.1.206/json-data", timeout=5)
        return r.json() if r.ok else f"Error: {r.status_code}"
    except Exception as e:
        return f"Error: {e}"

def get_weatherGOV_data():
    try:
        r = requests.get("https://api.weather.gov/stations/KLGA/observations/latest", timeout=5)
        return r.json() if r.ok else f"Error: {r.status_code}"
    except Exception as e:
        return f"Error: {e}"


# ==================
# File I/O Functions
# ==================

def _trim_csv(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
    if len(lines) > MAX_LINES:
        with open(filename, 'w', newline='') as f:
            f.writelines(lines[-MAX_LINES:])

def write_system_data_to_csv(data, wg_data):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open('system_data.csv', 'a', newline='') as f:
        csv.writer(f).writerow([timestamp] + data)
    _trim_csv('system_data.csv')

    tx, rx = wg_data
    last_tx, last_rx = 0, 0

    try:
        with open('wg0_data.csv', 'r') as f:
            last_line = f.readlines()[-1].strip()
            parts = last_line.split(',')
            if len(parts) >= 3:
                last_tx = int(parts[1])
                last_rx = int(parts[2])
    except (FileNotFoundError, IndexError, ValueError):
        pass  # Defaults are 0

    diff = [max(tx - last_tx, 0), max(rx - last_rx, 0)]
    with open('wg0_data.csv', 'a', newline='') as f:
        csv.writer(f).writerow([timestamp, tx, rx] + diff)
    _trim_csv('wg0_data.csv')

def write_sensor_data_to_csv(data):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            return f"Error decoding JSON: {e}"

    values = [timestamp] + [data.get(k) for k in ["temperature", "humidity", "pressure", "gas", "pm10", "pm25", "pm100"]]
    with open('weather.csv', 'a', newline='') as f:
        csv.writer(f).writerow(values)
    _trim_csv('weather.csv')


# ============
# Flask Routes
# ============

@app.route('/')
def index():
    try:
        output = subprocess.check_output(["pivpn", "-c"], text=True)
    except subprocess.CalledProcessError as e:
        output = f"Error: {e.output}"
    return render_template('index.html', pivpn_status=output)
    

@app.route('/json_data')
def json_data():
    return jsonify(_csv_to_json('system_data.csv', [
        "date", "temperature", "ram", "maxRam", "cpu", "usedspace",
        "allSpace", "ramperc", "diskperc"
    ]))

@app.route('/json_dataWG')
def json_data_wg():
    return jsonify(_csv_to_json('wg0_data.csv', ["date", "TX", "RX", "TXdiff", "RXdiff"]))

@app.route('/json_data_weather')
def json_data_weather():
    return jsonify(_csv_to_json('weather.csv', [
        "date", "temperature", "humidity", "pressure", "gas", "pm10", "pm25", "pm100"
    ]))


def _csv_to_json(filename, keys):
    with open(filename, 'r') as f:
        return [
            dict(zip(keys, [float(x) if x.replace('.', '', 1).isdigit() else x for x in row]))
            for row in csv.reader(f)
        ]

@app.route('/json_system_info')
def json_system_info():
    return jsonify(get_system_info())


# ====================
# Threaded Backgrounds
# ====================

def update_system_data():
    while True:
        temp = get_cpu_temperature()
        ram_usage = get_ram_usage()
        cpu = get_cpu_usage()
        disk = get_disk_space()
        wg = get_wireguard_stats()

        if isinstance(ram_usage, str) or isinstance(disk, str) or isinstance(cpu, str):
            continue  # skip this round if error

        ram_used, ram_total = ram_usage
        disk_used, disk_total, disk_pct = disk
        ram_pct = f"{(ram_used / ram_total) * 100:.2f}" if ram_total else "0.00"

        data = [temp, ram_used, ram_total, cpu, disk_used, disk_total, ram_pct, disk_pct]
        write_system_data_to_csv(data, wg)
        time.sleep(300)

def update_sensor_data():
    while True:
        data = get_sensor_data()
        write_sensor_data_to_csv(data)
        time.sleep(300)

def start_flask_server():
    app.run(host='0.0.0.0', port=5005)


# ========
# Run App
# ========

if __name__ == "__main__":
    threading.Thread(target=start_flask_server, daemon=True).start()
    threading.Thread(target=update_system_data, daemon=True).start()
    threading.Thread(target=update_sensor_data, daemon=True).start()
    while True:
        time.sleep(1)
