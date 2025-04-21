#!/usr/bin/env python3
"""
Test script for the fixed WiFi sensor implementation
"""

import asyncio
import os
import sys
import json
from sensors.wifi import WifiSensor

async def main():
    print("=== WiFi Sensor Test (Fixed Implementation) ===")
    print("Initializing WiFi sensor...")
    
    # Create WiFi sensor instance
    wifi = WifiSensor()
    
    print("Scanning for WiFi networks...")
    success, error, networks = await wifi.scan()
    
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
