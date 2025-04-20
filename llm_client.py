import subprocess
import json

def analyze(record: dict, model: str):
    """
    Sends the record to the local Ollama LLM for analysis.
    """
    # Construct an instruction prompt for anomaly detection
    instruction = (
        "You are monitoring sensor data. For the following record, determine if there is an anomaly. "
        "Respond with a JSON object containing keys 'anomaly' (true/false) and 'reason' (a brief description)."
    )
    payload = json.dumps(record)
    prompt = f"{instruction}\n\nRecord:\n{payload}"
    result = subprocess.run(
        ["ollama", "run", model, "--prompt", prompt],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LLM analysis failed: {result.stderr}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        # If the model did not output valid JSON, return raw text
        return {"anomaly": False, "reason": result.stdout.strip()}
    
def summarize(records: list, model: str, instruction: str = None):
    """
    Summarize a batch of sensor records using the LLM.
    Returns the parsed JSON or raw text summary.
    """
    if instruction is None:
        instruction = (
            "You are a cybersecurity and situational awareness analyst reviewing recent sensor data from Wi-Fi, Bluetooth, IMU, and network I/O. "
            "Identify and summarize: new cell phones or devices in proximity, new or changed Wi-Fi networks, devices joining local networks, unusually high data transfer rates, and any signals indicating drone presence (e.g., drone SSIDs or device names). "
            "Respond with a JSON object containing a key 'events' which is a list of objects with 'timestamp', 'type', 'level' (info/warning/critical), and 'description'."
        )
    payload = json.dumps(records)
    prompt = f"{instruction}\n\nRecords:\n{payload}"
    result = subprocess.run(
        ["ollama", "run", model, "--prompt", prompt],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LLM summary failed: {result.stderr}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout.strip()