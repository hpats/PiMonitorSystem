System Monitoring Application
Overview

This Python application provides a simple system monitoring tool with a web interface. It collects and displays information about CPU temperature, RAM usage, CPU usage, disk space, and WireGuard VPN statistics. The data is stored in CSV files and can be accessed through the provided Flask web server.
Prerequisites

Make sure you have the following installed:

    Python 3.x
    Flask
    WireGuard

Installation

    Clone this repository:

    bash

git clone https://github.com/your-username/system-monitoring-app.git
cd system-monitoring-app

Install required dependencies:

bash

pip install flask

Run the application:

bash

    python monitor.py

Usage

Visit http://localhost:5005 in your web browser to access the system monitoring dashboard. The dashboard provides both graphical and JSON representations of the system and WireGuard data.
Endpoints

    /: Provides an overview of the system status, including PiVPN status.
    /json_data: Returns system data in JSON format.
    /json_dataWG: Returns WireGuard data in JSON format.

Customization

Feel free to customize the application to suit your needs. You can modify the monitoring intervals, add new features, or enhance the web interface.
Contributing

Contributions are welcome! If you find a bug or have a suggestion, please open an issue or submit a pull request.
License

This project is licensed under the MIT License - see the LICENSE file for details.