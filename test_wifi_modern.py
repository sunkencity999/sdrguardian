#!/usr/bin/env python3
"""
Test script for the modern WiFi sensor implementation using wdutil
"""

import asyncio
import os
import sys
import json
from sensors.wifi import WifiSensor

async def main():
    print("=== WiFi Sensor Test (Modern Implementation) ===")
    print("Initializing WiFi sensor...")
    
    # Create WiFi sensor instance with empty config
    wifi = WifiSensor(config={})
    
    print("\nScanning for WiFi networks...")
    # Call the _scan_mac_wifi method directly for testing
    success, error, networks = await wifi._scan_mac_wifi()
    
    print(f"Scan success: {success}")
    if error:
        print(f"Error: {error}")
    print(f"Networks found: {len(networks)}")
    
    if networks:
        print("\nDetected Networks:")
        for i, network in enumerate(networks, 1):
            ssid = network.get("ssid", "Unknown")
            rssi = network.get("rssi", "N/A")
            connected = "✓" if network.get("connected", False) else " "
            channel = network.get("channel", "N/A")
            security = network.get("security", "N/A")
            
            print(f"{i}. {ssid} | RSSI: {rssi} dBm | Channel: {channel} | Security: {security} | Connected: {connected}")
    
    # Get the complete record for frontend display
    record = wifi.get_record()
    print("\nComplete WiFi Record:")
    print(json.dumps(record, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
