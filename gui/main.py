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
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(websocket)

async def _broadcaster(llm_model, alert_conf):
    """
    Consume sensor records, run LLM analysis and rule checks, and broadcast to all clients.
    """
    while True:
        record = await queue.get()
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
        elif sensor == 'assoc':
            global known_assoc
            ssid = record.get('ssid')
            if ssid and ssid != known_assoc:
                prog_alerts.append({
                    'sensor': 'assoc',
                    'timestamp': ts,
                    'issue': f'Connected to Wi-Fi network: {ssid}'
                })
                known_assoc = ssid
        # analysis via LLM
        analysis = None
        if llm_model:
            try:
                analysis = analyze(record, llm_model)
            except Exception:
                analysis = None
        alerts_list = []
        # Include programmatic alerts
        alerts_list.extend(prog_alerts)
        if isinstance(analysis, dict) and analysis.get("anomaly"):
            alerts_list.append({
                "sensor": record.get("sensor"),
                "timestamp": record.get("timestamp"),
                "reason": analysis.get("reason"),
            })
        try:
            alerts_list.extend(check_alerts(record, alert_conf))
        except Exception:
            pass
        message = {"record": record, "analysis": analysis, "alerts": alerts_list}
        disconnected = set()
        for ws in clients:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)
        for ws in disconnected:
            clients.discard(ws)
    
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
        for ws in clients:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)
        for ws in disconnected:
            clients.discard(ws)
        # End of record broadcasting loop