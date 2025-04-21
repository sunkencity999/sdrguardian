#!/usr/bin/env python3
import asyncio
from sensors.wifi import WifiSensor

async def test_wifi_sensor():
    print("Initializing WiFi sensor...")
    sensor = WifiSensor({})
    print(f"Hardware status: {sensor.hardware_status}")
    
    print("\nScanning for WiFi networks...")
    success, error, networks = await sensor._scan_mac_wifi()
    
    print(f"Scan success: {success}")
    if error:
        print(f"Error: {error}")
    
    print(f"Networks found: {len(networks)}")
    for i, network in enumerate(networks):
        print(f"Network {i+1}: {network}")
    
    return success, networks

if __name__ == "__main__":
    asyncio.run(test_wifi_sensor())
