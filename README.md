# SDRGuardian - Military-Grade RF Monitoring System

![SDRGuardian](https://img.shields.io/badge/Version-1.0-blue)
![Platform](https://img.shields.io/badge/Platform-macOS%20|%20Linux-green)
![License](https://img.shields.io/badge/License-Military%20Use-red)

SDRGuardian is an advanced Software Defined Radio (SDR) monitoring system designed for military applications. It leverages a device's built-in sensors (Wi-Fi, Bluetooth, IMU) to provide comprehensive security monitoring, including both cybersecurity and physical threat detection. The system combines sensor data with local LLM-powered analysis to identify potential threats in the RF environment and physical surroundings, offering military personnel complete situational awareness of their operational environment. By analyzing patterns in sensor data, SDRGuardian can detect unauthorized proximity, surveillance attempts, physical tampering, and other physical security threats without requiring additional hardware.

## Key Features

### Sensor Capabilities

- **WiFi Monitoring**: Detects and analyzes all WiFi networks in range using modern tools like wdutil and system_profiler
- **Bluetooth Scanning**: Identifies Bluetooth and BLE devices, including advertisement data
- **Network I/O Analysis**: Monitors network traffic patterns and detects anomalies
- **IMU (Inertial Measurement Unit)**: Tracks device movement and orientation
- **Association Monitoring**: Tracks device associations and connections

### Physical Security Detection

- **Proximity Threat Detection**: Identifies unauthorized devices in close proximity using Bluetooth signal strength
- **Movement Pattern Analysis**: Detects devices showing surveillance patterns (following, circling, persistent presence)
- **Device Tampering Detection**: Uses IMU sensor to detect unexpected orientation changes and impacts
- **Vibration Detection**: Identifies unusual vibrations that might indicate someone approaching
- **Surveillance Risk Assessment**: Analyzes device persistence and behavior to identify potential surveillance

### Analysis & Intelligence

- **Real-time LLM Analysis**: Uses local LLMs via Ollama for on-device threat analysis
- **Anomaly Detection**: Identifies unusual patterns in RF spectrum and physical environment
- **Threat Classification**: Categorizes potential threats as cyber, physical, or both
- **Signal Correlation**: Correlates signals across different sensor types for comprehensive threat assessment

### User Interface

- **Real-time Dashboard**: Web-based UI with live updates of sensor data
- **Comprehensive Security Panels**: Dedicated panels for both cybersecurity and physical security monitoring
- **Physical Security Metrics**: Visual indicators for proximity threats, movement detection, device tampering, and surveillance risk
- **Interactive Charts**: Visual representation of RF spectrum and device activity
- **Threat Type Classification**: Clear visual distinction between cyber threats, physical threats, or combined threats
- **Alert System**: Configurable alerts for detected threats with threat type indication
- **Responsive Design**: Works on various screen sizes for field operations

## System Requirements

### Hardware

- Modern laptop or desktop with built-in WiFi and Bluetooth capabilities
- For extended capabilities: External SDR hardware (optional)

### Software

- **Operating System**: macOS 10.15+ or Linux (Ubuntu 20.04+)
- **Python**: 3.8 or higher
- **Ollama**: For local LLM analysis

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/sdrguardian.git
cd sdrguardian
```

### 2. Installation Options

#### Option A: Manual Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Install Ollama (if not already installed):
   - macOS: `brew install ollama`
   - Linux: `curl -fsSL https://ollama.com/install.sh | sh`

4. Pull the required LLM model:

   ```bash
   ollama pull llama2
   ```

5. Adjust `config.yaml` to set sensor intervals, LLM model, and alert thresholds.

#### Option B: Automated Installer

- On macOS:

  ```bash
  bash scripts/install_mac.sh
  ```

- On Linux:

  ```bash
  bash scripts/install_linux.sh
  ```

This will set up the virtual environment, install dependencies, and generate launch scripts.

## Running SDRGuardian

### Starting with Sudo Privileges (Recommended)
For full functionality, especially WiFi scanning, SDRGuardian requires sudo privileges. Use one of the following methods:

#### 1. macOS Quick Launch
Double-click the `SDRGuardian.command` file in Finder. This will open a Terminal window, prompt for sudo password, and start the application.

#### 2. Command Line Launch

```bash
# Using the shell script
./run_sdrguardian.sh

# Or using the Python wrapper
python3 run_with_sudo.py
```

### Manual Running (Advanced)

#### Pipeline Mode (Collect and Analyze Sensor Data)

```bash
# With sudo (recommended)
sudo python run.py --mode pipeline

# Without sudo (limited functionality)
python run.py --mode pipeline
```

#### GUI Mode (Web Dashboard)

```bash
# With sudo (recommended)
sudo python run.py --mode gui

# Without sudo (limited functionality)
python run.py --mode gui --port 8000
```

Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser to view the dashboard.

## Physical Security Features

SDRGuardian leverages existing sensors to provide comprehensive physical security monitoring without additional hardware:

### Bluetooth-Based Physical Security

- **Proximity Detection**: Uses Bluetooth signal strength (RSSI) to detect when unauthorized devices are in close proximity
- **Movement Pattern Analysis**: Identifies devices that follow specific patterns indicative of surveillance
- **Persistent Device Detection**: Flags devices that remain in range for extended periods, potentially indicating surveillance
- **Device Density Monitoring**: Detects unusual gatherings of devices that may indicate physical threats

### WiFi-Based Physical Security

- **Device Density Analysis**: Monitors for unusual concentrations of devices in typically empty areas
- **Signal Strength Monitoring**: Detects devices with unusually strong signals that may indicate close proximity
- **Network Pattern Analysis**: Identifies unusual patterns in device connections that may indicate physical threats

### IMU-Based Physical Security

- **Vibration Detection**: Uses the device's accelerometer to detect vibrations from approaching personnel
- **Orientation Change Monitoring**: Detects when someone may be physically tampering with the device
- **Sudden Impact Detection**: Identifies sudden shocks that might indicate attempted physical access
- **Movement Analysis**: Identifies unusual movement patterns that might indicate unauthorized handling

### Integrated Threat Assessment

- **Multi-Sensor Correlation**: Combines data from all sensors to provide a comprehensive physical security assessment
- **Threat Classification**: Clearly identifies whether detected threats are cyber, physical, or both
- **Actionable Recommendations**: Provides specific recommendations for responding to physical threats

## Configuration

Edit the `config.yaml` file to customize SDRGuardian's behavior:


```yaml
# Sensor intervals (in seconds)
wifi:
  interval: 5
  # Add sudo_password here if not using sudo wrapper
  # sudo_password: "your_password"

bluetooth:
  interval: 10

imu:
  interval: 1

netio:
  interval: 5

# LLM configuration
llm:
  model: "llama2"
  # Other LLM options...

# Alert thresholds
alerts:
  wifi_networks_threshold: 10
  bluetooth_devices_threshold: 5
  # Other alert thresholds...
```

## Features in Detail

### WiFi Sensor

The WiFi sensor uses modern tools like wdutil and system_profiler to detect and analyze WiFi networks. It provides detailed information about each network, including:

- SSID (network name)
- Signal strength (RSSI)
- Channel
- Security type
- Connection status

The sensor requires sudo privileges for full functionality, especially when using wdutil for scanning.

### Bluetooth Sensor

The Bluetooth sensor detects Bluetooth and BLE devices in the vicinity, providing:

- Device name and address
- Signal strength
- Advertisement data (for BLE devices)
- Service information

### Network I/O Sensor

Monitors network traffic patterns and detects anomalies in data transfer rates.

### IMU Sensor

Tracks device movement and orientation using the built-in accelerometer and gyroscope.

### Association Sensor

Tracks device associations and connections to identify potential security risks.

## Dashboard Interface

The web-based dashboard provides real-time visualization of sensor data, including:


- WiFi network spectrum chart
- Bluetooth device proximity map
- Network traffic graphs
- Device movement tracking
- Alert notifications
- LLM analysis results

## Troubleshooting

### WiFi Scanning Issues

- **No Networks Detected**: Ensure you're running with sudo privileges
- **Permission Errors**: Use the sudo wrapper scripts provided
- **Hardware Not Detected**: Check if your WiFi interface is enabled

### Bluetooth Scanning Issues

- **No Devices Found**: Ensure Bluetooth is enabled on your system
- **Scanner Errors**: Check if your Bluetooth adapter is recognized

### Dashboard Not Loading

- Verify the server is running ([http://127.0.0.1:8000](http://127.0.0.1:8000))
- Check console logs for any errors
- Ensure all dependencies are installed correctly

## Military Usage Guidelines

SDRGuardian is designed for military applications and adheres to strict operational security standards:

1. **No Sample Data**: The system never generates fake or sample data, ensuring all analysis is based on real sensor readings
2. **Clear Error Reporting**: When data cannot be obtained, the system provides detailed diagnostic information
3. **Secure Local Processing**: All analysis is performed locally using Ollama, with no data sent to external servers
4. **Privilege Escalation**: The system properly handles sudo requirements for accessing hardware capabilities

## Contributing

Contributions to SDRGuardian are welcome. Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This software is provided for authorized use only. All rights reserved.

## Acknowledgments

- Ollama for local LLM capabilities
- FastAPI for the web framework
- Bleak for Bluetooth scanning

## Contact

For support or inquiries, please contact the developer Christopher Bradford at [sdrguardian@robotbirdservices.com](mailto:sdrguardian@robotbirdservices.com).