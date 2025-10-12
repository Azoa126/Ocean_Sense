import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import asyncio
import websockets
import json
import threading
from datetime import datetime, timedelta

# ==========================================================
# 🌊 OCEANSENSE DASHBOARD
# ==========================================================
st.set_page_config(page_title="🌊 OceanSense Dashboard", layout="wide")
st.title("🌊 OceanSense: Real-time Fish Migration & Productivity Dashboard")

st.markdown("""
Monitor **fish occurrences**, **sea surface temperature (SST)**, **salinity (SSS)**, and **chlorophyll-a** 
using OBIS + NOAA data — or pull directly from your OceanSense backend.
""")

# ==========================================================
# 🔹 Backend Configuration
# ==========================================================
BACKEND_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws"

@st.cache_data(ttl=600)
def fetch_backend_data():
    """Fetch fish dataset from FastAPI backend safely."""
    try:
        response = requests.get(f"{BACKEND_URL}/fish-data")
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "message" in data:
            st.warning(data["message"])
            return pd.DataFrame()
        df = pd.DataFrame(data)
        # Clean numeric columns: replace NaN / inf with None
        df = df.replace({pd.NA: None, pd.NA: None, float('inf'): None, float('-inf'): None})
        return df
    except Exception as e:
        st.error(f"⚠️ Error connecting to backend: {e}")
        return pd.DataFrame()

# ==========================================================
# 🔹 Sidebar Controls
# ==========================================================
st.sidebar.header("Dashboard Options")
tab_choice = st.sidebar.radio("Select Mode", ["📊 Dataset View", "🛰️ Live Telemetry"])
use_backend = st.sidebar.toggle("Use Backend CSV Data", value=True)
species = st.sidebar.text_input("Species Name", value="Thunnus albacares")
start_date = st.sidebar.date_input("Start Date", datetime.now() - timedelta(days=7))
end_date = st.sidebar.date_input("End Date", datetime.now())
lat_range = st.sidebar.slider("Latitude Range", -90.0, 90.0, (10.0, 20.0))
lon_range = st.sidebar.slider("Longitude Range", -180.0, 180.0, (70.0, 80.0))

# ==========================================================
# 📊 Dataset View
# ==========================================================
if tab_choice == "📊 Dataset View":
    if use_backend:
        fish_data = fetch_backend_data()
        if not fish_data.empty:
            st.success(f"✅ Loaded {len(fish_data)} records from backend.")
        else:
            st.warning("No data received from backend.")
    else:
        st.info("Using live OBIS + NOAA API sources.")
        fish_data = pd.DataFrame()  # Placeholder

    if not fish_data.empty:
        st.subheader("📍 Fish Occurrence Map")
        if "decimalLatitude" in fish_data.columns and "decimalLongitude" in fish_data.columns:
            fig = px.scatter_mapbox(
                fish_data,
                lat="decimalLatitude",
                lon="decimalLongitude",
                color="SST" if "SST" in fish_data.columns else None,
                hover_data=fish_data.columns,
                mapbox_style="carto-positron",
                zoom=2
            )
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📈 Environmental Parameters")
        env_cols = [col for col in ["SST", "Chl_a", "SSS"] if col in fish_data.columns]
        if env_cols:
            trend_df = fish_data.groupby(fish_data.index // 10)[env_cols].mean().reset_index()
            fig2 = px.line(trend_df, y=env_cols, title="Average Trends (Binned)")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Environmental parameter columns not found.")

        # Download CSV
        csv = fish_data.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Dataset", csv, "OceanSense_FishData.csv", "text/csv")

# ==========================================================
# 🛰️ Live Telemetry View
# ==========================================================
if tab_choice == "🛰️ Live Telemetry":
    st.subheader("🛰️ Real-time Fish Movement Tracking")
    st.markdown("This view updates automatically using **WebSocket** data from your backend simulation.")

    map_placeholder = st.empty()
    status_placeholder = st.empty()
    positions = {}

    async def run_websocket():
        """WebSocket client to receive live telemetry."""
        try:
            async with websockets.connect(WS_URL) as ws:
                status_placeholder.success("✅ Connected to telemetry server")
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data.get("type") == "telemetry_update":
                        positions[data["id"]] = {
                            "lat": data["lat"],
                            "lon": data["lon"],
                            "speed": data.get("speed"),
                            "heading": data.get("heading"),
                            "timestamp": data.get("timestamp")
                        }
                    elif data.get("type") == "snapshot":
                        positions.update(data["positions"])

                    df = pd.DataFrame.from_dict(positions, orient="index").reset_index()
                    df.rename(columns={"index": "FishID"}, inplace=True)

                    if not df.empty:
                        fig = px.scatter_mapbox(
                            df,
                            lat="lat",
                            lon="lon",
                            color="FishID",
                            hover_data=["speed", "heading", "timestamp"],
                            zoom=3,
                            mapbox_style="carto-positron"
                        )
                        map_placeholder.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            status_placeholder.error(f"⚠️ WebSocket connection failed: {e}")

    # Run WebSocket in background thread
    def start_ws_loop():
        asyncio.new_event_loop().run_until_complete(run_websocket())

    threading.Thread(target=start_ws_loop, daemon=True).start()

# ==========================================================
# 🔹 Footer
# ==========================================================
st.markdown("---")
st.caption("Developed by Abhidyu Ajila | Powered by FastAPI + Streamlit 🌍")
