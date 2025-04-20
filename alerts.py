def check_alerts(record: dict, config: dict):
    """
    Check record against alert rules and return a list of alerts (possibly empty).
    """
    import math
    alerts = []
    # Rule-based thresholds from config
    # config structure: { 'thresholds': { 'wifi': {...}, 'bluetooth': {...}, 'imu': {...} } }
    thresholds = config.get('thresholds', {})
    sensor = record.get('sensor')
    ts = record.get('timestamp')
    # Wi-Fi: low RSSI
    if sensor == 'wifi':
        wifi_thresh = thresholds.get('wifi', {})
        rssi_min = wifi_thresh.get('rssi_min')
        for net in record.get('networks', []):
            rssi = net.get('rssi')
            if rssi_min is not None and isinstance(rssi, (int, float)) and rssi < rssi_min:
                alerts.append({
                    'sensor': 'wifi',
                    'timestamp': ts,
                    'network': net.get('ssid'),
                    'issue': f'Low Wi-Fi RSSI ({rssi} dBm)',
                })
    # Bluetooth: low RSSI
    elif sensor == 'bluetooth':
        bt_thresh = thresholds.get('bluetooth', {})
        rssi_min = bt_thresh.get('rssi_min')
        for dev in record.get('devices', []):
            rssi = dev.get('rssi')
            if rssi_min is not None and isinstance(rssi, (int, float)) and rssi < rssi_min:
                alerts.append({
                    'sensor': 'bluetooth',
                    'timestamp': ts,
                    'device': dev.get('address'),
                    'issue': f'Low Bluetooth RSSI ({rssi} dBm)',
                })
    # IMU: acceleration magnitude exceeds threshold
    elif sensor == 'imu':
        imu_thresh = thresholds.get('imu', {})
        accel_max = imu_thresh.get('accel_max')
        accel = record.get('accel', {}) or {}
        x = accel.get('x', 0)
        y = accel.get('y', 0)
        z = accel.get('z', 0)
        mag = math.sqrt(x*x + y*y + z*z)
        if accel_max is not None and isinstance(accel_max, (int, float)) and mag > accel_max:
            alerts.append({
                'sensor': 'imu',
                'timestamp': ts,
                'issue': f'High acceleration magnitude ({mag:.2f})',
            })
    # Network I/O: detect high throughput
    if sensor == 'netio':
        net_thresh = thresholds.get('netio', {})
        sent_max = net_thresh.get('rate_sent_max')
        recv_max = net_thresh.get('rate_recv_max')
        rs = record.get('rate_sent')
        rr = record.get('rate_recv')
        if sent_max is not None and isinstance(rs, (int, float)) and rs > sent_max:
            alerts.append({
                'sensor': 'netio',
                'timestamp': ts,
                'issue': f'High upload rate ({rs:.1f} B/s)'
            })
        if recv_max is not None and isinstance(rr, (int, float)) and rr > recv_max:
            alerts.append({
                'sensor': 'netio',
                'timestamp': ts,
                'issue': f'High download rate ({rr:.1f} B/s)'
            })
    return alerts