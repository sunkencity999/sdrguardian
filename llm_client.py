import subprocess
import json
import requests
import time
import re

def extract_json_from_text(text):
    """
    Extracts JSON from text that might contain other content.
    Tries multiple approaches to find and parse valid JSON.
    """
    # First, try to parse the entire text as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON within markdown code blocks
    json_code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    matches = re.findall(json_code_block_pattern, text)
    
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    # Try to find JSON within curly braces
    try:
        json_pattern = r'\{[\s\S]*\}'
        match = re.search(json_pattern, text)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # If all else fails, return None
    return None

def analyze(record: dict, model: str):
    """
    Sends the record to the local Ollama LLM for analysis.
    """
    # Construct an enhanced instruction prompt for anomaly detection with emphasis on security and JSON format
    instruction = (
        "You are a military-grade cybersecurity analyst monitoring sensor data from a Software Defined Radio system. "
        "For the following record, analyze if there are any security implications or anomalies with absolute precision. "
        "This is for a military application where accuracy is critical.\n\n"
        
        "For WiFi data, analyze for:\n"
        "- Rogue/unauthorized access points (unexpected SSIDs or duplicate SSIDs with different security)\n"
        "- Evil twin attacks (duplicate networks with similar names but different security settings)\n"
        "- Unusual signal strengths (unexpectedly strong signals that might indicate proximity)\n"
        "- Open networks in secure areas (potential security risk)\n"
        "- Networks with weak security protocols (WEP, open)\n"
        "- Suspicious naming patterns that might indicate surveillance\n"
        "- Sudden appearance of new networks in previously stable environments\n"
        "- Disappearance of previously stable networks (could indicate jamming)\n\n"
        
        "For Bluetooth data, analyze for:\n"
        "- Unexpected devices with very strong signal strength (indicating close proximity)\n"
        "- Devices with suspicious names (surveillance equipment, drones, unknown devices)\n"
        "- Devices that appear to be spoofing legitimate device names\n"
        "- Persistent unknown devices that follow location changes\n"
        "- Bluetooth devices with unusual manufacturer data\n"
        "- Patterns suggesting Bluetooth tracking or surveillance\n"
        "- Bluetooth beacons in unexpected locations\n\n"
        
        "IMPORTANT: Your response MUST be a valid JSON object with EXACTLY these keys:\n"
        "- 'anomaly': boolean (true/false) - indicate if there is a potential security threat\n"
        "- 'reason': string (precise, factual description of the finding)\n"
        "- 'threat_level': string (must be one of: 'low', 'medium', 'high') - assess based on military security standards\n"
        "- 'recommendation': string (specific action to take based on military security protocols)\n"
        "- 'details': object (containing specific findings that led to this assessment)\n\n"
        
        "If you cannot make a determination due to insufficient data, indicate this clearly in the 'reason' field "
        "and set 'anomaly' to false and 'threat_level' to 'low'.\n\n"
        
        "DO NOT include any explanations, markdown formatting, or text outside the JSON object. "
        "DO NOT fabricate or invent data that is not present in the record."
    )
    payload = json.dumps(record)
    prompt = f"{instruction}\n\nRecord:\n{payload}"
    
    # Use the Ollama API directly - this is the most reliable method
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt}
        )
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Extract the generated text from the streaming response
        result_text = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    if "response" in data:
                        result_text += data["response"]
                except json.JSONDecodeError:
                    continue
        
        # Try to parse the result as JSON using our enhanced extraction
        json_result = extract_json_from_text(result_text)
        if json_result:
            # Validate that the JSON has the required keys
            required_keys = ['anomaly', 'reason', 'threat_level', 'recommendation']
            if all(key in json_result for key in required_keys):
                # Add details field if it doesn't exist
                if 'details' not in json_result:
                    json_result['details'] = {}
                return json_result
        
        # If we couldn't extract valid JSON or it's missing required keys
        return {
            "anomaly": False, 
            "reason": "Analysis could not be completed in proper format - original analysis data preserved in raw_output", 
            "raw_output": result_text.strip(),
            "threat_level": "low",
            "recommendation": "Manual review required - automated analysis failed to produce structured results"
        }
            
    except requests.RequestException as e:
        # If API fails, try CLI as fallback
        try:
            # Use the correct format for Ollama CLI (no --prompt flag)
            result = subprocess.run(
                ["ollama", "run", model, prompt],
                capture_output=True,
                text=True,
                timeout=30  # Set a reasonable timeout
            )
            
            if result.returncode != 0:
                return {
                    "anomaly": False,
                    "reason": f"LLM analysis failed: {result.stderr}",
                    "threat_level": "low",
                    "recommendation": "Check if Ollama is running correctly"
                }
                
            # Try to parse the result as JSON using our enhanced extraction
            json_result = extract_json_from_text(result.stdout)
            if json_result:
                # Validate that the JSON has the required keys
                required_keys = ['anomaly', 'reason', 'threat_level', 'recommendation']
                if all(key in json_result for key in required_keys):
                    return json_result
            
            # If we couldn't extract valid JSON or it's missing required keys
            return {
                "anomaly": False, 
                "reason": "Analysis could not be completed in proper format - original analysis data preserved in raw_output", 
                "raw_output": result.stdout.strip(),
                "threat_level": "low",
                "recommendation": "Manual review required - automated analysis failed to produce structured results"
            }
                
        except Exception as cli_error:
            return {
                "anomaly": False,
                "reason": f"LLM analysis failed: {str(cli_error)}",
                "threat_level": "low",
                "recommendation": "Check if Ollama is installed and running"
            }
    
def summarize(records: list, model: str, instruction: str = None):
    """
    Summarize a batch of sensor records using the LLM.
    Returns the parsed JSON or raw text summary.
    """
    if instruction is None:
        instruction = (
            "You are a military-grade cybersecurity and situational awareness analyst reviewing recent sensor data from Wi-Fi, Bluetooth, IMU, and network I/O.\n\n"
            "This analysis is for a critical military application where accuracy and precision are essential.\n\n"
            
            "ANALYZE WIFI DATA FOR SECURITY THREATS:\n"
            "- Evil Twin Attacks: Look for duplicate SSIDs with different security settings\n"
            "- Rogue Access Points: Identify unexpected networks or those with suspicious naming patterns\n"
            "- Deauthentication Attacks: Note networks that repeatedly appear and disappear\n"
            "- Weak Security: Flag networks using outdated security (WEP, Open)\n"
            "- Signal Anomalies: Identify unusually strong signals that could indicate close proximity\n"
            "- Surveillance Networks: Look for SSIDs matching patterns used by surveillance equipment\n"
            "- Historical Changes: Compare with previous scans to identify new or missing networks\n\n"
            
            "ANALYZE BLUETOOTH DATA FOR SECURITY THREATS:\n"
            "- Proximity Threats: Identify devices with very strong signal strength (RSSI > -50dBm)\n"
            "- Suspicious Devices: Flag devices with names suggesting drones, cameras, or surveillance equipment\n"
            "- Persistent Trackers: Note devices that consistently appear across multiple scans\n"
            "- Spoofed Devices: Identify devices that may be impersonating known trusted devices\n"
            "- Bluetooth Beacons: Detect unexpected beacon activity in secure areas\n"
            "- Unknown Manufacturers: Flag devices with unrecognized manufacturer data\n"
            "- Bluetooth Sniffers: Look for devices that might be capturing Bluetooth traffic\n\n"
            
            "CORRELATE DATA ACROSS SENSORS:\n"
            "- Look for relationships between WiFi and Bluetooth anomalies\n"
            "- Consider physical movement patterns from IMU data that coincide with network changes\n"
            "- Identify patterns suggesting coordinated surveillance or monitoring\n"
            "- Flag situations where multiple low-risk indicators combine to suggest higher risk\n\n"
            
            "IMPORTANT: Your response MUST be a valid JSON object with EXACTLY this structure:\n"
            "{ \"events\": [ \n"
            "    { \n"
            "        \"timestamp\": (number, current unix timestamp),\n"
            "        \"type\": (string, specific event type - e.g., 'evil_twin_detected', 'rogue_ap', 'suspicious_bluetooth', 'proximity_alert'),\n"
            "        \"sensor\": (string, which sensor detected this - 'wifi', 'bluetooth', 'imu', or 'correlated'),\n"
            "        \"level\": (string, must be one of: \"info\", \"warning\", \"critical\") - assess based on military security standards,\n"
            "        \"description\": (string, precise factual description),\n"
            "        \"affected_devices\": (array of strings, identifiers of relevant devices/networks),\n"
            "        \"recommendation\": (string, specific action based on military security protocols)\n"
            "    }\n"
            "]}\n\n"
            "If no events are detected, return an empty events array.\n\n"
            "DO NOT include any explanations, markdown formatting, or text outside the JSON object. "
            "DO NOT fabricate or invent data that is not present in the records."
        )
    payload = json.dumps(records)
    prompt = f"{instruction}\n\nRecords:\n{payload}"
    
    # Use the Ollama API directly - this is the most reliable method
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt}
        )
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Extract the generated text from the streaming response
        result_text = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    if "response" in data:
                        result_text += data["response"]
                except json.JSONDecodeError:
                    continue
        
        # Try to parse the result as JSON using our enhanced extraction
        json_result = extract_json_from_text(result_text)
        if json_result and 'events' in json_result and isinstance(json_result['events'], list):
            # Validate that the JSON has the required structure
            valid_events = True
            for event in json_result['events']:
                required_keys = ['timestamp', 'type', 'level', 'description', 'recommendation']
                if not all(key in event for key in required_keys):
                    valid_events = False
                    break
                
                # Add sensor field if missing
                if 'sensor' not in event:
                    event['sensor'] = 'unknown'
                
                # Add affected_devices field if missing
                if 'affected_devices' not in event:
                    event['affected_devices'] = []
            
            if valid_events:
                return json_result
        
        # Return a structured response even if the LLM didn't output valid JSON
        return {
            "events": [
                {
                    "timestamp": time.time(),
                    "type": "summary",
                    "level": "info",
                    "description": "Analysis could not be completed in proper format - manual review required",
                    "raw_output": result_text.strip(),
                    "recommendation": "Escalate to security team for manual analysis of raw data"
                }
            ]
        }
            
    except requests.RequestException as e:
        # If API fails, try CLI as fallback
        try:
            # Use the correct format for Ollama CLI (no --prompt flag)
            result = subprocess.run(
                ["ollama", "run", model, prompt],
                capture_output=True,
                text=True,
                timeout=30  # Set a reasonable timeout
            )
            
            if result.returncode != 0:
                return {
                    "events": [
                        {
                            "timestamp": time.time(),
                            "type": "error",
                            "level": "warning",
                            "description": f"LLM summary failed: {result.stderr}",
                            "recommendation": "Check if Ollama is running correctly"
                        }
                    ]
                }
                
            # Try to parse the result as JSON using our enhanced extraction
            json_result = extract_json_from_text(result.stdout)
            if json_result and 'events' in json_result and isinstance(json_result['events'], list):
                # Validate that the JSON has the required structure
                valid_events = True
                for event in json_result['events']:
                    required_keys = ['timestamp', 'type', 'level', 'description', 'recommendation']
                    if not all(key in event for key in required_keys):
                        valid_events = False
                        break
                
                if valid_events:
                    return json_result
            
            # Return a structured response even if the LLM didn't output valid JSON
            return {
                "events": [
                    {
                        "timestamp": time.time(),
                        "type": "summary",
                        "level": "info",
                        "description": "Analysis could not be completed in proper format - manual review required",
                        "raw_output": result.stdout.strip(),
                        "recommendation": "Escalate to security team for manual analysis of raw data"
                    }
                ]
            }
                
        except Exception as cli_error:
            return {
                "events": [
                    {
                        "timestamp": time.time(),
                        "type": "error",
                        "level": "warning",
                        "description": f"LLM summary failed: {str(cli_error)}",
                        "recommendation": "Check if Ollama is installed and running"
                    }
                ]
            }