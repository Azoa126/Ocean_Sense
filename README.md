# Ocean_Sense
OceanSense-Fish is a real-time analytics platform that visualizes fish migration patterns and predicts ocean productivity using environmental parameters like Sea Surface Temperature (SST), Sea Surface Salinity (SSS), and Chlorophyll-a (CHL) anomalies.
# 🐟 OceanSense-Fish — Real-Time Fisheries Migration Dashboard

**OceanSense-Fish** is a real-time marine telemetry and fisheries migration dashboard built using **Streamlit** and **FastAPI**.  
It simulates and visualizes live fish movement and productivity trends through WebSocket-based data streaming and geospatial visualization.

---

## 🌊 Project Overview

This project demonstrates how real-time data pipelines can be used to monitor and visualize fisheries-related datasets in an interactive dashboard.  
It connects a backend simulation engine (via WebSockets) with a Streamlit-powered frontend dashboard that displays live updates on fish telemetry.

The broader goal of OceanSense is to integrate **open marine biodiversity datasets** (like OBIS and NOAA ERDDAP) to make fish migration and productivity insights more accessible for research and conservation.

---

## ⚙️ Features

- 📡 **Real-time data streaming** via WebSocket (FastAPI backend → Streamlit frontend)  
- 🗺️ **Interactive geospatial visualization** using Plotly Mapbox  
- 📊 **Live telemetry feed** for fish movement (ID, latitude, longitude, speed, heading, timestamp)  
- 📈 **Data table view** with auto-updating telemetry records  
- ✅ Connection status & last update indicators  
- 💾 Optional processed data download functionality (coming soon)  

---

## 🧩 Tech Stack

| Component | Technology |
|------------|-------------|
| Backend | FastAPI + WebSocket |
| Frontend | Streamlit + Plotly Express |
| Data | OBIS / NOAA ERDDAP (open ocean datasets) |
| Language | Python 3.10+ |

---

## 🚀 How to Run

1. Clone the repository  
   ```bash
   git clone https://github.com/<your-username>/oceansense-fish.git
   cd oceansense-fish
   ```

2. Create a virtual environment  
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies  
   ```bash
   pip install -r requirements.txt
   ```

4. Start the backend  
   ```bash
   cd backend
   python main.py
   ```

5. Run the dashboard  
   ```bash
   streamlit run dashboard.py
   ```

---

## 🧠 Future Scope

- Integrate **live OBIS/NOAA ERDDAP APIs** for real-time fishery and productivity data.  
- Add machine learning models to predict **migration routes and productivity hotspots**.  
- Create download/export options for processed or derived datasets.  
- Host on Streamlit Cloud or Render for public access.

---

## 📚 Data Attribution

This project uses publicly available data from:
- [OBIS - Ocean Biodiversity Information System](https://obis.org)  
- [NOAA ERDDAP - Environmental Research Division’s Data Access Program](https://coastwatch.pfeg.noaa.gov/erddap)

> Data and services are made freely available under their respective open data policies.  
> Users are encouraged to cite the original data sources when reusing information.

---

## 👨‍🔬 Author

**Abhidyu Ajila**  
📸 Wildlife Photographer & Marine Biology Student  
🐾 Passionate about marine ecosystems, sustainability, and conservation storytelling.  
🌐 Instagram: [@bearded_tarzaan](https://www.instagram.com/bearded_tarzaan)

---

### 🌍 License

This project is open-source under the **MIT License**.
