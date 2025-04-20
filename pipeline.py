import asyncio
from sensors.wifi import WifiSensor
from sensors.bluetooth import BluetoothSensor
from sensors.imu import ImuSensor
from sensors.netio import NetIOSensor
from sensors.assoc import AssocSensor
from sensors.netio import NetIOSensor
from config import load_config
from llm_client import analyze
from alerts import check_alerts

SENSOR_CLASSES = {
    "wifi": WifiSensor,
    "bluetooth": BluetoothSensor,
    "imu": ImuSensor,
    "netio": NetIOSensor,
    "assoc": AssocSensor,
}

async def main():
    config = load_config()
    # LLM model and alert configuration
    llm_model = config.get("llm", {}).get("model")
    alert_conf = config.get("alerts", {}) or {}
    queue = asyncio.Queue()
    sensors = []
    for name, cls in SENSOR_CLASSES.items():
        conf = config.get(name, {})
        sensor = cls(conf)
        sensors.append(sensor)
    tasks = [asyncio.create_task(sensor.start(queue)) for sensor in sensors]
    try:
        while True:
            record = await queue.get()
            # Emit raw record
            print("Record:", record)
            # LLM analysis for anomaly detection
            analysis = None
            if llm_model:
                try:
                    analysis = analyze(record, llm_model)
                    print("Analysis:", analysis)
                except Exception as e:
                    print(f"LLM analysis error: {e}")
            # Gather alerts: LLM-based anomalies and rule-based thresholds
            alerts_list = []
            if isinstance(analysis, dict) and analysis.get("anomaly"):
                alerts_list.append({
                    "sensor": record.get("sensor"),
                    "timestamp": record.get("timestamp"),
                    "reason": analysis.get("reason"),
                })
            # Rule-based alerts
            try:
                alerts_list.extend(check_alerts(record, alert_conf))
            except Exception as e:
                print(f"Alert check error: {e}")
            if alerts_list:
                print("Alerts:", alerts_list)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("Stopping sensors...")
        for sensor in sensors:
            sensor.stop()
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())