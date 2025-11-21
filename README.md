# Hitting Coach - Real-Time Sensor Data Pipeline

Real-time accelerometer and gyroscope data streaming from a mobile phone to a web dashboard via MQTT.

## Architecture

```
📱 Phone (Sensor Logger App)
    ↓ MQTT over TLS (WebSocket/TCP)
🔄 Mosquitto Broker (localhost:8883/8884)
    ↓ Subscribe to "sensor-logger" topic
🐍 Python Server (Flask + Dash)
    ├─ MQTT Consumer (processes sensor data in real-time)
    ├─ HTTP POST endpoint (fallback)
    └─ Dash Dashboard (visualizes data)
        ↓ Nginx reverse proxy
🌐 https://poggywoggy.world/sensor/
```

## Performance Characteristics

- **End-to-end latency:** ~18-49ms (typically ~25ms)
  - Phone sensor sampling: 5-10ms
  - MQTT encode + TLS encrypt: 2-5ms
  - Network transmission: 10-30ms
  - TLS decrypt + MQTT decode: 1-3ms
  - Python processing: <1ms
- **Dashboard update frequency:** 500ms (optimized for browser performance)
- **Data buffer:** Last 200 data points (~10-40 seconds depending on sensor rate)

## Setup

### Prerequisites

- Python 3.12+
- uv (package manager)
- Mosquitto MQTT broker
- Nginx with SSL/TLS certificates
- Domain with DNS configured

### Installation

1. **Install Python dependencies:**
   ```bash
   uv sync
   ```

2. **Configure MQTT broker** (see Server Configuration below)

3. **Configure Nginx reverse proxy** (see Server Configuration below)

4. **Start the server:**
   ```bash
   uv run python sensor_server.py
   ```

## Server Configuration

### Mosquitto MQTT Broker

**Installation:**
```bash
apt install mosquitto mosquitto-clients
```

**Configuration file:** `/etc/mosquitto/conf.d/sensor-logger.conf`
```conf
# Disable anonymous access
allow_anonymous false
password_file /etc/mosquitto/passwd

# WebSocket listener with TLS
listener 8884
protocol websockets
certfile /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem
cafile /etc/letsencrypt/live/YOUR_DOMAIN/chain.pem
keyfile /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem
require_certificate false

# TCP listener with TLS
listener 8883
protocol mqtt
certfile /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem
cafile /etc/letsencrypt/live/YOUR_DOMAIN/chain.pem
keyfile /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem
require_certificate false
```

**Create MQTT credentials:**
```bash
mosquitto_passwd -c /etc/mosquitto/passwd sensor
chown mosquitto:mosquitto /etc/mosquitto/passwd
chmod 600 /etc/mosquitto/passwd
```

**Enable and start Mosquitto:**
```bash
systemctl enable mosquitto
systemctl start mosquitto
```

**Firewall rules:**
```bash
ufw allow 8883/tcp  # MQTT over TCP with TLS
ufw allow 8884/tcp  # MQTT over WebSocket with TLS
```

### Nginx Reverse Proxy

**Add to your site configuration** (e.g., `/etc/nginx/sites-available/YOUR_DOMAIN`):

```nginx
# Sensor data endpoint - proxy to Flask app
location /data {
    proxy_pass http://127.0.0.1:8000/data;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# Sensor dashboard - proxy to Dash app
location /sensor {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_buffering off;
}
```

**Reload Nginx:**
```bash
nginx -t && systemctl reload nginx
```

### SSL/TLS Certificates

This setup uses Let's Encrypt certificates managed by Certbot. The certificates are referenced by Mosquitto and Nginx but are **not included in this repository**.

**To obtain certificates:**
```bash
certbot certonly --nginx -d YOUR_DOMAIN
```

### Environment Variables

Create a `.env` file (not committed to git):
```bash
MQTT_BROKER=your-domain.com
MQTT_PORT=8883
MQTT_TOPIC=sensor-logger
MQTT_USERNAME=sensor
MQTT_PASSWORD=your-secure-password
```

## Mobile App Configuration (Sensor Logger)

### MQTT Settings (Recommended)
- **App:** [Sensor Logger](https://tszheichoi.com/sensorlogger)
- **Broker:** `your-domain.com`
- **Port:** `8884` (WebSocket) or `8883` (TCP)
- **Protocol:** WebSocket or TCP
- **Use TLS:** ✅ Required
- **Username:** `sensor`
- **Password:** (your configured password)
- **Topic:** `sensor-logger`

### HTTP POST Alternative
- **URL:** `https://your-domain.com/data`

## Endpoints

- **Dashboard:** `https://your-domain.com/sensor/`
- **HTTP POST:** `https://your-domain.com/data`
- **MQTT WebSocket:** `wss://your-domain.com:8884`
- **MQTT TCP:** `mqtts://your-domain.com:8883`

## Data Format

The server processes accelerometer and gyroscope data from Sensor Logger:

```json
{
  "messageId": 123,
  "sessionId": "unique-session-id",
  "deviceId": "device-identifier",
  "payload": [
    {
      "name": "accelerometer",
      "time": 1731809600000000000,
      "values": {"x": 1.5, "y": 2.3, "z": 9.8}
    },
    {
      "name": "gyroscope",
      "time": 1731809600000000000,
      "values": {"x": 0.5, "y": -0.3, "z": 1.2}
    }
  ]
}
```

## Dashboard Features

- **Two real-time graphs:**
  - Accelerometer: ±60 m/s²
  - Gyroscope: ±30 rad/s
- **Updates:** Every 500ms
- **Buffer:** Last 200 data points
- **Optimizations:**
  - Lines only (no markers)
  - Hover disabled
  - Thin lines for faster rendering
  - UI revision keys to preserve zoom

## Repository Structure

```
hitting_coach/
├── sensor_server.py      # Main server application
├── pyproject.toml        # Python dependencies
├── uv.lock              # Locked dependencies
├── README.md            # This file
├── .gitignore           # Excluded files
└── .venv/               # Virtual environment (not committed)
```

## What's NOT in the Repository

For security and portability:
- ❌ TLS certificates (server-specific, managed by Certbot)
- ❌ MQTT passwords (use environment variables)
- ❌ Virtual environment (.venv)
- ❌ Server-specific nginx configuration
- ❌ Mosquitto password file

## Deployment Notes

This setup is designed for a VPS with:
- A domain name with DNS configured
- SSL/TLS certificates from Let's Encrypt
- Nginx as reverse proxy
- Mosquitto MQTT broker

**To deploy on a new server:**
1. Install dependencies (Python, Mosquitto, Nginx, Certbot)
2. Obtain SSL certificates
3. Configure Mosquitto with your certificates
4. Configure Nginx reverse proxy
5. Set up MQTT credentials
6. Configure environment variables
7. Run the Python server

## Development

**Run locally:**
```bash
source .venv/bin/activate
python sensor_server.py
```

**Or with uv:**
```bash
uv run python sensor_server.py
```

## Monitoring

**Check Mosquitto logs:**
```bash
tail -f /var/log/mosquitto/mosquitto.log
```

**Check server status:**
```bash
ps aux | grep sensor_server
```

**Monitor MQTT connections:**
```bash
tail -f /var/log/mosquitto/mosquitto.log | grep -E "client|connect"
```

## Troubleshooting

**No data appearing:**
- Check MQTT broker is running: `systemctl status mosquitto`
- Check firewall allows ports 8883/8884
- Verify credentials in Sensor Logger app
- Check server logs for "received data" messages

**Dashboard not loading:**
- Verify Nginx is running: `systemctl status nginx`
- Check reverse proxy configuration
- Ensure server is running on port 8000

**High CPU usage:**
- Dashboard update frequency is optimized at 500ms
- Data buffer limited to 200 points
- Browser tab throttling may affect performance

## Credits

- Sensor data streaming: [Sensor Logger](https://tszheichoi.com/sensorlogger)
- Visualization: [Plotly Dash](https://dash.plotly.com/)
- MQTT broker: [Eclipse Mosquitto](https://mosquitto.org/)

## License

MIT (or your preferred license)
