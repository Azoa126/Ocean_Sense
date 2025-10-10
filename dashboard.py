import asyncio
import json
import threading
import time
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import websockets

# WebSocket URL of your backend
WS_URL = "ws://127.0.0.1:8000/ws"

st.set_page_config(page_title="🐟 OceanSense-Fish Dashboard", layout="wide")

st.title("🐟 OceanSense-Fish — Real-Time Fisheries Migration Dashboard")
st.caption("Tracking simulated fish telemetry and productivity trends in real time.")

# -----------------------------
# Session state initialization
# -----------------------------
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["id", "lat", "lon", "speed", "heading", "timestamp"])
if "connected" not in st.session_state:
    st.session_state.connected = False
if "last_update" not in st.session_state:
    st.session_state.last_update = None
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["id", "lat", "lon", "speed", "heading", "timestamp"])
if "error" not in st.session_state:
    st.session_state.error = None

# -----------------------------
# WebSocket listener
# -----------------------------
async def listen_for_data():
    """Async WebSocket listener that updates session_state."""
    try:
        async with websockets.connect(WS_URL) as websocket:
            st.session_state.connected = True

            while True:
                try:
                    msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                    message = json.loads(msg)

                    if message["type"] == "snapshot" and message["positions"]:
                        st.session_state.data = pd.DataFrame(
                            [{"id": k, **v} for k, v in message["positions"].items()]
                        )

                    elif message["type"] == "telemetry_update":
                        new_entry = pd.DataFrame([{
                            "id": message["id"],
                            "timestamp": message["timestamp"],
                            "lat": message["lat"],
                            "lon": message["lon"],
                            "speed": message.get("speed"),
                            "heading": message.get("heading")
                        }])

                        # Update latest positions
                        df = pd.concat([st.session_state.data, new_entry]).drop_duplicates(subset="id", keep="last")
                        st.session_state.data = df
                        st.session_state.last_update = time.strftime("%H:%M:%S")

                        # Append to full history
                        st.session_state.history = pd.concat([st.session_state.history, new_entry])

                except asyncio.TimeoutError:
                    continue
                except websockets.ConnectionClosed:
                    st.session_state.connected = False
                    break

    except Exception as e:
        st.session_state.connected = False
        st.session_state.error = str(e)

# -----------------------------
# Start listener in background
# -----------------------------
def start_listener():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(listen_for_data())

if "listener_started" not in st.session_state:
    listener_thread = threading.Thread(target=start_listener, daemon=True)
    listener_thread.start()
    st.session_state.listener_started = True

# -----------------------------
# Dashboard layout
# -----------------------------
col1, col2 = st.columns([3, 1])

# Left column: Map with trails
with col1:
    if not st.session_state.data.empty:
        fig = go.Figure()

        # Add trails for each fish
        for fish_id, fish_data in st.session_state.history.groupby("id"):
            fig.add_trace(
                go.Scattermapbox(
                    lat=fish_data["lat"],
                    lon=fish_data["lon"],
                    mode="lines+markers",
                    marker=dict(size=7),
                    name=f"{fish_id} trail",
                    hoverinfo="text",
                    text=[
                        f"ID: {row.id}<br>Speed: {row.speed}<br>Heading: {row.heading}<br>Time: {row.timestamp}"
                        for row in fish_data.itertuples()
                    ]
                )
            )

        # Map layout
        fig.update_layout(
            mapbox_style="carto-positron",
            mapbox_zoom=4,
            mapbox_center={"lat": 18.6, "lon": 73.9},
            margin={"l":0,"r":0,"t":40,"b":0},
            height=600,
            title="Live Fish Telemetry Map with Trails"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Waiting for telemetry data...")

# Right column: Info, table, charts
with col2:
    if st.session_state.connected:
        st.success("✅ Connected to WebSocket")
    else:
        st.warning("⚠️ Connecting to backend...")

    if st.session_state.last_update:
        st.caption(f"🕒 Last update: {st.session_state.last_update}")

    if st.session_state.error:
        st.error(f"WebSocket error: {st.session_state.error}")

    st.dataframe(st.session_state.data.sort_values("timestamp", ascending=False), height=200)

    # Real-time speed chart
    if not st.session_state.history.empty:
        speed_fig = px.line(
            st.session_state.history,
            x="timestamp",
            y="speed",
            color="id",
            title="🐟 Fish Speed Over Time"
        )
        st.plotly_chart(speed_fig, use_container_width=True)

    # Real-time heading chart
    if not st.session_state.history.empty:
        heading_fig = px.histogram(
            st.session_state.history,
            x="heading",
            color="id",
            nbins=36,
            title="🧭 Fish Heading Distribution",
            opacity=0.7
        )
        st.plotly_chart(heading_fig, use_container_width=True)
