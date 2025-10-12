import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel
import numpy as np
import joblib
import pandas as pd
from typing import List
import random
import datetime
import os

# ==========================================================
# 🌊 OCEANSENSE-FISH BACKEND
# ==========================================================
app = FastAPI(title="OceanSense-Fish Backend")

# ==========================================================
# 🔹 LOAD LOCAL CSV DATA
# ==========================================================
csv_path = os.path.join(os.path.dirname(__file__), "OBIS_Fisheries_Merged.csv")

if os.path.exists(csv_path):
    fish_data = pd.read_csv(csv_path)
    print(f"✅ Loaded CSV: {fish_data.shape[0]} rows × {fish_data.shape[1]} cols")
else:
    fish_data = pd.DataFrame()
    print(f"⚠️ CSV not found at {csv_path}")

# ==========================================================
# 🔹 LOAD RANDOM FOREST MODEL (Safe Load)
# ==========================================================
model_path = os.path.join(os.path.dirname(__file__), "rf_baseline_model.pkl")
rf = None
if os.path.exists(model_path):
    try:
        rf = joblib.load(model_path)
        print(f"✅ ML model loaded from {model_path}")
    except Exception as e:
        print(f"⚠️ Error loading model: {e}")
else:
    print(f"⚠️ No model found at {model_path}. ML predictions disabled.")

# ==========================================================
# 🔹 MACHINE LEARNING PREDICTION ENDPOINT
# ==========================================================
class PredictionInput(BaseModel):
    sst: list
    chl_anomaly: list
    sss: list

@app.post("/predict")
def predict(input_data: PredictionInput):
    if rf is None:
        return {"error": "Model not loaded. Please ensure rf_baseline_model.pkl is available."}

    sst = np.array(input_data.sst)
    chl = np.array(input_data.chl_anomaly)
    sss = np.array(input_data.sss)
    X_input = np.stack([sst.flatten(), chl.flatten(), sss.flatten()], axis=1)
    y_pred = rf.predict(X_input)
    grid_pred = y_pred.reshape(sst.shape)
    return {"productivity_map": grid_pred.tolist()}

# ==========================================================
# 🔹 CSV DATA ENDPOINT (JSON-SAFE)
# ==========================================================
@app.get("/fish-data")
def get_fish_data():
    """Serve CSV data safely to dashboard (NaN -> None)."""
    if fish_data.empty:
        return {"message": "No CSV data available."}

    # Replace NaN and inf values with None for JSON
    safe_df = fish_data.replace({np.nan: None, np.inf: None, -np.inf: None})
    return safe_df.to_dict(orient="records")

# ==========================================================
# 🔹 REAL-TIME TELEMETRY (WebSocket)
# ==========================================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        living_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
                living_connections.append(connection)
            except Exception:
                pass
        self.active_connections = living_connections

manager = ConnectionManager()
latest_positions = {}

class Telemetry(BaseModel):
    id: str
    timestamp: str
    lat: float
    lon: float
    speed: float = None
    heading: float = None
    extra: dict = None

@app.post("/ingest")
async def ingest_telemetry(payload: Telemetry, background_tasks: BackgroundTasks):
    """Receive telemetry data and broadcast to clients."""
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
    background_tasks.add_task(manager.broadcast, message)
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections."""
    await manager.connect(websocket)
    try:
        # Send snapshot of current positions
        snapshot = {"type": "snapshot", "positions": latest_positions}
        await websocket.send_json(snapshot)
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Server received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ==========================================================
# 🔹 SIMULATED TELEMETRY
# ==========================================================
async def simulate_telemetry():
    """Generate simulated fish movement data."""
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
            latest_positions[payload["id"]] = payload
            await manager.broadcast(payload)
        await asyncio.sleep(2)

@app.on_event("startup")
async def start_simulation():
    """Run telemetry simulation at startup."""
    asyncio.create_task(simulate_telemetry())

