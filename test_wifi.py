#!/usr/bin/env python3
import asyncio
import sys
from sensors.wifi import WifiSensor

async def test_wifi_sensor():
    print("===== SDRGuardian WiFi Sensor Test =====\n")
    print("Initializing WiFi sensor...")
    sensor = WifiSensor({})
    print(f"Hardware status: {sensor.hardware_status}")
    print(f"WiFi interface: {sensor.wifi_interface}")
    print(f"Scan command: {sensor.scan_cmd}")
    print(f"Sudo available: {sensor.sudo_available}")
    
    print("\nScanning for WiFi networks...")
    success, error, networks = await sensor._scan_mac_wifi()
    
    print("\n===== SCAN RESULTS =====")
    print(f"Scan success: {success}")
    if error:
        print(f"Error: {error}")
    
    print(f"\nNetworks found: {len(networks)}")
    if networks:
        for i, network in enumerate(networks):
            connected = "✓" if network.get("connected", False) else " "
            print(f"  {i+1}. [{connected}] {network.get('ssid')} (RSSI: {network.get('rssi')} dBm)")
    else:
        print("  No networks found!")
    
    return success, networks

if __name__ == "__main__":
    asyncio.run(test_wifi_sensor())

if __name__ == "__main__":
    asyncio.run(test_wifi_sensor())
