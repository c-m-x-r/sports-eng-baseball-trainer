"""
Sensor Server - Main Entry Point
Integrates backend (Flask + MQTT) with frontend (Dash dashboard)
"""
import threading
from backend import start_mqtt_client
from frontend import app


if __name__ == "__main__":
    # Start MQTT client in background thread
    mqtt_thread = threading.Thread(target=start_mqtt_client, daemon=True)
    mqtt_thread.start()
    print("[Server] MQTT client started in background")

    # Start Dash/Flask server
    print("[Server] Starting Dash server on port 8000")
    app.run(port=8000, host="0.0.0.0")
