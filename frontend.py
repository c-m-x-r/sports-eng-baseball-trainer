import dash
from dash.dependencies import Output, Input
from dash import dcc, html, dcc
from datetime import datetime
import plotly.graph_objs as go

# Import backend components
from backend import (
    server,
    MAX_DATA_POINTS,
    UPDATE_FREQ_MS,
    time,
    accel_x, accel_y, accel_z,
    gyro_x, gyro_y, gyro_z,
    accel_uncal_x, accel_uncal_y, accel_uncal_z,
    rotation_rate_x, rotation_rate_y, rotation_rate_z,
    recording, recording_start_time, current_recording, recordings,
    analyze_recording,
    save_recording
)

# Create Dash app
app = dash.Dash(
    __name__,
    server=server,
    url_base_pathname='/sensor/',
    external_stylesheets=['https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600;700&display=swap']
)

# Wii Sports inspired color scheme
WII_BLUE = '#0099FF'
WII_LIGHT_BLUE = '#66CCFF'
WII_WHITE = '#FFFFFF'
WII_ORANGE = '#FF9933'
WII_GREEN = '#33CC66'
WII_RED = '#FF3366'
WII_GRAY = '#F0F4F8'

app.layout = html.Div(
    style={
        'fontFamily': 'Fredoka, Arial, sans-serif',
        'backgroundColor': WII_BLUE,
        'minHeight': '100vh',
        'padding': '20px',
        'background': f'linear-gradient(135deg, {WII_BLUE} 0%, {WII_LIGHT_BLUE} 100%)'
    },
    children=[
        # Header
        html.Div([
            html.H1("⚾ Swing Like Springer",
                   style={
                       'textAlign': 'left',
                       'color': WII_WHITE,
                       'fontSize': '64px',
                       'fontWeight': '700',
                       'margin': '20px 0',
                       'textShadow': '4px 4px 8px rgba(0,0,0,0.3)',
                       'letterSpacing': '2px'
                   }),
            html.H2("Powered by Sensor Logger @tszheichoi",
                   style={
                       'textAlign': 'left',
                       'color': WII_WHITE,
                       'fontSize': '32px',
                       'fontWeight': '400',
                       'marginLeft': '20px',
                       'smarginTop': '0',
                       'marginBottom': '30px',
                       'textShadow': '2px 2px 4px rgba(0,0,0,0.2)'
                   }),
        ]),

        # Main content container
        html.Div(
            style={
                'maxWidth': '1400px',
                'margin': '0 auto',
                'backgroundColor': WII_WHITE,
                'padding': '40px',
                'boxShadow': '0 10px 40px rgba(0,0,0,0.3)'
            },
            children=[
                # Purpose section (collapsible)
                html.Div([
                    html.Button([
                        html.Span("ℹ️ ", style={'fontSize': '24px', 'marginRight': '10px'}),
                        html.Span("APP INFO & INSTRUCTIONS", style={'fontSize': '20px', 'fontWeight': '700'}),
                        html.Span(" (Click to expand)", id="info-toggle-text", style={'fontSize': '14px', 'marginLeft': '10px', 'fontWeight': '400', 'fontStyle': 'italic'})
                    ],
                    id="info-toggle-btn",
                    n_clicks=0,
                    style={
                        'width': '100%',
                        'padding': '15px',
                        'backgroundColor': WII_BLUE,
                        'color': WII_WHITE,
                        'border': 'none',
                        'borderRadius': '15px',
                        'cursor': 'pointer',
                        'fontSize': '18px',
                        'fontWeight': '600',
                        'fontFamily': 'Fredoka, Arial, sans-serif',
                        'textAlign': 'left',
                        'boxShadow': '0 4px 10px rgba(0,0,0,0.2)',
                        'marginBottom': '15px',
                        'transition': 'all 0.3s'
                    }),

                    html.Div([
                        html.H3("🎯 WHAT IS THIS APP?",
                               style={'color': WII_BLUE, 'fontSize': '28px', 'fontWeight': '700', 'marginBottom': '15px'}),
                        html.P([
                            "\"Use your lower body!\" - Every coach ever. But what does that actually ",
                            html.Span("feel", style={'fontWeight': '700', 'fontStyle': 'italic', 'color': WII_ORANGE}),
                            " like?"
                        ], style={'fontSize': '18px', 'lineHeight': '1.6', 'marginBottom': '10px', 'color': '#333'}),
                        html.P([
                            "This app turns your phone into a ",
                            html.Span("hitting coach", style={'fontWeight': '700', 'color': WII_BLUE}),
                            " by measuring your hip rotation and timing. Get real-time data on your swing mechanics and compare yourself to high school, college, and pro players."
                        ], style={'fontSize': '16px', 'lineHeight': '1.6', 'marginBottom': '20px', 'color': '#333'}),

                        html.Div([
                            html.H4("📊 WHAT WE MEASURE:",
                                   style={'color': WII_BLUE, 'fontSize': '20px', 'fontWeight': '700', 'marginBottom': '10px'}),
                            html.Ul([
                                html.Li([
                                    html.Span("Foot Contact Time", style={'fontWeight': '700', 'color': WII_ORANGE}),
                                    html.Span(" - When your front foot plants", style={'fontWeight': '400'})
                                ], style={'marginBottom': '8px', 'fontSize': '16px'}),
                                html.Li([
                                    html.Span("Hip Rotation Speed", style={'fontWeight': '700', 'color': WII_ORANGE}),
                                    html.Span(" - How fast your hips are turning (angular velocity)", style={'fontWeight': '400'})
                                ], style={'marginBottom': '8px', 'fontSize': '16px'}),
                                html.Li([
                                    html.Span("Timing", style={'fontWeight': '700', 'color': WII_ORANGE}),
                                    html.Span(" - The delay from foot plant to peak hip rotation", style={'fontWeight': '400'})
                                ], style={'marginBottom': '8px', 'fontSize': '16px'}),
                            ], style={'marginLeft': '20px', 'color': '#333'}),
                        ], style={'marginBottom': '25px', 'padding': '15px', 'backgroundColor': WII_WHITE, 'borderRadius': '12px'}),

                        html.Div([
                            html.H4("📲 HOW TO USE:",
                                   style={'color': WII_BLUE, 'fontSize': '20px', 'fontWeight': '700', 'marginBottom': '10px'}),
                            html.Ol([
                                html.Li([
                                    html.Span("Download ", style={'fontWeight': '400'}),
                                    html.A("Sensor Logger",
                                          href="https://tszheichoi.com/sensorlogger",
                                          style={'color': WII_ORANGE, 'textDecoration': 'none', 'fontWeight': '700'}),
                                    html.Span(" and connect it to ", style={'fontWeight': '400'}),
                                    html.Code("poggywoggy.world:8883",
                                            style={'backgroundColor': WII_WHITE, 'padding': '2px 8px', 'borderRadius': '4px', 'fontSize': '14px', 'fontWeight': '600'})
                                ], style={'marginBottom': '12px', 'fontSize': '16px', 'lineHeight': '1.8'}),
                                html.Li([
                                    html.Span("Strap your phone to your ", style={'fontWeight': '400'}),
                                    html.Span("waist/belt", style={'fontWeight': '700', 'color': WII_BLUE}),
                                    html.Span(" (screen facing forward)", style={'fontWeight': '400'})
                                ], style={'marginBottom': '12px', 'fontSize': '16px'}),
                                html.Li([
                                    html.Span("Get in your ", style={'fontWeight': '400'}),
                                    html.Span("batting stance", style={'fontWeight': '700', 'color': WII_BLUE}),
                                    html.Span(" and stay still", style={'fontWeight': '400'})
                                ], style={'marginBottom': '12px', 'fontSize': '16px'}),
                                html.Li([
                                    html.Span("Hit ", style={'fontWeight': '400'}),
                                    html.Span("START", style={'fontWeight': '700', 'color': WII_GREEN, 'fontSize': '18px'}),
                                    html.Span(" → Take your swing → Hit ", style={'fontWeight': '400'}),
                                    html.Span("STOP", style={'fontWeight': '700', 'color': WII_RED, 'fontSize': '18px'})
                                ], style={'marginBottom': '12px', 'fontSize': '16px'}),
                                html.Li([
                                    html.Span("Check your analytics below!", style={'fontWeight': '700', 'color': WII_ORANGE, 'fontSize': '17px'})
                                ], style={'marginBottom': '8px', 'fontSize': '16px'}),
                            ], style={'marginLeft': '20px', 'color': '#333'}),
                        ], style={'padding': '15px', 'backgroundColor': WII_WHITE, 'borderRadius': '12px'}),
                    ], id="info-content", style={'display': 'none', 'padding': '20px', 'backgroundColor': WII_GRAY, 'borderRadius': '15px'}),
                ], style={'marginBottom': '30px', 'padding': '5px', 'backgroundColor': WII_WHITE}),

                # Recording Controls
                html.Div([
                    html.H2("🎮 RECORDING CONTROLS",
                           style={
                               'color': WII_BLUE,
                               'fontSize': '36px',
                               'fontWeight': '700',
                               'marginBottom': '20px',
                               'textAlign': 'center'
                           }),
                    html.Div([
                        html.Button("START",
                                   id="start-btn",
                                   n_clicks=0,
                                   style={
                                       'padding': '25px 60px',
                                       'fontSize': '32px',
                                       'fontWeight': '700',
                                       'backgroundColor': WII_GREEN,
                                       'color': WII_WHITE,
                                       'border': 'none',
                                       'borderRadius': '20px',
                                       'cursor': 'pointer',
                                       'marginRight': '20px',
                                       'boxShadow': '0 8px 0 #28a745, 0 12px 20px rgba(0,0,0,0.3)',
                                       'transition': 'all 0.1s',
                                       'fontFamily': 'Fredoka, Arial, sans-serif',
                                       'position': 'relative',
                                       'top': '0'
                                   }),
                        html.Button("STOP",
                                   id="stop-btn",
                                   n_clicks=0,
                                   style={
                                       'padding': '25px 60px',
                                       'fontSize': '32px',
                                       'fontWeight': '700',
                                       'backgroundColor': WII_RED,
                                       'color': WII_WHITE,
                                       'border': 'none',
                                       'borderRadius': '20px',
                                       'cursor': 'pointer',
                                       'boxShadow': '0 8px 0 #cc0033, 0 12px 20px rgba(0,0,0,0.3)',
                                       'transition': 'all 0.1s',
                                       'fontFamily': 'Fredoka, Arial, sans-serif',
                                       'position': 'relative',
                                       'top': '0'
                                   }),
                    ], style={'textAlign': 'center', 'marginBottom': '25px'}),
                    html.Div(id="recording-status",
                            style={
                                'marginTop': '20px',
                                'fontSize': '28px',
                                'fontWeight': '700',
                                'textAlign': 'center',
                                'color': WII_BLUE,
                                'padding': '15px',
                                'backgroundColor': WII_GRAY,
                                'borderRadius': '15px'
                            }),
                    html.Div(id="recordings-count",
                            style={
                                'marginTop': '10px',
                                'fontSize': '20px',
                                'textAlign': 'center',
                                'color': '#666',
                                'fontWeight': '600'
                            }),
                ], style={
                    'margin': '30px 0',
                    'padding': '20px',
                    'backgroundColor': WII_WHITE,
                    'borderRadius': '25px',
                    'border': f'5px solid {WII_BLUE}',
                    'boxShadow': '0 5px 20px rgba(0,153,255,0.2)'
                }),

                # Recordings display
                html.Div(id="recordings-display", children=[], style={'margin': '30px 0'}),

                # Graphs
                html.Div([
                    dcc.Graph(id="accel_graph",
                             style={'marginBottom': '20px', 'borderRadius': '15px', 'overflow': 'hidden'}),
                    dcc.Graph(id="gyro_graph",
                             style={'marginBottom': '20px', 'borderRadius': '15px', 'overflow': 'hidden'}),
                    dcc.Graph(id="accel_uncal_graph",
                             style={'marginBottom': '20px', 'borderRadius': '15px', 'overflow': 'hidden'}),
                    dcc.Graph(id="rotation_rate_graph",
                             style={'borderRadius': '15px', 'overflow': 'hidden'}),
                ], style={'marginTop': '30px'}),
            ]
        ),

        dcc.Interval(id="counter", interval=UPDATE_FREQ_MS),
    ]
)


@app.callback(
    Output("accel_graph", "figure"),
    Output("gyro_graph", "figure"),
    Output("accel_uncal_graph", "figure"),
    Output("rotation_rate_graph", "figure"),
    Input("counter", "n_intervals")
)
def update_graphs(_counter):
    # Wii Sports color palette for lines
    colors = [WII_RED, WII_GREEN, WII_BLUE]

    # Accelerometer graph
    accel_data = [
        go.Scatter(
            x=list(time)[:len(accel_x)], y=list(d), name=name,
            mode='lines', line=dict(width=3, color=colors[i]), hoverinfo='skip'
        )
        for i, (d, name) in enumerate(zip([accel_x, accel_y, accel_z], ["X", "Y", "Z"]))
    ]

    accel_graph = {
        "data": accel_data,
        "layout": go.Layout(
            title={
                'text': "ACCELEROMETER (Calibrated)",
                'font': {'size': 24, 'family': 'Fredoka, Arial, sans-serif', 'color': WII_BLUE, 'weight': 700}
            },
            xaxis={"type": "date", "range": [min(time), max(time)] if len(time) > 0 else None},
            yaxis={"title": {"text": "m/s²", "font": {'size': 16, 'family': 'Fredoka'}}, "range": [-60, 60]},
            margin=dict(l=60, r=30, t=60, b=40),
            height=350,
            showlegend=True,
            uirevision='accel',
            paper_bgcolor=WII_GRAY,
            plot_bgcolor='white',
            font={'family': 'Fredoka, Arial, sans-serif', 'size': 14}
        ),
    }

    # Gyroscope graph
    gyro_data = [
        go.Scatter(
            x=list(time)[:len(gyro_x)], y=list(d), name=name,
            mode='lines', line=dict(width=3, color=colors[i]), hoverinfo='skip'
        )
        for i, (d, name) in enumerate(zip([gyro_x, gyro_y, gyro_z], ["X", "Y", "Z"]))
    ]

    gyro_graph = {
        "data": gyro_data,
        "layout": go.Layout(
            title={
                'text': "GYROSCOPE",
                'font': {'size': 24, 'family': 'Fredoka, Arial, sans-serif', 'color': WII_BLUE, 'weight': 700}
            },
            xaxis={"type": "date", "range": [min(time), max(time)] if len(time) > 0 else None},
            yaxis={"title": {"text": "rad/s", "font": {'size': 16, 'family': 'Fredoka'}}, "range": [-30, 30]},
            margin=dict(l=60, r=30, t=60, b=40),
            height=350,
            showlegend=True,
            uirevision='gyro',
            paper_bgcolor=WII_GRAY,
            plot_bgcolor='white',
            font={'family': 'Fredoka, Arial, sans-serif', 'size': 14}
        ),
    }

    # Uncalibrated Accelerometer graph
    accel_uncal_data = [
        go.Scatter(
            x=list(time)[:len(accel_uncal_x)], y=list(d), name=name,
            mode='lines', line=dict(width=3, color=colors[i]), hoverinfo='skip'
        )
        for i, (d, name) in enumerate(zip([accel_uncal_x, accel_uncal_y, accel_uncal_z], ["X", "Y", "Z"]))
    ]

    accel_uncal_graph = {
        "data": accel_uncal_data,
        "layout": go.Layout(
            title={
                'text': "ACCELEROMETER (Uncalibrated)",
                'font': {'size': 24, 'family': 'Fredoka, Arial, sans-serif', 'color': WII_BLUE, 'weight': 700}
            },
            xaxis={"type": "date", "range": [min(time), max(time)] if len(time) > 0 else None},
            yaxis={"title": {"text": "m/s²", "font": {'size': 16, 'family': 'Fredoka'}}, "range": [-60, 60]},
            margin=dict(l=60, r=30, t=60, b=40),
            height=350,
            showlegend=True,
            uirevision='accel_uncal',
            paper_bgcolor=WII_GRAY,
            plot_bgcolor='white',
            font={'family': 'Fredoka, Arial, sans-serif', 'size': 14}
        ),
    }

    # Rotation Rate graph (from wrist motion)
    rotation_rate_data = [
        go.Scatter(
            x=list(time)[:len(rotation_rate_x)], y=list(d), name=name,
            mode='lines', line=dict(width=3, color=colors[i]), hoverinfo='skip'
        )
        for i, (d, name) in enumerate(zip([rotation_rate_x, rotation_rate_y, rotation_rate_z], ["X", "Y", "Z"]))
    ]

    rotation_rate_graph = {
        "data": rotation_rate_data,
        "layout": go.Layout(
            title={
                'text': "WRIST GYROSCOPE",
                'font': {'size': 24, 'family': 'Fredoka, Arial, sans-serif', 'color': WII_BLUE, 'weight': 700}
            },
            xaxis={"type": "date", "range": [min(time), max(time)] if len(time) > 0 else None},
            yaxis={"title": {"text": "rad/s", "font": {'size': 16, 'family': 'Fredoka'}}, "range": [-5, 5]},
            margin=dict(l=60, r=30, t=60, b=40),
            height=350,
            showlegend=True,
            uirevision='rotation_rate',
            paper_bgcolor=WII_GRAY,
            plot_bgcolor='white',
            font={'family': 'Fredoka, Arial, sans-serif', 'size': 14}
        ),
    }

    return accel_graph, gyro_graph, accel_uncal_graph, rotation_rate_graph


@app.callback(
    Output("recording-status", "children"),
    Output("recordings-count", "children"),
    Input("start-btn", "n_clicks"),
    Input("stop-btn", "n_clicks"),
    prevent_initial_call=True
)
def handle_recording(start_clicks, stop_clicks):
    import backend

    ctx = dash.callback_context
    if not ctx.triggered:
        return "Ready", f"Recordings saved: {len(recordings)}/5"

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "start-btn":
        if not backend.recording:
            backend.recording = True
            backend.recording_start_time = datetime.now()
            backend.current_recording = {
                'start_time': backend.recording_start_time,
                'time': [],
                'accel_x': [], 'accel_y': [], 'accel_z': [],
                'gyro_x': [], 'gyro_y': [], 'gyro_z': [],
                'accel_uncal_x': [], 'accel_uncal_y': [], 'accel_uncal_z': [],
                'rotation_rate_x': [], 'rotation_rate_y': [], 'rotation_rate_z': []
            }
            print(f"[RECORDING] Started at {backend.recording_start_time}")
            return "🔴 RECORDING...", f"Recordings saved: {len(recordings)}/5"

    elif button_id == "stop-btn":
        print(f"[DEBUG] STOP button pressed. recording={backend.recording}, current_recording exists={backend.current_recording is not None}")
        if backend.recording:
            backend.recording = False
            if backend.current_recording and len(backend.current_recording['time']) > 0:
                print(f"[DEBUG] Recording has {len(backend.current_recording['time'])} samples")
                backend.current_recording['end_time'] = datetime.now()
                duration = (backend.current_recording['end_time'] - backend.current_recording['start_time']).total_seconds()
                backend.current_recording['duration'] = duration
                backend.current_recording['samples'] = len(backend.current_recording['time'])
                samples = backend.current_recording['samples']

                # Analyze recording to compute metrics
                try:
                    analyze_recording(backend.current_recording)
                except Exception as e:
                    print(f"[ERROR] Analysis failed: {e}")
                    import traceback
                    traceback.print_exc()
                    backend.current_recording['metrics'] = {}

                # Save recording to disk
                save_recording(backend.current_recording)

                recordings.append(backend.current_recording)
                print(f"[RECORDING] Stopped. Duration: {duration:.2f}s, Samples: {samples}, Total recordings: {len(recordings)}")
                backend.current_recording = None
                return f"✓ Recording saved ({duration:.1f}s, {samples} samples)", f"Recordings saved: {len(recordings)}/5"
            else:
                print("[RECORDING] Stopped but no data captured")
                backend.current_recording = None
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

        # Determine swing feedback color
        swing_feedback = metrics.get('swing_feedback', 'N/A')
        if swing_feedback == "NICE SWING!":
            feedback_color = '#00C851'  # Green
        elif swing_feedback == "HIPS FIRED LATE":
            feedback_color = '#ff4444'  # Red
        elif swing_feedback == "HIPS FIRED EARLY":
            feedback_color = '#ffbb33'  # Orange
        else:
            feedback_color = '#666'

        # Format metrics text with Wii Sports styling
        metrics_text = [
            html.H3(f"🏆 RECORDING #{rec_num}",
                   style={
                       'marginBottom': '5px',
                       'color': WII_BLUE,
                       'fontSize': '28px',
                       'fontWeight': '700'
                   }),
            html.Div(f"⏰ {rec['start_time'].strftime('%H:%M:%S')}",
                    style={
                        'fontSize': '18px',
                        'color': '#666',
                        'marginBottom': '10px',
                        'fontWeight': '600'
                    }),
            # Swing Feedback - Large and prominent
            html.Div(swing_feedback,
                    style={
                        'fontSize': '24px',
                        'color': 'white',
                        'backgroundColor': feedback_color,
                        'padding': '15px',
                        'borderRadius': '15px',
                        'textAlign': 'center',
                        'fontWeight': '700',
                        'marginBottom': '20px',
                        'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
                    }),
            html.Div([
                html.Div([
                    html.Span("Peak Hip Angular Velocity: ", style={'fontWeight': '700', 'color': WII_BLUE, 'fontSize': '16px'}),
                    html.Span(f"{metrics['peak_gyro_x_value']:.2f} rad/s ({metrics['gyro_direction']})",
                             style={'fontSize': '16px', 'color': '#333'}),
                ], style={'marginBottom': '10px'}),
                html.Div([
                    html.Span("Peak Accel (uncal): ", style={'fontWeight': '700', 'color': WII_BLUE, 'fontSize': '16px'}),
                    html.Span(f"{metrics['peak_accel_uncal_mag_value']:.2f} m/s²",
                             style={'fontSize': '16px', 'color': '#333'}),
                ], style={'marginBottom': '10px'}),
                html.Div([
                    html.Span("Time from 10% Contact to Peak: ", style={'fontWeight': '700', 'color': WII_BLUE, 'fontSize': '16px'}),
                    html.Span(f"{metrics.get('time_from_10pct_to_peak_gyro_ms', 0):.1f} ms",
                             style={'fontSize': '16px', 'color': '#333'}),
                ], style={'marginBottom': '10px'}),
                html.Div([
                    html.Span("Time from 100% Contact to Peak: ", style={'fontWeight': '700', 'color': WII_BLUE, 'fontSize': '16px'}),
                    html.Span(f"{metrics.get('time_from_100pct_to_peak_gyro_ms', 0):.1f} ms",
                             style={'fontSize': '16px', 'color': '#333'}),
                ], style={'marginBottom': '10px'}),
                html.Div([
                    html.Span("Peak Gyro to Peak Accel Offset: ", style={'fontWeight': '700', 'color': WII_BLUE, 'fontSize': '16px'}),
                    html.Span(f"{metrics['time_diff_ms']:.1f} ms",
                             style={'fontSize': '16px', 'color': '#333'}),
                ], style={'marginBottom': '10px'}),
            ], style={'padding': '15px', 'backgroundColor': WII_GRAY, 'borderRadius': '15px', 'marginBottom': '20px'})
        ]

        # Wii Sports colors for traces
        trace_colors = [WII_RED, WII_GREEN, WII_BLUE]

        # Create gyro graph
        gyro_traces = [
            go.Scatter(x=time_arr, y=rec['gyro_x'], name='X', mode='lines', line=dict(width=2, color=trace_colors[0])),
            go.Scatter(x=time_arr, y=rec['gyro_y'], name='Y', mode='lines', line=dict(width=2, color=trace_colors[1])),
            go.Scatter(x=time_arr, y=rec['gyro_z'], name='Z', mode='lines', line=dict(width=2, color=trace_colors[2]))
        ]

        # Build shapes and annotations for gyro plot
        gyro_shapes = [{
            'type': 'line',
            'x0': metrics['peak_gyro_x_time'],
            'x1': metrics['peak_gyro_x_time'],
            'y0': 0,
            'y1': 1,
            'yref': 'paper',
            'line': {'color': WII_ORANGE, 'width': 3, 'dash': 'dash'}
        }]
        gyro_annotations = [{
            'x': metrics['peak_gyro_x_time'],
            'y': 0.95,
            'yref': 'paper',
            'text': f"⭐ Peak",
            'showarrow': False,
            'bgcolor': WII_ORANGE,
            'font': {'color': 'white', 'size': 12, 'family': 'Fredoka', 'weight': 600},
            'borderpad': 6,
            'borderwidth': 0
        }]

        # Add foot contact time vertical lines if available
        if 'contact_10pct_time' in metrics:
            gyro_shapes.append({
                'type': 'line',
                'x0': metrics['contact_10pct_time'],
                'x1': metrics['contact_10pct_time'],
                'y0': 0,
                'y1': 1,
                'yref': 'paper',
                'line': {'color': '#00C851', 'width': 2, 'dash': 'dot'}
            })
            gyro_annotations.append({
                'x': metrics['contact_10pct_time'],
                'y': 0.85,
                'yref': 'paper',
                'text': "10%",
                'showarrow': False,
                'bgcolor': '#00C851',
                'font': {'color': 'white', 'size': 10, 'family': 'Fredoka', 'weight': 600},
                'borderpad': 4,
                'borderwidth': 0
            })

        if 'contact_100pct_bw_time' in metrics:
            gyro_shapes.append({
                'type': 'line',
                'x0': metrics['contact_100pct_bw_time'],
                'x1': metrics['contact_100pct_bw_time'],
                'y0': 0,
                'y1': 1,
                'yref': 'paper',
                'line': {'color': '#ffbb33', 'width': 2, 'dash': 'dot'}
            })
            gyro_annotations.append({
                'x': metrics['contact_100pct_bw_time'],
                'y': 0.75,
                'yref': 'paper',
                'text': "100%",
                'showarrow': False,
                'bgcolor': '#ffbb33',
                'font': {'color': 'white', 'size': 10, 'family': 'Fredoka', 'weight': 600},
                'borderpad': 4,
                'borderwidth': 0
            })

        gyro_fig = go.Figure(data=gyro_traces, layout=go.Layout(
            title={
                'text': "Hip Angular Velocity",
                'font': {'size': 18, 'family': 'Fredoka, Arial, sans-serif', 'color': WII_BLUE, 'weight': 600}
            },
            xaxis={"type": "date"},
            yaxis={"title": "rad/s"},
            height=280,
            margin=dict(l=50, r=20, t=50, b=30),
            paper_bgcolor=WII_GRAY,
            plot_bgcolor='white',
            font={'family': 'Fredoka, Arial, sans-serif', 'size': 12},
            shapes=gyro_shapes,
            annotations=gyro_annotations
        ))

        # Create accel graph
        accel_traces = [
            go.Scatter(x=time_arr, y=rec['accel_x'], name='X', mode='lines', line=dict(width=2, color=trace_colors[0])),
            go.Scatter(x=time_arr, y=rec['accel_y'], name='Y', mode='lines', line=dict(width=2, color=trace_colors[1])),
            go.Scatter(x=time_arr, y=rec['accel_z'], name='Z', mode='lines', line=dict(width=2, color=trace_colors[2]))
        ]

        accel_fig = go.Figure(data=accel_traces, layout=go.Layout(
            title={
                'text': "⚡ Accelerometer",
                'font': {'size': 18, 'family': 'Fredoka, Arial, sans-serif', 'color': WII_BLUE, 'weight': 600}
            },
            xaxis={"type": "date"},
            yaxis={"title": "m/s²"},
            height=280,
            margin=dict(l=50, r=20, t=50, b=30),
            paper_bgcolor=WII_GRAY,
            plot_bgcolor='white',
            font={'family': 'Fredoka, Arial, sans-serif', 'size': 12},
            shapes=[{
                'type': 'line',
                'x0': metrics['peak_accel_mag_time'],
                'x1': metrics['peak_accel_mag_time'],
                'y0': 0,
                'y1': 1,
                'yref': 'paper',
                'line': {'color': WII_ORANGE, 'width': 3, 'dash': 'dash'}
            }],
            annotations=[{
                'x': metrics['peak_accel_mag_time'],
                'y': 0.95,
                'yref': 'paper',
                'text': f"⭐ Peak",
                'showarrow': False,
                'bgcolor': WII_ORANGE,
                'font': {'color': 'white', 'size': 12, 'family': 'Fredoka', 'weight': 600},
                'borderpad': 6,
                'borderwidth': 0
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
            'padding': '30px',
            'backgroundColor': WII_WHITE,
            'borderRadius': '25px',
            'boxShadow': '0 8px 20px rgba(0,0,0,0.15)',
            'marginBottom': '25px',
            'border': f'4px solid {WII_LIGHT_BLUE}'
        })

        recording_divs.append(recording_div)
        print(f"[DEBUG] Recording #{rec_num} visualization created")

    print(f"[DEBUG] Returning {len(recording_divs)} recording visualizations")
    return recording_divs


@app.callback(
    Output("info-content", "style"),
    Output("info-toggle-text", "children"),
    Input("info-toggle-btn", "n_clicks"),
    prevent_initial_call=False
)
def toggle_info_section(n_clicks):
    """Toggle the visibility of the info section"""
    if n_clicks % 2 == 1:
        # Expanded state
        return (
            {'display': 'block', 'padding': '20px', 'backgroundColor': WII_GRAY, 'borderRadius': '15px'},
            " (Click to collapse)"
        )
    else:
        # Collapsed state
        return (
            {'display': 'none'},
            " (Click to expand)"
        )
