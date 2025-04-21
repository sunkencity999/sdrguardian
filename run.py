import argparse
import asyncio
import socket
import sys

def is_port_available(port):
    """Check if a port is available for use."""
    try:
        # Try to create a socket and bind it to the port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
            return True
    except socket.error:
        return False

def find_available_port(start_port, max_attempts=5):
    """Find an available port starting from start_port."""
    for port_offset in range(max_attempts):
        port = start_port + port_offset
        if is_port_available(port):
            return port
    return None

def run_gui_server(port):
    """Run the GUI server on the specified port."""
    import uvicorn
    import webbrowser
    import threading
    import time
    
    # Function to open browser after a short delay
    def open_browser():
        time.sleep(2)  # Wait for server to start
        url = f"http://127.0.0.1:{port}"
        print(f"Opening browser to {url}")
        webbrowser.open(url)
    
    # Start browser in a separate thread
    threading.Thread(target=open_browser).start()
    
    try:
        print(f"Starting server on port {port}...")
        uvicorn.run("gui.main:app", host="127.0.0.1", port=port, reload=True)
    except Exception as e:
        print(f"Failed to start server on port {port}: {e}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="SDRGuardian runner")
    parser.add_argument(
        "--mode",
        choices=["pipeline", "gui"],
        default="pipeline",
        help="Mode to run",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Starting port for the GUI server (will try up to 5 consecutive ports)",
    )
    args = parser.parse_args()
    
    if args.mode == "pipeline":
        from pipeline import main as pipeline_main
        asyncio.run(pipeline_main())
    else:
        # Try to find an available port
        start_port = args.port
        available_port = find_available_port(start_port)
        
        if available_port:
            print(f"Found available port: {available_port}")
            run_gui_server(available_port)
        else:
            print(f"No available ports found in range {start_port}-{start_port+4}")
            print("You can try specifying a different starting port with --port")
            sys.exit(1)

if __name__ == "__main__":
    main()