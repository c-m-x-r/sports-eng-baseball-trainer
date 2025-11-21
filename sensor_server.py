import dash
from dash.dependencies import Output, Input
from dash import dcc, html, dcc
from datetime import datetime
import json
import plotly.graph_objs as go
from collections import deque
from flask import Flask, request
import paho.mqtt.client as mqtt
import threading
import ssl

server = Flask(__name__)
app = dash.Dash(
    __name__,
    server=server,
    url_base_pathname='/sensor/'
)

MAX_DATA_POINTS = 400  # Reduced for better performance
UPDATE_FREQ_MS = 500   # Update every 500ms instead of 100ms

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

app.layout = html.Div(
    [
        dcc.Markdown(
            children="""
            # Live Sensor Readings
            Streamed from Sensor Logger: [tszheichoi.com/sensorlogger](https://tszheichoi.com/sensorlogger)

            **Status:** Waiting for data...

            **MQTT Settings:**
            - Broker: `poggywoggy.world`
            - Port: `8884` (WebSocket) or `8883` (TCP)
            - Username: `sensor`
            - Topic: `sensor-logger`
            - TLS: Required

            **HTTP POST Alternative:**
            - URL: `https://poggywoggy.world/data`
        """
        ),
        html.Div([
            html.H3("Recording Controls"),
            html.Button("START (Ready)", id="start-btn", n_clicks=0,
                       style={'marginRight': '10px', 'padding': '10px 20px', 'fontSize': '16px', 'backgroundColor': '#28a745', 'color': 'white', 'border': 'none', 'cursor': 'pointer'}),
            html.Button("STOP (Finish)", id="stop-btn", n_clicks=0,
                       style={'padding': '10px 20px', 'fontSize': '16px', 'backgroundColor': '#dc3545', 'color': 'white', 'border': 'none', 'cursor': 'pointer'}),
            html.Div(id="recording-status", style={'marginTop': '10px', 'fontSize': '18px', 'fontWeight': 'bold'}),
            html.Div(id="recordings-count", style={'marginTop': '5px', 'fontSize': '14px', 'color': '#666'}),
        ], style={'margin': '20px 0', 'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '5px'}),
        html.Div(id="recordings-display", children=[], style={'margin': '20px 0'}),
        dcc.Graph(id="accel_graph"),
        dcc.Graph(id="gyro_graph"),
        dcc.Graph(id="accel_uncal_graph"),
        dcc.Interval(id="counter", interval=UPDATE_FREQ_MS),
    ]
)


def process_sensor_data(payload):
    """Process sensor data from either HTTP POST or MQTT"""
    # Group data by timestamp
    accel_by_time = {}
    gyro_by_time = {}
    accel_uncal_by_time = {}

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

    # Add synced data points
    for ts in sorted(set(accel_by_time.keys()) | set(gyro_by_time.keys()) | set(accel_uncal_by_time.keys())):
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

    # 4. Gyro_x value at time of peak accelerometer magnitude
    gyro_x_at_peak_accel = gyro_x[peak_accel_mag_idx]

    # 5. Time difference between peak gyro_x and peak accel magnitude
    time_diff_ms = (peak_gyro_x_time - peak_accel_mag_time).total_seconds() * 1000

    # Store all metrics
    rec['metrics'] = {
        'peak_gyro_x_value': peak_gyro_x_value,
        'peak_gyro_x_time': peak_gyro_x_time,
        'gyro_direction': gyro_direction,
        'peak_accel_mag_value': peak_accel_mag_value,
        'peak_accel_mag_time': peak_accel_mag_time,
        'peak_accel_uncal_mag_value': peak_accel_uncal_mag_value,
        'peak_accel_uncal_mag_time': peak_accel_uncal_mag_time,
        'gyro_x_at_peak_accel': gyro_x_at_peak_accel,
        'time_diff_ms': time_diff_ms,
        'accel_mag': accel_mag,  # Store for plotting
        'accel_uncal_mag': accel_uncal_mag  # Store for plotting
    }

    print(f"[ANALYSIS] Peak Gyro X: {peak_gyro_x_value:.2f} rad/s ({gyro_direction}) at {peak_gyro_x_time.strftime('%H:%M:%S.%f')[:-3]}")
    print(f"[ANALYSIS] Peak Accel Mag: {peak_accel_mag_value:.2f} m/s² at {peak_accel_mag_time.strftime('%H:%M:%S.%f')[:-3]}")
    print(f"[ANALYSIS] Time diff: {time_diff_ms:.1f} ms, Gyro X at peak accel: {gyro_x_at_peak_accel:.2f} rad/s")


@app.callback(
    Output("accel_graph", "figure"),
    Output("gyro_graph", "figure"),
    Output("accel_uncal_graph", "figure"),
    Input("counter", "n_intervals")
)
def update_graphs(_counter):
    # Accelerometer graph
    accel_data = [
        go.Scatter(
            x=list(time)[:len(accel_x)], y=list(d), name=name,
            mode='lines', line=dict(width=1), hoverinfo='skip'
        )
        for d, name in zip([accel_x, accel_y, accel_z], ["X", "Y", "Z"])
    ]

    accel_graph = {
        "data": accel_data,
        "layout": go.Layout(
            title="Accelerometer (Calibrated)",
            xaxis={"type": "date", "range": [min(time), max(time)] if len(time) > 0 else None},
            yaxis={"title": "m/s²", "range": [-60, 60]},
            margin=dict(l=50, r=20, t=40, b=30),
            height=300,
            showlegend=True,
            uirevision='accel'
        ),
    }

    # Gyroscope graph
    gyro_data = [
        go.Scatter(
            x=list(time)[:len(gyro_x)], y=list(d), name=name,
            mode='lines', line=dict(width=1), hoverinfo='skip'
        )
        for d, name in zip([gyro_x, gyro_y, gyro_z], ["X", "Y", "Z"])
    ]

    gyro_graph = {
        "data": gyro_data,
        "layout": go.Layout(
            title="Gyroscope",
            xaxis={"type": "date", "range": [min(time), max(time)] if len(time) > 0 else None},
            yaxis={"title": "rad/s", "range": [-30, 30]},
            margin=dict(l=50, r=20, t=40, b=30),
            height=300,
            showlegend=True,
            uirevision='gyro'
        ),
    }

    # Uncalibrated Accelerometer graph
    accel_uncal_data = [
        go.Scatter(
            x=list(time)[:len(accel_uncal_x)], y=list(d), name=name,
            mode='lines', line=dict(width=1), hoverinfo='skip'
        )
        for d, name in zip([accel_uncal_x, accel_uncal_y, accel_uncal_z], ["X", "Y", "Z"])
    ]

    accel_uncal_graph = {
        "data": accel_uncal_data,
        "layout": go.Layout(
            title="Accelerometer (Uncalibrated)",
            xaxis={"type": "date", "range": [min(time), max(time)] if len(time) > 0 else None},
            yaxis={"title": "m/s²", "range": [-60, 60]},
            margin=dict(l=50, r=20, t=40, b=30),
            height=300,
            showlegend=True,
            uirevision='accel_uncal'
        ),
    }

    return accel_graph, gyro_graph, accel_uncal_graph


@app.callback(
    Output("recording-status", "children"),
    Output("recordings-count", "children"),
    Input("start-btn", "n_clicks"),
    Input("stop-btn", "n_clicks"),
    prevent_initial_call=True
)
def handle_recording(start_clicks, stop_clicks):
    global recording, recording_start_time, current_recording, recordings

    ctx = dash.callback_context
    if not ctx.triggered:
        return "Ready", f"Recordings saved: {len(recordings)}/5"

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "start-btn":
        if not recording:
            recording = True
            recording_start_time = datetime.now()
            current_recording = {
                'start_time': recording_start_time,
                'time': [],
                'accel_x': [], 'accel_y': [], 'accel_z': [],
                'gyro_x': [], 'gyro_y': [], 'gyro_z': [],
                'accel_uncal_x': [], 'accel_uncal_y': [], 'accel_uncal_z': []
            }
            print(f"[RECORDING] Started at {recording_start_time}")
            return "🔴 RECORDING...", f"Recordings saved: {len(recordings)}/5"

    elif button_id == "stop-btn":
        print(f"[DEBUG] STOP button pressed. recording={recording}, current_recording exists={current_recording is not None}")
        if recording:
            recording = False
            if current_recording and len(current_recording['time']) > 0:
                print(f"[DEBUG] Recording has {len(current_recording['time'])} samples")
                current_recording['end_time'] = datetime.now()
                duration = (current_recording['end_time'] - current_recording['start_time']).total_seconds()
                current_recording['duration'] = duration
                current_recording['samples'] = len(current_recording['time'])
                samples = current_recording['samples']

                # Analyze recording to compute metrics
                try:
                    analyze_recording(current_recording)
                except Exception as e:
                    print(f"[ERROR] Analysis failed: {e}")
                    import traceback
                    traceback.print_exc()
                    current_recording['metrics'] = {}

                recordings.append(current_recording)
                print(f"[RECORDING] Stopped. Duration: {duration:.2f}s, Samples: {samples}, Total recordings: {len(recordings)}")
                current_recording = None
                return f"✓ Recording saved ({duration:.1f}s, {samples} samples)", f"Recordings saved: {len(recordings)}/5"
            else:
                print("[RECORDING] Stopped but no data captured")
                current_recording = None
                return "⚠ Stopped (no data)", f"Recordings saved: {len(recordings)}/5"

    return "Ready", f"Recordings saved: {len(recordings)}/5"


@app.callback(
    Output("recordings-display", "children"),
    Input("recordings-count", "children"),
    prevent_initial_call=True
)
def update_recordings_display(_):
    """Generate visualization for all saved recordings"""
    print(f"[DEBUG] update_recordings_display called. {len(recordings)} recordings available")

    if len(recordings) == 0:
        print("[DEBUG] No recordings to display")
        return []

    recording_divs = []

    # Display newest first
    for idx, rec in enumerate(reversed(list(recordings))):
        rec_num = len(recordings) - idx
        print(f"[DEBUG] Processing recording #{rec_num}")

        if 'metrics' not in rec or not rec['metrics']:
            print(f"[DEBUG] Recording #{rec_num} has no metrics, skipping")
            continue

        metrics = rec['metrics']
        time_arr = rec['time']
        print(f"[DEBUG] Recording #{rec_num} has {len(time_arr)} samples, creating visualizations")

        # Format metrics text
        metrics_text = [
            html.H4(f"Recording #{rec_num} - {rec['start_time'].strftime('%H:%M:%S')}", style={'marginBottom': '10px'}),
            html.Div([
                html.Span(f"Peak Gyro X: ", style={'fontWeight': 'bold'}),
                html.Span(f"{metrics['peak_gyro_x_value']:.2f} rad/s ({metrics['gyro_direction']}) at {metrics['peak_gyro_x_time'].strftime('%H:%M:%S.%f')[:-3]}"),
                html.Br(),
                html.Span(f"Peak Accel Mag (cal): ", style={'fontWeight': 'bold'}),
                html.Span(f"{metrics['peak_accel_mag_value']:.2f} m/s² at {metrics['peak_accel_mag_time'].strftime('%H:%M:%S.%f')[:-3]}"),
                html.Br(),
                html.Span(f"Peak Accel Mag (uncal): ", style={'fontWeight': 'bold'}),
                html.Span(f"{metrics['peak_accel_uncal_mag_value']:.2f} m/s²"),
                html.Br(),
                html.Span(f"Gyro X at peak accel: ", style={'fontWeight': 'bold'}),
                html.Span(f"{metrics['gyro_x_at_peak_accel']:.2f} rad/s"),
                html.Br(),
                html.Span(f"Time difference: ", style={'fontWeight': 'bold'}),
                html.Span(f"{metrics['time_diff_ms']:.1f} ms"),
            ], style={'fontSize': '14px', 'marginBottom': '15px', 'color': '#333'})
        ]

        # Create gyro graph
        gyro_traces = [
            go.Scatter(x=time_arr, y=rec['gyro_x'], name='X', mode='lines', line=dict(width=1)),
            go.Scatter(x=time_arr, y=rec['gyro_y'], name='Y', mode='lines', line=dict(width=1)),
            go.Scatter(x=time_arr, y=rec['gyro_z'], name='Z', mode='lines', line=dict(width=1))
        ]

        gyro_fig = go.Figure(data=gyro_traces, layout=go.Layout(
            title="Gyroscope (rad/s)",
            xaxis={"type": "date"},
            yaxis={"title": "rad/s"},
            height=250,
            margin=dict(l=50, r=20, t=40, b=30),
            shapes=[{
                'type': 'line',
                'x0': metrics['peak_gyro_x_time'],
                'x1': metrics['peak_gyro_x_time'],
                'y0': 0,
                'y1': 1,
                'yref': 'paper',
                'line': {'color': 'red', 'width': 2, 'dash': 'dash'}
            }],
            annotations=[{
                'x': metrics['peak_gyro_x_time'],
                'y': 0.95,
                'yref': 'paper',
                'text': f"Peak Gyro X",
                'showarrow': False,
                'bgcolor': 'rgba(255,0,0,0.7)',
                'font': {'color': 'white', 'size': 10}
            }]
        ))

        # Create accel graph
        accel_traces = [
            go.Scatter(x=time_arr, y=rec['accel_x'], name='X', mode='lines', line=dict(width=1)),
            go.Scatter(x=time_arr, y=rec['accel_y'], name='Y', mode='lines', line=dict(width=1)),
            go.Scatter(x=time_arr, y=rec['accel_z'], name='Z', mode='lines', line=dict(width=1))
        ]

        accel_fig = go.Figure(data=accel_traces, layout=go.Layout(
            title="Accelerometer (m/s²)",
            xaxis={"type": "date"},
            yaxis={"title": "m/s²"},
            height=250,
            margin=dict(l=50, r=20, t=40, b=30),
            shapes=[{
                'type': 'line',
                'x0': metrics['peak_accel_mag_time'],
                'x1': metrics['peak_accel_mag_time'],
                'y0': 0,
                'y1': 1,
                'yref': 'paper',
                'line': {'color': 'blue', 'width': 2, 'dash': 'dash'}
            }],
            annotations=[{
                'x': metrics['peak_accel_mag_time'],
                'y': 0.95,
                'yref': 'paper',
                'text': f"Peak Accel Mag",
                'showarrow': False,
                'bgcolor': 'rgba(0,0,255,0.7)',
                'font': {'color': 'white', 'size': 10}
            }]
        ))

        # Combine into a single recording div
        recording_div = html.Div([
            *metrics_text,
            html.Div([
                html.Div([dcc.Graph(figure=gyro_fig, config={'displayModeBar': False})],
                         style={'width': '49%', 'display': 'inline-block'}),
                html.Div([dcc.Graph(figure=accel_fig, config={'displayModeBar': False})],
                         style={'width': '49%', 'display': 'inline-block', 'marginLeft': '2%'})
            ])
        ], style={
            'padding': '20px',
            'backgroundColor': '#ffffff',
            'borderRadius': '8px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
            'marginBottom': '20px',
            'border': '1px solid #ddd'
        })

        recording_divs.append(recording_div)
        print(f"[DEBUG] Recording #{rec_num} visualization created")

    print(f"[DEBUG] Returning {len(recording_divs)} recording visualizations")
    return recording_divs


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


if __name__ == "__main__":
    # Start MQTT client in background thread
    mqtt_thread = threading.Thread(target=start_mqtt_client, daemon=True)
    mqtt_thread.start()
    print("[Server] MQTT client started in background")

    # Start Dash/Flask server
    print("[Server] Starting Dash server on port 8000")
    app.run(port=8000, host="0.0.0.0")
