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


def analyze_recording(rec):
    """Compute all metrics for a saved recording"""
    print(f"[ANALYSIS] Starting analysis for recording with {len(rec['time'])} samples")

    # Extract arrays
    gyro_x = rec['gyro_x']
    gyro_y = rec['gyro_y']
    gyro_z = rec['gyro_z']
    accel_x = rec['accel_x']
    accel_y = rec['accel_y']
    accel_z = rec['accel_z']
    accel_uncal_x = rec['accel_uncal_x']
    accel_uncal_y = rec['accel_uncal_y']
    accel_uncal_z = rec['accel_uncal_z']
    rotation_rate_x = rec.get('rotation_rate_x', [])
    rotation_rate_y = rec.get('rotation_rate_y', [])
    rotation_rate_z = rec.get('rotation_rate_z', [])
    time_arr = rec['time']

    if len(gyro_x) == 0:
        rec['metrics'] = {}
        return

    # 1. Peak gyro_x (max absolute value, preserve sign for direction)
    gyro_x_abs = [abs(v) for v in gyro_x]
    peak_gyro_x_idx = gyro_x_abs.index(max(gyro_x_abs))
    peak_gyro_x_value = gyro_x[peak_gyro_x_idx]
    peak_gyro_x_time = time_arr[peak_gyro_x_idx]
    gyro_direction = "RIGHT" if peak_gyro_x_value > 0 else "LEFT"

    # 2. Peak accelerometer magnitude (calibrated)
    accel_mag = calculate_magnitude(accel_x, accel_y, accel_z)
    peak_accel_mag_idx = accel_mag.index(max(accel_mag))
    peak_accel_mag_value = accel_mag[peak_accel_mag_idx]
    peak_accel_mag_time = time_arr[peak_accel_mag_idx]

    # 3. Peak accelerometer magnitude (uncalibrated)
    accel_uncal_mag = calculate_magnitude(accel_uncal_x, accel_uncal_y, accel_uncal_z)
    peak_accel_uncal_mag_idx = accel_uncal_mag.index(max(accel_uncal_mag))
    peak_accel_uncal_mag_value = accel_uncal_mag[peak_accel_uncal_mag_idx]
    peak_accel_uncal_mag_time = time_arr[peak_accel_uncal_mag_idx]

    # 4. Peak Z-axis acceleration (for foot contact timing)
    accel_z_abs = [abs(v) for v in accel_z]
    peak_accel_z_idx = accel_z_abs.index(max(accel_z_abs))
    peak_accel_z_value = accel_z[peak_accel_z_idx]
    peak_accel_z_time = time_arr[peak_accel_z_idx]

    # 5. Foot contact times (offset from peak uncalibrated acceleration)
    # Use peak_accel_uncal_mag_time as reference as specified by user
    from datetime import timedelta
    contact_100pct_time = peak_accel_uncal_mag_time - timedelta(milliseconds=40)
    contact_10pct_time = peak_accel_uncal_mag_time - timedelta(milliseconds=80)

    # 6. Time from foot contact to peak angular velocity (hip rotation)
    time_from_10pct_to_peak_gyro_ms = (peak_gyro_x_time - contact_10pct_time).total_seconds() * 1000
    time_from_100pct_to_peak_gyro_ms = (peak_gyro_x_time - contact_100pct_time).total_seconds() * 1000

    # 7. Gyro_x value at time of peak accelerometer magnitude
    gyro_x_at_peak_accel = gyro_x[peak_accel_mag_idx]

    # 8. Time difference between peak gyro_x and peak accel magnitude
    time_diff_ms = (peak_gyro_x_time - peak_accel_mag_time).total_seconds() * 1000

    # 9. Swing timing feedback based on offset between peak accel and peak hip angular velocity
    if time_diff_ms > 80:
        swing_feedback = "HIPS FIRED LATE"
    elif time_diff_ms > 30:
        swing_feedback = "NICE SWING!"
    else:
        swing_feedback = "HIPS FIRED EARLY"

    # Store all metrics
    rec['metrics'] = {
        'peak_gyro_x_value': peak_gyro_x_value,
        'peak_gyro_x_time': peak_gyro_x_time,
        'gyro_direction': gyro_direction,
        'peak_accel_mag_value': peak_accel_mag_value,
        'peak_accel_mag_time': peak_accel_mag_time,
        'peak_accel_uncal_mag_value': peak_accel_uncal_mag_value,
        'peak_accel_uncal_mag_time': peak_accel_uncal_mag_time,
        'peak_accel_z_value': peak_accel_z_value,
        'peak_accel_z_time': peak_accel_z_time,
        'contact_100pct_bw_time': contact_100pct_time,
        'contact_10pct_time': contact_10pct_time,
        'time_from_10pct_to_peak_gyro_ms': time_from_10pct_to_peak_gyro_ms,
        'time_from_100pct_to_peak_gyro_ms': time_from_100pct_to_peak_gyro_ms,
        'gyro_x_at_peak_accel': gyro_x_at_peak_accel,
        'time_diff_ms': time_diff_ms,
        'swing_feedback': swing_feedback,
        'accel_mag': accel_mag,  # Store for plotting
        'accel_uncal_mag': accel_uncal_mag  # Store for plotting
    }

    print(f"[ANALYSIS] Peak Gyro X: {peak_gyro_x_value:.2f} rad/s ({gyro_direction}) at {peak_gyro_x_time.strftime('%H:%M:%S.%f')[:-3]}")
    print(f"[ANALYSIS] Peak Accel Mag: {peak_accel_mag_value:.2f} m/s² at {peak_accel_mag_time.strftime('%H:%M:%S.%f')[:-3]}")
    print(f"[ANALYSIS] Peak Accel Z: {peak_accel_z_value:.2f} m/s² at {peak_accel_z_time.strftime('%H:%M:%S.%f')[:-3]}")
    print(f"[ANALYSIS] Foot Contact 10%: {contact_10pct_time.strftime('%H:%M:%S.%f')[:-3]}")
    print(f"[ANALYSIS] Foot Contact 100% BW: {contact_100pct_time.strftime('%H:%M:%S.%f')[:-3]}")
    print(f"[ANALYSIS] Time from 10% contact to peak gyro: {time_from_10pct_to_peak_gyro_ms:.1f} ms")
    print(f"[ANALYSIS] Time from 100% contact to peak gyro: {time_from_100pct_to_peak_gyro_ms:.1f} ms")
    print(f"[ANALYSIS] Time diff (peak gyro to peak accel): {time_diff_ms:.1f} ms")
    print(f"[ANALYSIS] Swing Feedback: {swing_feedback}")


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

        # Add metrics if they exist (convert datetime objects)
        if 'metrics' in rec and rec['metrics']:
            metrics = rec['metrics'].copy()
            # Convert datetime objects in metrics to ISO format strings
            if 'peak_gyro_x_time' in metrics:
                metrics['peak_gyro_x_time'] = metrics['peak_gyro_x_time'].isoformat()
            if 'peak_accel_mag_time' in metrics:
                metrics['peak_accel_mag_time'] = metrics['peak_accel_mag_time'].isoformat()
            if 'peak_accel_uncal_mag_time' in metrics:
                metrics['peak_accel_uncal_mag_time'] = metrics['peak_accel_uncal_mag_time'].isoformat()
            if 'peak_accel_z_time' in metrics:
                metrics['peak_accel_z_time'] = metrics['peak_accel_z_time'].isoformat()
            if 'contact_100pct_bw_time' in metrics:
                metrics['contact_100pct_bw_time'] = metrics['contact_100pct_bw_time'].isoformat()
            if 'contact_10pct_time' in metrics:
                metrics['contact_10pct_time'] = metrics['contact_10pct_time'].isoformat()
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
