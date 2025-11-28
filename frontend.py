import dash
from dash.dependencies import Output, Input, State
from dash import dcc, html
from datetime import datetime, timedelta
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import uuid
import threading
import numpy as np

import backend
import json

# Load density data
with open('computed_density_data.json', 'r') as f:
    density_data = json.load(f)

# Create Dash app
app = dash.Dash(
    __name__,
    server=backend.server,
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
        html.Div([
            html.H1("⚾ Swing Like Springer",
                   style={
                       'textAlign': 'left', 'color': WII_WHITE, 'fontSize': '64px',
                       'fontWeight': '700', 'margin': '20px 0', 'textShadow': '4px 4px 8px rgba(0,0,0,0.3)',
                       'letterSpacing': '2px'
                   }),
            html.H2("Powered by Sensor Logger @tszheichoi",
                   style={
                       'textAlign': 'left', 'color': WII_WHITE, 'fontSize': '32px',
                       'fontWeight': '400', 'marginLeft': '20px', 'marginTop': '0',
                       'marginBottom': '30px', 'textShadow': '2px 2px 4px rgba(0,0,0,0.2)'
                   }),
        ]),
        html.Div(
            style={
                'maxWidth': '1400px', 'margin': '0 auto', 'backgroundColor': WII_WHITE,
                'padding': '40px', 'boxShadow': '0 10px 40px rgba(0,0,0,0.3)'
            },
            children=[
                html.Div([
                    html.Button([
                        html.Span("ℹ️ ", style={'fontSize': '24px', 'marginRight': '10px'}),
                        html.Span("APP INFO & INSTRUCTIONS", style={'fontSize': '20px', 'fontWeight': '700'}),
                        html.Span(" (Click to expand)", id="info-toggle-text", style={'fontSize': '14px', 'marginLeft': '10px', 'fontWeight': '400', 'fontStyle': 'italic'})
                    ],
                    id="info-toggle-btn", n_clicks=0,
                    style={
                        'width': '100%', 'padding': '15px', 'backgroundColor': WII_BLUE, 'color': WII_WHITE,
                        'border': 'none', 'borderRadius': '15px', 'cursor': 'pointer', 'fontSize': '18px',
                        'fontWeight': '600', 'fontFamily': 'Fredoka, Arial, sans-serif', 'textAlign': 'left',
                        'boxShadow': '0 4px 10px rgba(0,0,0,0.2)', 'marginBottom': '15px', 'transition': 'all 0.3s'
                    }),
                    dcc.Markdown("""
                        ### 🎯 WHAT IS THIS APP?
                        This app turns your phone into a hitting coach by measuring your hip rotation and timing. Get real-time data on your swing mechanics.

                        ### 📊 WHAT WE MEASURE:
                        - **Heel Strike Time**: When your front foot plants.
                        - **Hip & Wrist Rotation Speed**: How fast your segments are turning.
                        - **Timing**: The kinetic sequence from foot plant to peak speeds.

                        ### 📲 HOW TO USE:
                        1. Download [Sensor Logger](https://tszheichoi.com/sensorlogger) and connect it to `poggywoggy.world:8883`.
                        2. Strap your phone to your waist/belt (screen facing forward).
                        3. Get in your batting stance and stay still.
                        4. Hit **START** → Take your swing → Hit **STOP**.
                        5. Check your analytics below!
                    """, id="info-content", style={'display': 'none', 'padding': '20px', 'backgroundColor': WII_GRAY, 'borderRadius': '15px'}),
                ], style={'marginBottom': '30px'}),
                html.Div([
                    html.H2("RECORDING CONTROLS",
                           style={
                               'color': WII_BLUE, 'fontSize': '36px', 'fontWeight': '700',
                               'marginBottom': '20px', 'textAlign': 'center'
                           }),
                    dcc.Input(id='recording-name', type='text', placeholder='Enter Swing Name...',
                              style={'width': 'calc(100% - 40px)', 'padding': '15px 20px', 'fontSize': '18px', 'marginBottom': '20px', 'borderRadius': '10px', 'border': '2px solid #ccc'}),
                    html.Div([
                        html.Button("START", id="start-btn", n_clicks=0,
                                   style={
                                       'padding': '25px 60px', 'fontSize': '32px', 'fontWeight': '700',
                                       'backgroundColor': WII_GREEN, 'color': WII_WHITE, 'border': 'none',
                                       'borderRadius': '20px', 'cursor': 'pointer', 'marginRight': '20px',
                                       'boxShadow': '0 8px 0 #28a745, 0 12px 20px rgba(0,0,0,0.3)',
                                       'transition': 'all 0.1s', 'fontFamily': 'Fredoka, Arial, sans-serif',
                                       'position': 'relative', 'top': '0'
                                   }),
                        html.Button("STOP", id="stop-btn", n_clicks=0,
                                   style={
                                       'padding': '25px 60px', 'fontSize': '32px', 'fontWeight': '700',
                                       'backgroundColor': WII_RED, 'color': WII_WHITE, 'border': 'none',
                                       'borderRadius': '20px', 'cursor': 'pointer',
                                       'boxShadow': '0 8px 0 #cc0033, 0 12px 20px rgba(0,0,0,0.3)',
                                       'transition': 'all 0.1s', 'fontFamily': 'Fredoka, Arial, sans-serif',
                                       'position': 'relative', 'top': '0'
                                   }),
                    ], style={'textAlign': 'center', 'marginBottom': '25px'}),
                    html.Div(id="recording-status", children="Ready",
                            style={
                                'marginTop': '20px', 'fontSize': '28px', 'fontWeight': '700',
                                'textAlign': 'center', 'color': WII_BLUE, 'padding': '15px',
                                'backgroundColor': WII_GRAY, 'borderRadius': '15px'
                            }),
                    html.Div(id="recordings-count",
                            children=f"Recordings saved: {len(backend.recordings)}/5",
                            style={
                                'marginTop': '10px', 'fontSize': '20px', 'textAlign': 'center',
                                'color': '#666', 'fontWeight': '600'
                            }),
                ], style={
                    'margin': '30px 0', 'padding': '20px', 'backgroundColor': WII_WHITE,
                    'borderRadius': '25px', 'border': f'5px solid {WII_BLUE}',
                    'boxShadow': '0 5px 20px rgba(0,153,255,0.2)'
                }),
                dcc.Store(id='job-id-store'),
                dcc.Store(id='level-display-store', data={}),
                html.Div(id="recordings-display", children=[], style={'margin': '30px 0'}),

                # Live Graphs Section
                html.Div([
                    html.H2("LIVE SENSOR DATA", style={'textAlign': 'center', 'color': WII_BLUE, 'fontWeight': '700', 'marginBottom': '20px'}),
                    html.Div([
                        dcc.Graph(id="accel_graph", style={'display': 'inline-block', 'width': '49%', 'verticalAlign': 'top'}),
                        dcc.Graph(id="gyro_graph", style={'display': 'inline-block', 'width': '49%', 'verticalAlign': 'top'})
                    ]),
                    html.Div([
                        dcc.Graph(id="accel_uncal_graph", style={'display': 'inline-block', 'width': '49%', 'verticalAlign': 'top'}),
                        dcc.Graph(id="rotation_rate_graph", style={'display': 'inline-block', 'width': '49%', 'verticalAlign': 'top'})
                    ]),
                ], style={'marginTop': '30px', 'padding': '20px', 'backgroundColor': WII_GRAY, 'borderRadius': '15px'}),
            ]
        ),
        dcc.Interval(id='counter', interval=backend.UPDATE_FREQ_MS),
        dcc.Interval(id='analysis-interval', interval=1000, disabled=True),
    ]
)

@app.callback(
    Output("accel_graph", "figure"),
    Output("gyro_graph", "figure"),
    Output("accel_uncal_graph", "figure"),
    Output("rotation_rate_graph", "figure"),
    Input("counter", "n_intervals")
)
def update_live_graphs(_counter):
    colors = [WII_RED, WII_GREEN, WII_BLUE]
    
    common_layout = {
        "xaxis": {"type": "date", "range": [min(backend.time), max(backend.time)] if len(backend.time) > 0 else None},
        "margin": dict(l=50, r=20, t=40, b=30),
        "height": 250,
        "showlegend": True,
        "paper_bgcolor": 'white',
        "plot_bgcolor": WII_GRAY,
        "font": {'family': 'Fredoka, Arial, sans-serif', 'size': 10}
    }
    
    def create_graph(data_deques, names, title_text, y_title, y_range, uirevision):
        data = [
            go.Scatter(
                x=list(backend.time)[-len(d):], y=list(d), name=name,
                mode='lines', line=dict(width=2, color=colors[i])
            ) for i, (d, name) in enumerate(zip(data_deques, names))
        ]
        layout = go.Layout(
            **common_layout,
            title={'text': title_text, 'font': {'size': 16, 'family': 'Fredoka, Arial, sans-serif', 'color': WII_BLUE}},
            yaxis={"title": {"text": y_title, "font": {'size': 12}}, "range": y_range},
            uirevision=uirevision
        )
        return {"data": data, "layout": layout}

    accel_fig = create_graph([backend.accel_x, backend.accel_y, backend.accel_z], ["X", "Y", "Z"], "Accelerometer", "m/s²", [-50, 50], 'accel')
    gyro_fig = create_graph([backend.gyro_x, backend.gyro_y, backend.gyro_z], ["X", "Y", "Z"], "Gyroscope", "rad/s", [-20, 20], 'gyro')
    accel_uncal_fig = create_graph([backend.accel_uncal_x, backend.accel_uncal_y, backend.accel_uncal_z], ["X", "Y", "Z"], "Uncalibrated Accel", "m/s²", [-50, 50], 'accel_uncal')
    rotation_rate_fig = create_graph([backend.rotation_rate_x, backend.rotation_rate_y, backend.rotation_rate_z], ["X", "Y", "Z"], "Wrist Rotation", "rad/s", [-5, 5], 'rotation_rate')

    return accel_fig, gyro_fig, accel_uncal_fig, rotation_rate_fig

@app.callback(
    Output("recording-status", "children"),
    Output("job-id-store", "data"),
    Output("analysis-interval", "disabled"),
    Input("start-btn", "n_clicks"),
    Input("stop-btn", "n_clicks"),
    State('recording-name', 'value'),
    prevent_initial_call=True
)
def handle_recording(start_clicks, stop_clicks, recording_name):
    ctx = dash.callback_context
    if not ctx.triggered:
        return "Ready", None, True

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    job_id = None
    analysis_disabled = True
    status_message = dash.no_update

    if button_id == "start-btn":
        if not backend.recording:
            backend.recording = True
            backend.recording_start_time = datetime.now()
            backend.current_recording = {
                'start_time': backend.recording_start_time, 'time': [],
                'accel_x': [], 'accel_y': [], 'accel_z': [], 'gyro_x': [], 'gyro_y': [], 'gyro_z': [],
                'accel_uncal_x': [], 'accel_uncal_y': [], 'accel_uncal_z': [],
                'rotation_rate_x': [], 'rotation_rate_y': [], 'rotation_rate_z': []
            }
            status_message = "🔴 RECORDING..."

    elif button_id == "stop-btn":
        if backend.recording:
            backend.recording = False
            if backend.current_recording and len(backend.current_recording['time']) > 0:
                rec = backend.current_recording
                rec['end_time'] = datetime.now()
                rec['duration'] = (rec['end_time'] - rec['start_time']).total_seconds()
                rec['samples'] = len(rec['time'])
                rec['name'] = recording_name
                
                job_id = str(uuid.uuid4())
                thread = threading.Thread(target=backend.analyze_recording_background, args=(job_id, rec.copy()))
                thread.start()
                
                backend.current_recording = None
                status_message = "⌛ Analyzing..."
                analysis_disabled = False
            else:
                backend.current_recording = None
                status_message = "⚠ Stopped (no data)"

    return status_message, job_id, analysis_disabled


@app.callback(
    Output("recordings-count", "children"),
    Output("analysis-interval", "disabled", allow_duplicate=True),
    Output("recording-status", "children", allow_duplicate=True),
    Input("analysis-interval", "n_intervals"),
    State("job-id-store", "data"),
    prevent_initial_call=True
)
def check_analysis_status(n_intervals, job_id):
    if not job_id or job_id not in backend.analysis_results:
        return dash.no_update, False, dash.no_update

    rec = backend.analysis_results.pop(job_id)
    backend.save_recording(rec)
    backend.recordings.append(rec)
    
    status = f"✓ Recording saved ({rec.get('duration', 0):.1f}s, {rec.get('samples', 0)} samples)"
    count = f"Recordings saved: {len(backend.recordings)}/5"
    
    return count, True, status

@app.callback(
    Output("recordings-display", "children"),
    [Input("recordings-count", "children"),
     Input("level-display-store", "data")]
)
def update_recordings_display(_, level_data_store):
    """
    Generate I-Graph visualization for all saved recordings.
    """
    if not backend.recordings:
        return []

    recording_divs = []
    for idx, rec in enumerate(reversed(list(backend.recordings))):
        rec_num = len(backend.recordings) - idx
        metrics = rec.get('metrics')
        if not metrics or not metrics.get('heel_strike_time'):
            continue

        # --- I-Graph ---
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        time_arr = rec.get('time', [])
        heel_strike_time = metrics['heel_strike_time']
        
        # Convert time_arr to relative time in ms
        relative_time_ms = [(t - heel_strike_time).total_seconds() * 1000 for t in time_arr]

        # --- Density Distributions ---
        current_level = level_data_store.get(str(rec_num), 'all')
        level_density_data = density_data.get(current_level, {})

        if level_density_data:
            # Pelvis Density
            pelvis_data = level_density_data.get('pelvis')
            if pelvis_data:
                fig.add_trace(go.Contour(
                    x=np.array(pelvis_data['time_grid']) * 1000, # ms
                    y=pelvis_data['vel_grid'], 
                    z=pelvis_data['density'],
                    colorscale=[[0, 'rgba(255,0,0,0)'], [1, 'rgba(255,0,0,0.4)']],
                    showscale=False, name='Pelvis Density',
                    contours_coloring='heatmap', opacity=0.6, hoverinfo='skip',
                    line=dict(color='red')
                ), secondary_y=False)

            # Wrist Density
            wrist_data = level_density_data.get('wrist')
            if wrist_data:
                fig.add_trace(go.Contour(
                    x=np.array(wrist_data['time_grid']) * 1000, # ms
                    y=wrist_data['vel_grid'], 
                    z=wrist_data['density'],
                    colorscale=[[0, 'rgba(0,255,0,0)'], [1, 'rgba(0,255,0,0.4)']],
                    showscale=False, name='Wrist Density',
                    contours_coloring='heatmap', opacity=0.6, hoverinfo='skip',
                    line=dict(color='green')
                ), secondary_y=False)

        # --- Other Traces ---
        if metrics.get('hip_angular_velocity_mag'):
            fig.add_trace(go.Scatter(x=relative_time_ms, y=np.rad2deg(metrics['hip_angular_velocity_mag']), name='Hip Speed', mode='lines', line=dict(color=WII_BLUE, width=3)), secondary_y=False)
        if metrics.get('wrist_angular_velocity_mag'):
             fig.add_trace(go.Scatter(x=relative_time_ms, y=np.rad2deg(metrics['wrist_angular_velocity_mag']), name='Wrist Speed', mode='lines', line=dict(color=WII_GREEN, width=2, dash='dash')), secondary_y=False)
        
        if metrics.get('peak_hip_speed_time'):
            peak_hip_time_rel = (metrics['peak_hip_speed_time'] - heel_strike_time).total_seconds() * 1000
            fig.add_trace(go.Scatter(x=[peak_hip_time_rel], y=[metrics['peak_hip_speed_deg_s']], name='Peak Hip Speed', mode='markers', marker=dict(symbol='star', color=WII_ORANGE, size=15, line=dict(color='white', width=2))), secondary_y=False)
        
        if metrics.get('peak_wrist_speed_time'):
            peak_wrist_time_rel = (metrics['peak_wrist_speed_time'] - heel_strike_time).total_seconds() * 1000
            fig.add_trace(go.Scatter(x=[peak_wrist_time_rel], y=[metrics['peak_wrist_speed_deg_s']], name='Peak Wrist Speed', mode='markers', marker=dict(symbol='diamond', color=WII_RED, size=12, line=dict(color='white', width=2))), secondary_y=False)
        
        fig.add_trace(go.Scatter(x=relative_time_ms, y=rec.get('accel_uncal_x', []), name='Foot Accel (X)', mode='lines', opacity=0.6, line=dict(color='#FF6B6B', width=2)), secondary_y=True)

        # --- Vertical Lines ---
        shapes, annotations = [], []
        def add_event_line_rel(ts_rel_ms, color, name, y_anchor=1.05):
            if ts_rel_ms is not None:
                shapes.append(dict(type='line', x0=ts_rel_ms, x1=ts_rel_ms, y0=0, y1=1, yref='paper', line=dict(color=color, width=2, dash='dot')))
                annotations.append(dict(x=ts_rel_ms, y=y_anchor, yref='paper', text=name, showarrow=False, bgcolor=color, font=dict(color='white')))

        add_event_line_rel(0, WII_GREEN, 'Heel Strike')
        if metrics.get('max_accel_x_time'):
            max_accel_x_time_rel = (metrics['max_accel_x_time'] - heel_strike_time).total_seconds() * 1000
            add_event_line_rel(max_accel_x_time_rel, WII_ORANGE, 'Max Foot X-Accel', 1.15)
        
        # --- Layout ---
        fig.update_layout(
            xaxis={"range": [-100, 300], "title": "Time Relative to Heel Strike (ms)", "dtick": 100},
            yaxis={"range": [0, 2500],"title": "Angular Velocity (deg/s)", "color": WII_BLUE, "side": 'left'},
            yaxis2={"title": "Foot Acceleration (m/s²)", "color": '#FF6B6B', "overlaying": 'y', "side": 'right'},
            height=600, margin=dict(l=60, r=60, t=40, b=50),
            paper_bgcolor='white', plot_bgcolor=WII_GRAY,
            font={'family': 'Fredoka, Arial, sans-serif', 'size': 12},
            shapes=shapes, annotations=annotations,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        # --- UI Components ---
        swing_name = rec.get('name') or f"Recording #{rec_num}"
        
        swing_feedback = metrics.get('swing_feedback', 'N/A')
        feedback_color = {'GOOD SEQUENCE': '#00C851', 'HIPS A BIT LATE': '#ff4444', 'HIPS A BIT EARLY': '#ffbb33'}.get(swing_feedback, '#666')

        def metric_item(label, value, unit, color=WII_BLUE):
            if value is None: return None
            formatted_value = f"{value:.1f}"
            return html.Div([
                html.Span(f"{label}: ", style={'fontWeight': '700', 'color': color, 'fontSize': '16px'}),
                html.Span(f"{formatted_value} {unit}", style={'fontSize': '16px', 'color': '#333'}),
            ], style={'display': 'inline-block', 'marginRight': '20px'})

        metrics_summary_div = html.Div([
            metric_item("Peak Hip Speed", metrics.get('peak_hip_speed_deg_s'), "deg/s"),
            metric_item("Time to Peak Hip", metrics.get('time_to_peak_hip_speed_ms'), "ms"),
            metric_item("Peak Wrist Speed", metrics.get('peak_wrist_speed_deg_s'), "deg/s"),
            metric_item("Time to Peak Wrist", metrics.get('time_to_peak_wrist_speed_ms'), "ms"),
        ], style={'textAlign': 'center', 'marginTop': '10px'})

        recording_divs.append(html.Div([
            html.H3(swing_name, style={'color': WII_BLUE, 'fontSize': '28px', 'fontWeight': '700', 'textAlign': 'center'}),
            html.Div(swing_feedback, style={'fontSize': '24px', 'color': 'white', 'backgroundColor': feedback_color, 'padding': '10px', 'borderRadius': '15px', 'textAlign': 'center', 'fontWeight': '700', 'marginBottom': '15px'}),
            dcc.Graph(figure=fig, config={'displayModeBar': False}),
            metrics_summary_div,
            html.Button(f"Compare: {current_level.upper()}", id={'type': 'level-button', 'rec_num': rec_num},
                        style={'marginTop': '15px', 'width': '100%', 'padding': '10px', 'backgroundColor': WII_BLUE, 'color': 'white', 'border': 'none', 'borderRadius': '10px'})
        ], style={
            'padding': '30px', 'backgroundColor': WII_WHITE, 'borderRadius': '25px', 
            'boxShadow': '0 8px 20px rgba(0,0,0,0.15)', 'marginBottom': '25px', 
            'border': f'4px solid {WII_LIGHT_BLUE}'
        }))

    return recording_divs

@app.callback(
    Output('level-display-store', 'data'),
    Input({'type': 'level-button', 'rec_num': dash.ALL}, 'n_clicks'),
    State('level-display-store', 'data'),
    prevent_initial_call=True
)
def cycle_level(n_clicks, current_data):
    if not any(n_clicks):
        raise dash.exceptions.PreventUpdate

    ctx = dash.callback_context
    button_id = ctx.triggered_id
    rec_num = str(button_id['rec_num'])

    levels = ['all', 'milb', 'college', 'high_school']
    
    current_level = current_data.get(rec_num, 'all')
    try:
        current_index = levels.index(current_level)
        next_index = (current_index + 1) % len(levels)
        next_level = levels[next_index]
    except ValueError:
        next_level = 'all'

    current_data[rec_num] = next_level
    return current_data

@app.callback(
    Output("info-content", "style"),
    Output("info-toggle-text", "children"),
    Input("info-toggle-btn", "n_clicks"),
)
def toggle_info_section(n_clicks):
    if n_clicks and n_clicks % 2 == 1:
        return {'display': 'block'}, " (Click to collapse)"
    return {'display': 'none'}, " (Click to expand)"
