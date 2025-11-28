from datetime import datetime
import json
from collections import deque
from flask import Flask, request
import paho.mqtt.client as mqtt
import threading
import ssl
import os
from pathlib import Path

# Flask server setup
server = Flask(__name__)

# Configuration
MAX_DATA_POINTS = 400  # Reduced for better performance
UPDATE_FREQ_MS = 500   # Update every 500ms instead of 100ms

# Storage configuration
STORAGE_DIR = Path(__file__).parent / "storage"
STORAGE_DIR.mkdir(exist_ok=True)  # Create storage directory if it doesn't exist

# Data storage
time = deque(maxlen=MAX_DATA_POINTS)
accel_x = deque(maxlen=MAX_DATA_POINTS)
accel_y = deque(maxlen=MAX_DATA_POINTS)
accel_z = deque(maxlen=MAX_DATA_POINTS)
gyro_x = deque(maxlen=MAX_DATA_POINTS)
gyro_y = deque(maxlen=MAX_DATA_POINTS)
gyro_z = deque(maxlen=MAX_DATA_POINTS)
accel_uncal_x = deque(maxlen=MAX_DATA_POINTS)
accel_uncal_y = deque(maxlen=MAX_DATA_POINTS)
accel_uncal_z = deque(maxlen=MAX_DATA_POINTS)
rotation_rate_x = deque(maxlen=MAX_DATA_POINTS)
rotation_rate_y = deque(maxlen=MAX_DATA_POINTS)
rotation_rate_z = deque(maxlen=MAX_DATA_POINTS)

# Recording state
recording = False
recording_start_time = None
current_recording = None
recordings = deque(maxlen=5)  # Keep last 5 recordings

# MQTT Configuration
MQTT_BROKER = "poggywoggy.world"
MQTT_PORT = 8883  # TLS port
MQTT_TOPIC = "sensor-logger"
MQTT_USERNAME = "sensor"
MQTT_PASSWORD = "SensorLogger2024"


def process_sensor_data(payload):
    """Process sensor data from either HTTP POST or MQTT"""
    # Group data by timestamp
    accel_by_time = {}
    gyro_by_time = {}
    accel_uncal_by_time = {}
    rotation_rate_by_time = {}

    for d in payload:
        ts = datetime.fromtimestamp(d["time"] / 1000000000)
        sensor_name = d.get("name", None)

        if sensor_name == "accelerometer":
            accel_by_time[ts] = d["values"]
        elif sensor_name == "accelerometeruncalibrated":
            accel_uncal_by_time[ts] = d["values"]
        elif sensor_name == "gyroscope":  # Prefer calibrated over uncalibrated
            gyro_by_time[ts] = d["values"]
        elif sensor_name == "gyroscopeuncalibrated" and ts not in gyro_by_time:
            gyro_by_time[ts] = d["values"]
        elif sensor_name == "wrist motion":
            # Extract rotation rate from wrist motion data
            values = d["values"]
            rotation_rate_by_time[ts] = {
                "x": values.get("rotationRateX", 0),
                "y": values.get("rotationRateY", 0),
                "z": values.get("rotationRateZ", 0)
            }

    # Add synced data points
    for ts in sorted(set(accel_by_time.keys()) | set(gyro_by_time.keys()) | set(accel_uncal_by_time.keys()) | set(rotation_rate_by_time.keys())):
        if len(time) == 0 or ts > time[-1]:
            time.append(ts)

            # Add accel if available, else use last value or 0
            if ts in accel_by_time:
                accel_x.append(accel_by_time[ts]["x"])
                accel_y.append(accel_by_time[ts]["y"])
                accel_z.append(accel_by_time[ts]["z"])
            elif len(accel_x) > 0:
                accel_x.append(accel_x[-1])
                accel_y.append(accel_y[-1])
                accel_z.append(accel_z[-1])
            else:
                accel_x.append(0)
                accel_y.append(0)
                accel_z.append(0)

            # Add gyro if available, else use last value or 0
            if ts in gyro_by_time:
                gyro_x.append(gyro_by_time[ts]["x"])
                gyro_y.append(gyro_by_time[ts]["y"])
                gyro_z.append(gyro_by_time[ts]["z"])
            elif len(gyro_x) > 0:
                gyro_x.append(gyro_x[-1])
                gyro_y.append(gyro_y[-1])
                gyro_z.append(gyro_z[-1])
            else:
                gyro_x.append(0)
                gyro_y.append(0)
                gyro_z.append(0)

            # Add uncalibrated accel if available, else use last value or 0
            if ts in accel_uncal_by_time:
                accel_uncal_x.append(accel_uncal_by_time[ts]["x"])
                accel_uncal_y.append(accel_uncal_by_time[ts]["y"])
                accel_uncal_z.append(accel_uncal_by_time[ts]["z"])
            elif len(accel_uncal_x) > 0:
                accel_uncal_x.append(accel_uncal_x[-1])
                accel_uncal_y.append(accel_uncal_y[-1])
                accel_uncal_z.append(accel_uncal_z[-1])
            else:
                accel_uncal_x.append(0)
                accel_uncal_y.append(0)
                accel_uncal_z.append(0)

            # Add rotation rate if available, else use last value or 0
            if ts in rotation_rate_by_time:
                rotation_rate_x.append(rotation_rate_by_time[ts]["x"])
                rotation_rate_y.append(rotation_rate_by_time[ts]["y"])
                rotation_rate_z.append(rotation_rate_by_time[ts]["z"])
            elif len(rotation_rate_x) > 0:
                rotation_rate_x.append(rotation_rate_x[-1])
                rotation_rate_y.append(rotation_rate_y[-1])
                rotation_rate_z.append(rotation_rate_z[-1])
            else:
                rotation_rate_x.append(0)
                rotation_rate_y.append(0)
                rotation_rate_z.append(0)

            # Record data if recording is active
            global recording, current_recording
            if recording and current_recording is not None:
                current_recording['time'].append(ts)
                current_recording['accel_x'].append(accel_x[-1])
                current_recording['accel_y'].append(accel_y[-1])
                current_recording['accel_z'].append(accel_z[-1])
                current_recording['gyro_x'].append(gyro_x[-1])
                current_recording['gyro_y'].append(gyro_y[-1])
                current_recording['gyro_z'].append(gyro_z[-1])
                current_recording['accel_uncal_x'].append(accel_uncal_x[-1])
                current_recording['accel_uncal_y'].append(accel_uncal_y[-1])
                current_recording['accel_uncal_z'].append(accel_uncal_z[-1])
                current_recording['rotation_rate_x'].append(rotation_rate_x[-1])
                current_recording['rotation_rate_y'].append(rotation_rate_y[-1])
                current_recording['rotation_rate_z'].append(rotation_rate_z[-1])


def calculate_magnitude(x_arr, y_arr, z_arr):
    """Calculate 3D magnitude from x, y, z components"""
    import math
    return [math.sqrt(x_arr[i]**2 + y_arr[i]**2 + z_arr[i]**2) for i in range(len(x_arr))]


# For asynchronous analysis
analysis_results = {}

def analyze_recording_background(job_id, rec):
    """Wrapper to run analysis in background and store result."""
    import uuid
    print(f"[ANALYSIS] Starting background job {job_id}")
    analyze_recording(rec)
    analysis_results[job_id] = rec
    print(f"[ANALYSIS] Finished background job {job_id}")


def analyze_recording(rec):
    """
    Compute all metrics for a saved recording.
    This refactored version improves heel strike detection and clarifies metrics.
    """
    print(f"[ANALYSIS] Starting analysis for recording with {len(rec.get('time', []))} samples")
    import numpy as np
    from datetime import timedelta

    # Initialize metrics structure
    rec['metrics'] = {
        'heel_strike_time': None,
        'max_accel_x_time': None,
        'peak_hip_speed_deg_s': None,
        'peak_hip_speed_time': None,
        'hip_rotation_direction': None,
        'time_to_peak_hip_speed_ms': None,
        'peak_wrist_speed_deg_s': None,
        'peak_wrist_speed_time': None,
        'time_to_peak_wrist_speed_ms': None,
        'swing_feedback': "INSUFFICIENT DATA",
        'hip_angular_velocity_mag': [],
        'wrist_angular_velocity_mag': [],
    }

    # --- 1. Data Extraction and Validation ---
    time_arr = rec.get('time', [])
    accel_x = np.array(rec.get('accel_uncal_x', []))
    gyro_x = np.array(rec.get('gyro_x', []))
    gyro_y = np.array(rec.get('gyro_y', []))
    gyro_z = np.array(rec.get('gyro_z', []))
    rotation_rate_x = np.array(rec.get('rotation_rate_x', []))
    rotation_rate_y = np.array(rec.get('rotation_rate_y', []))
    rotation_rate_z = np.array(rec.get('rotation_rate_z', []))

    if len(time_arr) < 2 or len(accel_x) < 2 or len(gyro_x) < 2:
        print("[ANALYSIS] Insufficient data for analysis.")
        return

    # --- 2. Event Detection: Heel Strike and Max Acceleration ---
    try:
        # Find peak positive X-axis acceleration (max force of foot plant)
        max_accel_x_idx = np.argmax(accel_x)
        max_accel_x_time = time_arr[max_accel_x_idx]

        # Find preceding minimum X-axis acceleration (the actual heel strike)
        preceding_accel_x_segment = accel_x[:max_accel_x_idx]
        if len(preceding_accel_x_segment) > 0:
            heel_strike_idx = np.argmin(preceding_accel_x_segment)
            heel_strike_time = time_arr[heel_strike_idx]
            rec['metrics']['heel_strike_time'] = heel_strike_time
            rec['metrics']['max_accel_x_time'] = max_accel_x_time
            print(f"[ANALYSIS] Heel strike detected at {heel_strike_time.strftime('%H:%M:%S.%f')[:-3]}")
        else:
            # Fallback if peak is at the start
            heel_strike_time = max_accel_x_time
            rec['metrics']['heel_strike_time'] = heel_strike_time
            rec['metrics']['max_accel_x_time'] = max_accel_x_time
            print("[ANALYSIS] Warning: Max acceleration at start of data, using as heel strike time.")

    except (ValueError, IndexError) as e:
        print(f"[ANALYSIS] Could not determine heel strike: {e}")
        return # Cannot proceed without heel strike time

    # --- 3. Angular Velocity Analysis ---
    # Hip rotation
    try:
        hip_angular_velocity_mag = np.sqrt(gyro_x**2 + gyro_y**2 + gyro_z**2)
        peak_hip_speed_idx = np.argmax(hip_angular_velocity_mag)
        peak_hip_speed_rad_s = hip_angular_velocity_mag[peak_hip_speed_idx]
        peak_hip_speed_deg_s = np.rad2deg(peak_hip_speed_rad_s)
        peak_hip_speed_time = time_arr[peak_hip_speed_idx]
        
        # Determine direction from gyro_x at the peak
        hip_rotation_direction = "RIGHT" if gyro_x[peak_hip_speed_idx] > 0 else "LEFT"
        
        rec['metrics']['hip_angular_velocity_mag'] = hip_angular_velocity_mag.tolist()
        rec['metrics']['peak_hip_speed_deg_s'] = peak_hip_speed_deg_s
        rec['metrics']['peak_hip_speed_time'] = peak_hip_speed_time
        rec['metrics']['hip_rotation_direction'] = hip_rotation_direction
        print(f"[ANALYSIS] Peak Hip Speed: {peak_hip_speed_deg_s:.2f} deg/s")

    except (ValueError, IndexError) as e:
        print(f"[ANALYSIS] Could not determine hip speed: {e}")
        peak_hip_speed_time = None # Ensure this is None if calculation fails

    # Wrist rotation (if available)
    if len(rotation_rate_x) > 0:
        try:
            wrist_angular_velocity_mag = np.sqrt(rotation_rate_x**2 + rotation_rate_y**2 + rotation_rate_z**2)
            peak_wrist_speed_idx = np.argmax(wrist_angular_velocity_mag)
            peak_wrist_speed_rad_s = wrist_angular_velocity_mag[peak_wrist_speed_idx]
            peak_wrist_speed_deg_s = np.rad2deg(peak_wrist_speed_rad_s)
            peak_wrist_speed_time = time_arr[peak_wrist_speed_idx]
            
            rec['metrics']['wrist_angular_velocity_mag'] = wrist_angular_velocity_mag.tolist()
            rec['metrics']['peak_wrist_speed_deg_s'] = peak_wrist_speed_deg_s
            rec['metrics']['peak_wrist_speed_time'] = peak_wrist_speed_time
            print(f"[ANALYSIS] Peak Wrist Speed: {peak_wrist_speed_deg_s:.2f} deg/s")
        except (ValueError, IndexError) as e:
            print(f"[ANALYSIS] Could not determine wrist speed: {e}")
            peak_wrist_speed_time = None
    else:
        peak_wrist_speed_time = None

    # --- 4. Timing and Feedback Metrics ---
    if heel_strike_time and peak_hip_speed_time:
        time_to_peak_hip_speed = (peak_hip_speed_time - heel_strike_time).total_seconds() * 1000
        rec['metrics']['time_to_peak_hip_speed_ms'] = time_to_peak_hip_speed
        print(f"[ANALYSIS] Time from Heel Strike to Peak Hip Speed: {time_to_peak_hip_speed:.1f} ms")

        # Clarified third metric: Time difference between peak hip speed and max foot acceleration
        # This indicates how closely the peak rotation is coupled with the peak force application into the ground.
        time_hip_to_accel_peak = (peak_hip_speed_time - max_accel_x_time).total_seconds() * 1000
        rec['metrics']['time_hip_speed_to_max_accel_ms'] = time_hip_to_accel_peak
        print(f"[ANALYSIS] Time from Max Accel to Peak Hip Speed: {time_hip_to_accel_peak:.1f} ms")
        
        # Updated Swing Feedback Logic
        if 50 < time_to_peak_hip_speed < 150:
             rec['metrics']['swing_feedback'] = "GOOD SEQUENCE"
        elif time_to_peak_hip_speed <= 50:
             rec['metrics']['swing_feedback'] = "HIPS A BIT EARLY"
        else:
             rec['metrics']['swing_feedback'] = "HIPS A BIT LATE"
    
    if heel_strike_time and peak_wrist_speed_time:
        time_to_peak_wrist_speed = (peak_wrist_speed_time - heel_strike_time).total_seconds() * 1000
        rec['metrics']['time_to_peak_wrist_speed_ms'] = time_to_peak_wrist_speed
        print(f"[ANALYSIS] Time from Heel Strike to Peak Wrist Speed: {time_to_peak_wrist_speed:.1f} ms")

    print(f"[ANALYSIS] Final feedback: {rec['metrics']['swing_feedback']}")


def save_recording(rec):
    """Save recording to disk with signals and metadata"""
    try:
        # Create filename based on start time
        timestamp = rec['start_time'].strftime('%Y%m%d_%H%M%S')
        filename = f"recording_{timestamp}.json"
        filepath = STORAGE_DIR / filename

        # Prepare data for JSON serialization (convert datetime objects to strings)
        recording_data = {
            'metadata': {
                'start_time': rec['start_time'].isoformat(),
                'end_time': rec['end_time'].isoformat() if 'end_time' in rec else None,
                'duration': rec.get('duration', 0),
                'samples': rec.get('samples', len(rec['time'])),
            },
            'signals': {
                'time': [t.isoformat() for t in rec['time']],
                'accel_x': rec['accel_x'],
                'accel_y': rec['accel_y'],
                'accel_z': rec['accel_z'],
                'gyro_x': rec['gyro_x'],
                'gyro_y': rec['gyro_y'],
                'gyro_z': rec['gyro_z'],
                'accel_uncal_x': rec['accel_uncal_x'],
                'accel_uncal_y': rec['accel_uncal_y'],
                'accel_uncal_z': rec['accel_uncal_z'],
                'rotation_rate_x': rec.get('rotation_rate_x', []),
                'rotation_rate_y': rec.get('rotation_rate_y', []),
                'rotation_rate_z': rec.get('rotation_rate_z', []),
            },
            'metrics': {}
        }

        # Add metrics if they exist (convert all datetime objects)
        if 'metrics' in rec and rec['metrics']:
            metrics = rec['metrics'].copy()
            for key, value in metrics.items():
                if isinstance(value, datetime):
                    metrics[key] = value.isoformat()
            recording_data['metrics'] = metrics

        # Save to file
        with open(filepath, 'w') as f:
            json.dump(recording_data, f, indent=2)

        print(f"[STORAGE] Recording saved to {filepath}")
        return str(filepath)
    except Exception as e:
        print(f"[STORAGE] Error saving recording: {e}")
        import traceback
        traceback.print_exc()
        return None


@server.route("/data", methods=["POST"])
def data():
    """HTTP POST endpoint (fallback/alternative to MQTT)"""
    if str(request.method) == "POST":
        print(f"[HTTP] Received data: {len(request.data)} bytes")
        data = json.loads(request.data)
        process_sensor_data(data["payload"])
    return "success"


# MQTT Callbacks
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[MQTT] Connected to broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        print(f"[MQTT] Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"[MQTT] Connection failed with code {rc}")


def on_message(client, userdata, msg):
    """Process incoming MQTT messages"""
    try:
        data = json.loads(msg.payload.decode())
        print(f"[MQTT] Received message #{data.get('messageId', '?')} from session {data.get('sessionId', '?')[:8]}...")
        process_sensor_data(data["payload"])
    except Exception as e:
        print(f"[MQTT] Error processing message: {e}")


def on_disconnect(client, userdata, rc, properties=None):
    if rc != 0:
        print(f"[MQTT] Unexpected disconnection. Reconnecting...")


def start_mqtt_client():
    """Start MQTT client in a separate thread"""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # Enable TLS
    client.tls_set(cert_reqs=ssl.CERT_NONE)  # Use CERT_REQUIRED in production with proper CA
    client.tls_insecure_set(True)  # Only for self-signed certs

    try:
        print(f"[MQTT] Connecting to {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as e:
        print(f"[MQTT] Connection error: {e}")
