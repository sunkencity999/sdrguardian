#!/usr/bin/env python3
import asyncio
import traceback
from sensors.wifi import WifiSensor

async def test_wifi_sensor():
    print("=== WiFi Sensor Test ===")
    try:
        print("Initializing WiFi sensor...")
        sensor = WifiSensor({})
        print(f"Hardware status: {sensor.hardware_status}")
        print(f"WiFi interface: {sensor.wifi_interface}")
        print(f"Airport command: {sensor.airport_cmd}")
        print(f"Sudo available: {sensor.sudo_available}")
        
        print("\nScanning for WiFi networks...")
        success, error, networks = await sensor._scan_mac_wifi()
        
        print(f"Scan success: {success}")
        if error:
            print(f"Error: {error}")
        
        print(f"Networks found: {len(networks)}")
        for i, network in enumerate(networks):
            print(f"Network {i+1}: {network}")
        
        return success, networks
    except Exception as e:
        print(f"Exception during test: {e}")
        traceback.print_exc()
        return False, []

if __name__ == "__main__":
    asyncio.run(test_wifi_sensor())
