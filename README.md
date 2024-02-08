# System Monitoring and Wireguard Statistics

This project provides a simple system monitoring tool that collects and records various system metrics, including CPU temperature, RAM usage, CPU usage, and disk space. Additionally, it captures Wireguard interface statistics such as transmitted (TX) and received (RX) packets.

## Features

- **System Monitoring:**
  - CPU Temperature
  - RAM Usage
  - CPU Usage
  - Disk Space

- **Wireguard Statistics:**
  - Transmitted (TX) Packets
  - Received (RX) Packets

## Requirements

- Python 3.x
- Flask
- Wireguard (PiVPN)

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/system-monitoring-app.git
   cd system-monitoring-app

2. **Install required dependencies:**

   ```bash
   pip install flask
   
2. **Run the application:**

   ```bash
   python piMonitorWebServer.py

## Usage

Visit http://localhost:5005 in your web browser to access the system monitoring dashboard.

## Endpoints

    /: Provides an overview of the system status, including PiVPN status.
    /json_data: Returns system data in JSON format.
    /json_dataWG: Returns WireGuard data in JSON format.

## Customization

Feel free to customize the application to suit your needs. You can modify the monitoring intervals, add new features, or enhance the web interface.
## Contributing

Contributions are welcome! If you find a bug or have a suggestion, please open an issue or submit a pull request.
## License

This project is licensed under the MIT License - see the LICENSE file for details.
