"""
Simple OUI (Organizationally Unique Identifier) lookup.
"""
from typing import Optional
# Sample OUI to vendor mapping. Extend as needed.
OUI_MAP = {
    '00:14:BF': 'DJI',            # DJI drones
    'E0:91:F5': 'Parrot',         # Parrot drones
    '00:17:F2': 'Apple, Inc.',    # Apple devices
    'FC:FB:FB': 'Apple, Inc.',
    '3C:5A:B4': 'Samsung Electronics',  # Samsung electronics
    'A4:5E:60': 'Google, Inc.',   # Google devices
}

def lookup(mac: str) -> Optional[str]:
    """
    Lookup vendor by MAC address prefix (OUI).
    mac: string like '00:14:BF:xx:xx:xx'
    Returns vendor name or None.
    """
    if not mac or len(mac) < 8:
        return None
    prefix = mac.upper()[0:8]
    return OUI_MAP.get(prefix)