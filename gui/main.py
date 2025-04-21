from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import re
import re
import time
import os

from config import load_config, CONFIG_PATH
from sensors.oui import lookup as oui_lookup
import yaml
from sensors.wifi import WifiSensor
from sensors.bluetooth import BluetoothSensor
from sensors.imu import ImuSensor
from llm_client import analyze
from alerts import check_alerts

app = FastAPI()

# Serve static files under /static
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

from fastapi.responses import FileResponse
import json
from typing import Optional

@app.get("/")
async def root():
    # Serve the frontend index page
    return FileResponse(os.path.join(static_dir, "index.html"))

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connected WebSocket clients
# Connected WebSocket clients
clients: set[WebSocket] = set()
## Programmatic state tracking
known_ssids: set[str] = set()
known_bt: set[str] = set()
known_assoc: Optional[str] = None
# Buffer for periodic summaries
summary_buffer: list[dict] = []
# Queue for incoming sensor data
queue: asyncio.Queue = asyncio.Queue()
# Tracking and summary buffers
known_ssids: set[str] = set()
known_bt: set[str] = set()
summary_buffer: list[dict] = []

@app.on_event("startup")
async def startup_event():
    config = load_config()
    llm_model = config.get("llm", {}).get("model")
    alert_conf = config.get("alerts", {}) or {}
    SENSOR_CLASSES = {
        "wifi": WifiSensor,
        "bluetooth": BluetoothSensor,
        "imu": ImuSensor,
    }
    for name, cls in SENSOR_CLASSES.items():
        conf = config.get(name, {})
        sensor = cls(conf)
        asyncio.create_task(sensor.start(queue))
    summary_interval = config.get('summary_interval', 300)
    # Start broadcaster and periodic summary tasks
    asyncio.create_task(_broadcaster(llm_model, alert_conf))
    asyncio.create_task(_summary_scheduler(llm_model, summary_interval))

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/settings")
async def get_settings():
    """
    Retrieve current sensor and alert configuration.
    """
    return load_config()

@app.post("/settings")
async def post_settings(new_conf: dict):
    """
    Update configuration file with provided settings.
    """
    try:
        with open(CONFIG_PATH, 'w') as f:
            yaml.safe_dump(new_conf, f)
    except Exception as e:
        return {"status": "error", "detail": str(e)}
    return {"status": "success"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_info = f"{websocket.client.host}:{websocket.client.port}"
    print(f"New WebSocket connection attempt from {client_info}")
    try:
        await websocket.accept()
        print(f"WebSocket connection accepted from {client_info}")
        clients.add(websocket)
        print(f"Total active WebSocket connections: {len(clients)}")
        
        # Send a test message to confirm connection is working
        await websocket.send_json({
            "status": "connected", 
            "timestamp": time.time(),
            "message": "WebSocket connection established"
        })
        print(f"Sent connection confirmation to {client_info}")
        
        # Keep the connection alive
        while True:
            data = await websocket.receive_text()
            print(f"Received message from {client_info}: {data[:50]}..." if len(data) > 50 else f"Received message from {client_info}: {data}")
            # Echo back to confirm receipt
            await websocket.send_json({"status": "received", "timestamp": time.time()})
    except WebSocketDisconnect:
        print(f"WebSocket disconnected from {client_info}")
    except Exception as e:
        print(f"WebSocket error with {client_info}: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if websocket in clients:
            clients.discard(websocket)
            print(f"Removed {client_info} from clients. Remaining active connections: {len(clients)}")

async def _broadcaster(llm_model, alert_conf):
    """
    Consume sensor records, run LLM analysis and rule checks, and broadcast to all clients.
    """
    print("Broadcaster started and waiting for sensor data...")
    while True:
        print("Waiting for data from sensors...")
        record = await queue.get()
        sensor_type = record.get('sensor', 'unknown')
        print(f"Received {sensor_type} data")
        
        # Buffer for periodic summaries
        summary_buffer.append(record)
        # Programmatic detection of new devices/events
        prog_alerts = []
        sensor = record.get("sensor")
        ts = record.get("timestamp")
        if sensor == 'wifi':
            for net in record.get('networks', []):
                ssid = net.get('ssid')
                bssid = net.get('bssid') if isinstance(net, dict) else None
                # New network detection
                if ssid and ssid not in known_ssids:
                    prog_alerts.append({
                        'sensor': 'wifi',
                        'timestamp': ts,
                        'issue': f'New Wi-Fi network detected: {ssid}'
                    })
                    known_ssids.add(ssid)
                # Drone-like SSID detection
                if ssid and re.search(r'(drone|mavic|dji|parrot|bebop)', ssid, re.IGNORECASE):
                    prog_alerts.append({
                        'sensor': 'wifi',
                        'timestamp': ts,
                        'issue': f'Possible drone network detected: {ssid}'
                    })
        elif sensor == 'bluetooth':
            for dev in record.get('devices', []):
                addr = dev.get('address')
                name = dev.get('name') or ''
                # Vendor lookup
                vendor = oui_lookup(addr)
                vendor_str = f" (vendor: {vendor})" if vendor else ''
                # New device detection
                if addr and addr not in known_bt:
                    prog_alerts.append({
                        'sensor': 'bluetooth',
                        'timestamp': ts,
                        'issue': f'New Bluetooth device detected: {name or addr}{vendor_str}'
                    })
                    known_bt.add(addr)
                # Drone-like device detection (by name or vendor)
                if ((name and re.search(r'(drone|mavic|dji|parrot|bebop)', name, re.IGNORECASE))
                        or vendor in ['DJI', 'Parrot']):
                    prog_alerts.append({
                        'sensor': 'bluetooth',
                        'timestamp': ts,
                        'issue': f'Possible drone device detected: {name or addr}{vendor_str}'
                    })
                # Smartphone detection by name patterns
                if name and re.search(r'(iphone|pixel|galaxy|android)', name, re.IGNORECASE):
                    prog_alerts.append({
                        'sensor': 'bluetooth',
                        'timestamp': ts,
                        'issue': f'Nearby smartphone detected: {name}{vendor_str}'
                    })
        
        # Run LLM analysis if model is configured
        analysis = None
        if llm_model:
            try:
                analysis = await asyncio.to_thread(analyze, record, llm_model)
            except Exception as e:
                print(f"LLM analysis error: {e}")
        
        # Check for alerts based on rules
        alerts = []
        if alert_conf and alert_conf.get("thresholds"):
            alerts = check_alerts(record, alert_conf["thresholds"])
        
        # Prepare message to send to clients
        # Ensure all required fields are present in the record
        if sensor_type == 'wifi' and 'networks' not in record:
            record['networks'] = []
        elif sensor_type == 'bluetooth' and 'devices' not in record:
            record['devices'] = []
        elif sensor_type == 'imu' and 'accel' not in record:
            record['accel'] = {'x': 0, 'y': 0, 'z': 0}
            
        # Ensure hardware_status is always present
        if 'hardware_status' not in record:
            record['hardware_status'] = 'unknown'
            
        message = {
            "record": record,
            "timestamp": time.time(),
        }
        
        # Debug logging of the message content
        print(f"Message content for {record.get('sensor', 'unknown')}:")
        import json
        print(json.dumps(message, indent=2, default=str))
        if analysis:
            message["analysis"] = analysis
        if alerts:
            message["alerts"] = alerts
            # Also add to summary buffer for periodic summaries
            for alert in alerts:
                summary_buffer.append({
                    "timestamp": record["timestamp"],
                    "type": f"{record.get('sensor', 'unknown')}_alert",
                    "description": alert["issue"] if "issue" in alert else alert.get("reason", "Unknown alert")
                })
        
        client_count = len(clients)
        print(f"Preparing to broadcast {record.get('sensor', 'unknown')} data to {client_count} clients")
        
        # Only proceed if there are clients connected
        if client_count == 0:
            print("No WebSocket clients connected. Data will not be displayed.")
            continue
            
        # Make a copy of the clients set to avoid modification during iteration
        current_clients = list(clients)
        successful_broadcasts = 0
        
        # Broadcast to all connected clients
        for ws in current_clients:
            try:
                await ws.send_json(message)
                successful_broadcasts += 1
            except WebSocketDisconnect:
                print(f"Client disconnected during broadcast")
                clients.discard(ws)
            except Exception as e:
                print(f"Error broadcasting to client: {str(e)}")
                # Client might be disconnected, remove it
                clients.discard(ws)
        
        print(f"Successfully broadcasted {record.get('sensor', 'unknown')} data to {successful_broadcasts}/{client_count} clients")

    
async def _summary_scheduler(llm_model, interval: int):
    """
    Periodically summarize buffered sensor data and broadcast summary to clients.
    """
    # Import here to avoid circular issues
    from llm_client import summarize
    while True:
        await asyncio.sleep(interval)
        if not summary_buffer or not llm_model:
            continue
        # Collect and clear buffer
        records = list(summary_buffer)
        summary_buffer.clear()
        try:
            summary = summarize(records, llm_model)
        except Exception as e:
            print(f"Summary generation error: {e}")
            continue
        message = {"summary": summary, "timestamp": time.time()}
        disconnected = set()
        # Create a copy of the clients set to safely iterate over it
        for ws in list(clients):
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)
        for ws in disconnected:
            clients.discard(ws)
        # End of record broadcasting loop