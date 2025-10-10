from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel
import numpy as np
import joblib
import asyncio
from typing import List
import random
import datetime

# Initialize FastAPI app
app = FastAPI(title="OceanSense-Fish Backend")

# -----------------------------
# 🔹 MACHINE LEARNING PREDICTION ENDPOINT
# -----------------------------

class PredictionInput(BaseModel):
    sst: list
    chl_anomaly: list
    sss: list

# Load your trained Random Forest model
rf = joblib.load("rf_baseline_model.pkl")

@app.post("/predict")
def predict(input_data: PredictionInput):
    """Predict productivity map based on SST, CHL anomaly, and SSS"""
    sst = np.array(input_data.sst)
    chl = np.array(input_data.chl_anomaly)
    sss = np.array(input_data.sss)

    X_input = np.stack([sst.flatten(), chl.flatten(), sss.flatten()], axis=1)
    y_pred = rf.predict(X_input)
    grid_pred = y_pred.reshape(sst.shape)

    return {"productivity_map": grid_pred.tolist()}


# -----------------------------
# 🔹 REAL-TIME TELEMETRY + WEBSOCKET SYSTEM
# -----------------------------

class ConnectionManager:
    """Manage WebSocket connections"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send a message to all active WebSocket clients"""
        living_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
                living_connections.append(connection)
            except Exception:
                # Ignore dead connections
                pass
        self.active_connections = living_connections


# Instantiate connection manager
manager = ConnectionManager()

# Model for incoming telemetry data
class Telemetry(BaseModel):
    id: str
    timestamp: str
    lat: float
    lon: float
    speed: float = None
    heading: float = None
    extra: dict = None


# In-memory store for latest positions (replace with DB for production)
latest_positions = {}


@app.post("/ingest")
async def ingest_telemetry(payload: Telemetry, background_tasks: BackgroundTasks):
    """Receive telemetry and broadcast to connected WebSocket clients"""
    latest_positions[payload.id] = {
        "timestamp": payload.timestamp,
        "lat": payload.lat,
        "lon": payload.lon,
        "speed": payload.speed,
        "heading": payload.heading,
        "extra": payload.extra,
    }

    message = {
        "type": "telemetry_update",
        "id": payload.id,
        "timestamp": payload.timestamp,
        "lat": payload.lat,
        "lon": payload.lon,
        "speed": payload.speed,
        "heading": payload.heading,
    }

    # Broadcast asynchronously
    background_tasks.add_task(manager.broadcast, message)
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections for live telemetry updates"""
    await manager.connect(websocket)
    try:
        # Send initial snapshot of current positions
        snapshot = {"type": "snapshot", "positions": latest_positions}
        await websocket.send_json(snapshot)

        # Listen for messages from client (optional)
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Server received: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# -----------------------------
# 🔹 SIMULATED TELEMETRY FOR DEMO
# -----------------------------

async def simulate_telemetry():
    """Simulate live telemetry for demo purposes"""
    fish_ids = ["fish1", "fish2", "fish3"]
    while True:
        for fish_id in fish_ids:
            payload = {
                "type": "telemetry_update",
                "id": fish_id,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "lat": 18.5 + random.random(),
                "lon": 73.8 + random.random(),
                "speed": round(random.uniform(1, 5), 2),
                "heading": random.randint(0, 360)
            }
            # Update in-memory positions
            latest_positions[payload["id"]] = {
                "timestamp": payload["timestamp"],
                "lat": payload["lat"],
                "lon": payload["lon"],
                "speed": payload["speed"],
                "heading": payload["heading"]
            }
            # Broadcast to connected WebSocket clients
            await manager.broadcast(payload)
        await asyncio.sleep(2)


@app.on_event("startup")
async def start_simulation():
    """Start telemetry simulation on app startup"""
    asyncio.create_task(simulate_telemetry())
