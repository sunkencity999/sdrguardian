import os
import yaml

CONFIG_PATH = os.environ.get("SENSOR_CONF", "config.yaml")

def load_config():
    """
    Load configuration from YAML file.
    """
    try:
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}