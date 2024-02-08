import subprocess
import time
import csv
from datetime import datetime
from flask import Flask, render_template, jsonify
import threading
import os
import re

MAX_LINES = 2560

app = Flask(__name__, template_folder='templates')

def get_absolute_template_folder_path():
    script_folder = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_folder, 'templates')

app = Flask(__name__, template_folder=get_absolute_template_folder_path())

def get_cpu_temperature():
    try:
        result = subprocess.check_output(["/usr/bin/vcgencmd", "measure_temp"])
        temperature_str = result.decode("utf-8").strip()
        temperature_value = float(temperature_str.replace("temp=", "").replace("'C", ""))
        return temperature_value
    except Exception as e:
        return f"Error: {e}"

def get_ram_usage():
    try:
        result = subprocess.check_output(["free", "-m"])
        lines = result.decode("utf-8").split('\n')[1].split()
        ram_used = int(lines[2])
        ram_total = int(lines[1])
        return ram_used, ram_total
    except Exception as e:
        return f"Error: {e}"

def get_cpu_usage():
    try:
        result = subprocess.check_output(["top", "-bn1"])
        lines = result.decode("utf-8").split('\n')
        cpu_line = [line for line in lines if line.startswith("%Cpu(s):")][0]
        cpu_usage = float(cpu_line.split()[1])
        return cpu_usage
    except Exception as e:
        return f"Error: {e}"

def calculate_disk_percentage(used_space, total_space):
    if total_space == 0:
        return 0
    return (used_space / total_space) * 100

def get_disk_space():
    try:
        result = subprocess.check_output(["df", "-h", "/"])
        lines = result.decode("utf-8").split('\n')[1].split()
        disk_used = float(lines[2].replace('G', ''))  # Assuming disk space is in GB
        disk_total = float(lines[1].replace('G', ''))
        return disk_used, disk_total, "{:.2f}".format(calculate_disk_percentage(disk_used, disk_total))
    except Exception as e:
        return f"Error: {e}"

def calculate_ram_percentage(ram_used, ram_total):
    if ram_total == 0:
        return 0
    return (ram_used / ram_total) * 100

def get_wireguard_stats():
    try:
        ifconfig_output = subprocess.check_output(["ifconfig", "wg0"], stderr=subprocess.PIPE, universal_newlines=True)
        rx_bytes_match = re.search(r'RX packets.*?bytes (\d+) \(', ifconfig_output)
        if rx_bytes_match:
            rx_packets = int(rx_bytes_match.group(1))
        else:
            print("RX Packets Bytes not found")

        tx_bytes_match = re.search(r'TX packets.*?bytes (\d+) \(', ifconfig_output)
        if tx_bytes_match:
            tx_packets = int(tx_bytes_match.group(1))
        else:
            print("TX Packets Bytes not found")
        return tx_packets, rx_packets
    except Exception as e:
        return 0, 0  # Return default values in case of an error

def write_system_data_to_csv(data, wg_data):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data_with_timestamp = [timestamp] + data
    wg_data_with_timestamp = [timestamp] + wg_data
    with open('system_data.csv', 'a', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(data_with_timestamp)

    # Check and remove the oldest line if the number of lines exceeds MAX_LINES
    with open('system_data.csv', 'r') as csvfile:
        lines = csvfile.readlines()
        if len(lines) > MAX_LINES:
            lines = lines[1:]

    with open('system_data.csv', 'w', newline='') as csvfile:
        csvfile.writelines(lines)

    try:
        first_time = False
        with open('wg0_data.csv', 'r') as csvfile:
            lines = csvfile.readlines()
            if lines:
                last_row_values = lines[-1].strip().split(',')
                print(last_row_values)
                last_values = int(last_row_values[-4]), int(last_row_values[-3])
            else:
                last_values = 0, 0
    except FileNotFoundError:
        # Handle the case where the file doesn't exist yet
        first_time = True
        last_values = 0, 0

    smaller_than_old_values = wg_data_with_timestamp[1] < last_values[0] or wg_data_with_timestamp[2] < last_values[1]
    difference = (wg_data_with_timestamp[1] - last_values[0], wg_data_with_timestamp[2] - last_values[1])

    print(smaller_than_old_values, wg_data_with_timestamp[1], last_values[0], wg_data_with_timestamp[1] < last_values[0], wg_data_with_timestamp[2] < last_values[1],
          wg_data_with_timestamp[2], last_values[1])

    if smaller_than_old_values or first_time:
        stored_data = (wg_data_with_timestamp[0], wg_data_with_timestamp[1], wg_data_with_timestamp[2], 0, 0)
    else:
        stored_data = (wg_data_with_timestamp[0], wg_data_with_timestamp[1], wg_data_with_timestamp[2], difference[0], difference[1])

    with open('wg0_data.csv', 'a', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(stored_data)

    # Check and remove the oldest line if the number of lines exceeds MAX_LINES
    with open('wg0_data.csv', 'r') as csvfile:
        lines = csvfile.readlines()
        if len(lines) > MAX_LINES:
            lines = lines[1:]

    with open('wg0_data.csv', 'w', newline='') as csvfile:
        csvfile.writelines(lines)

@app.route('/')
def index():
    try:
        pivpn_status = subprocess.check_output(["pivpn", "-c"], universal_newlines=True)
    except subprocess.CalledProcessError as e:
        pivpn_status = f"Error: {e.output}"

    return render_template('index.html', pivpn_status=pivpn_status)

@app.route('/json_data')
def json_data():
    json_data_list = []
    with open('system_data.csv', 'r') as csvfile:
        csv_reader = csv.reader(csvfile)
        data = [list(row) for row in csv_reader]

    for line in data:
        json_data_list.append({
            "date": line[0],
            "temperature": float(line[1]),
            "ram": float(line[2]),
            "maxRam": float(line[3]),
            "cpu": float(line[4]),
            "usedspace": str(line[5]),
            "allSpace": str(line[6]),
            "ramperc": str(line[7]),
            "diskperc": str(line[8]),
        })
    return jsonify(json_data_list)

@app.route('/json_dataWG')
def json_data_wg():
    json_data_list = []
    with open('wg0_data.csv', 'r') as csvfile:
        csv_reader = csv.reader(csvfile)
        data = [list(row) for row in csv_reader]

    for line in data:
        json_data_list.append({
            "date": line[0],
            "TX": float(line[1]),
            "RX": float(line[2]),
            "TXdiff": float(line[3]),
            "RXdiff": float(line[4]),
        })
    return jsonify(json_data_list)

def start_flask_server():
    app.run(host='0.0.0.0', port=5005)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=start_flask_server)
    flask_thread.start()

    try:
        while True:
            temperature = get_cpu_temperature()
            ram_used, ram_total = get_ram_usage()
            cpu_usage = get_cpu_usage()
            disk_used, disk_total, disk_percentage = get_disk_space()
            tx_packets, rx_packets = get_wireguard_stats()

            data = [temperature, ram_used, ram_total, cpu_usage, disk_used,
                    disk_total, "{:.2f}".format(calculate_ram_percentage(ram_used, ram_total)), disk_percentage]
            write_system_data_to_csv(data, [tx_packets, rx_packets])
            time.sleep(60)  # Sleep for 60 minutes before the next iteration
    except KeyboardInterrupt:
        print("\nExiting the live updates.")
