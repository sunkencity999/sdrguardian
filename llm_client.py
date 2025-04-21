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
    # Construct an instruction prompt for anomaly detection with emphasis on security and JSON format
    instruction = (
        "You are a military-grade cybersecurity analyst monitoring sensor data from a Software Defined Radio system. "
        "For the following record, analyze if there are any security implications or anomalies with absolute precision. "
        "This is for a military application where accuracy is critical. "
        "Consider: unauthorized device proximity, potential surveillance drones, suspicious network activity, signal interference, "
        "unauthorized access points, spoofed networks, or unusual motion patterns that could indicate security threats.\n\n"
        "IMPORTANT: Your response MUST be a valid JSON object with EXACTLY these keys:\n"
        "- 'anomaly': boolean (true/false) - indicate if there is a potential security threat\n"
        "- 'reason': string (precise, factual description of the finding)\n"
        "- 'threat_level': string (must be one of: 'low', 'medium', 'high') - assess based on military security standards\n"
        "- 'recommendation': string (specific action to take based on military security protocols)\n\n"
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
            "This analysis is for a critical military application where accuracy and precision are essential. "
            "Identify and summarize with absolute precision: unauthorized devices in proximity, new or changed Wi-Fi networks, "
            "devices joining local networks, unusually high data transfer rates, potential signal jamming, "
            "and any signals indicating surveillance or reconnaissance (e.g., drone SSIDs, suspicious device names, unusual signal patterns).\n\n"
            "IMPORTANT: Your response MUST be a valid JSON object with EXACTLY this structure:\n"
            "{ \"events\": [ \n"
            "    { \n"
            "        \"timestamp\": (number, current unix timestamp),\n"
            "        \"type\": (string, specific event type),\n"
            "        \"level\": (string, must be one of: \"info\", \"warning\", \"critical\") - assess based on military security standards,\n"
            "        \"description\": (string, precise factual description),\n"
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