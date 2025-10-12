import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta

# --------------------------------------------
# Page Setup
# --------------------------------------------
st.set_page_config(page_title="🌊 OceanSense Live Dashboard", layout="wide")
st.title("🌊 OceanSense: Real-time Fish Migration & Productivity Dashboard")

st.markdown("""
This dashboard provides **real-time insights** into fish occurrences, sea surface temperature (SST), 
salinity (SSS), and chlorophyll concentration (Chl-a) using **OBIS** and **NOAA ERDDAP** data.
""")

# --------------------------------------------
# 1️⃣ User Inputs
# --------------------------------------------
species = st.text_input("Enter Species Name", value="Thunnus albacares")
start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
end_date = st.date_input("End Date", datetime.now())
lat_range = st.slider("Latitude Range", -90.0, 90.0, (10.0, 20.0))
lon_range = st.slider("Longitude Range", -180.0, 180.0, (70.0, 80.0))

# --------------------------------------------
# 2️⃣ Helper: Fetch OBIS Data
# --------------------------------------------
@st.cache_data(ttl=3600)
def fetch_obis_data(species):
    try:
        url = f"https://api.obis.org/v3/occurrence?scientificName={species}&size=500"
        data = requests.get(url).json()
        df = pd.json_normalize(data['results'])
        df = df[['scientificName', 'decimalLatitude', 'decimalLongitude', 'eventDate', 'depth']].dropna()
        df['eventDate'] = pd.to_datetime(df['eventDate'])
        return df
    except Exception as e:
        st.error(f"OBIS fetch error: {e}")
        return pd.DataFrame()

# --------------------------------------------
# 3️⃣ Helper: Fetch NOAA Data (SST, SSS, Chl-a)
# --------------------------------------------
@st.cache_data(ttl=3600)
def fetch_noaa_data(lat_range, lon_range, start_date, end_date):
    try:
        datasets = {
            "SST": "https://coastwatch.pfeg.noaa.gov/erddap/tabledap/erdAGsstamday.csv",
            "Chl_a": "https://coastwatch.pfeg.noaa.gov/erddap/tabledap/erdMH1chlamday.csv",
            "SSS": "https://coastwatch.pfeg.noaa.gov/erddap/tabledap/erdMWsstdmday.csv"
        }

        df_all = []
        for key, base_url in datasets.items():
            url = (
                f"{base_url}?time,latitude,longitude,{key.lower()}&"
                f"latitude>={lat_range[0]}&latitude<={lat_range[1]}&"
                f"longitude>={lon_range[0]}&longitude<={lon_range[1]}&"
                f"time>={start_date}T00:00:00Z&time<={end_date}T00:00:00Z"
            )
            df = pd.read_csv(url)
            df['time'] = pd.to_datetime(df['time'])
            df_all.append(df.rename(columns={key.lower(): key}))

        df_merged = df_all[0]
        for df_next in df_all[1:]:
            df_merged = pd.merge_asof(df_merged.sort_values('time'),
                                      df_next.sort_values('time'),
                                      on='time',
                                      direction='nearest')
        return df_merged

    except Exception as e:
        st.error(f"NOAA fetch error: {e}")
        return pd.DataFrame()

# --------------------------------------------
# 4️⃣ Fetch & Merge Live Data
# --------------------------------------------
if st.button("🚀 Fetch Live Data"):
    with st.spinner("Fetching OBIS and NOAA data..."):
        df_obis = fetch_obis_data(species)
        if df_obis.empty:
            st.warning("No OBIS data found for this species.")
            st.stop()

        df_noaa = fetch_noaa_data(lat_range, lon_range, start_date, end_date)
        if df_noaa.empty:
            st.warning("No NOAA data found for this region or period.")
            st.stop()

        df_obis = df_obis.sort_values('eventDate')
        df_noaa = df_noaa.sort_values('time')

        df_combined = pd.merge_asof(df_obis, df_noaa,
                                    left_on='eventDate',
                                    right_on='time',
                                    direction='nearest',
                                    tolerance=pd.Timedelta('1D')).dropna(subset=['SST'])
        
        st.success(f"✅ Data merged successfully — {len(df_combined)} records ready!")

        # --------------------------------------------
        # 5️⃣ Visualization: Map
        # --------------------------------------------
        st.subheader("📍 Fish Occurrences with Ocean Parameters")
        fig = px.scatter_mapbox(
            df_combined,
            lat="decimalLatitude",
            lon="decimalLongitude",
            color="SST",
            size="depth",
            hover_data=["scientificName", "Chl_a", "SSS"],
            color_continuous_scale="Viridis",
            mapbox_style="carto-positron",
            zoom=2,
            title=f"{species} — SST, Chl-a, and SSS Overlay"
        )
        st.plotly_chart(fig, use_container_width=True)

        # --------------------------------------------
        # 6️⃣ Visualization: Time Series
        # --------------------------------------------
        st.subheader("📈 Environmental Trends (SST, Chl-a, SSS)")
        trend_df = df_combined.groupby(df_combined['time'].dt.date)[['SST', 'Chl_a', 'SSS']].mean().reset_index()
        fig2 = px.line(trend_df, x='time', y=['SST', 'Chl_a', 'SSS'],
                       labels={'value': 'Measurement', 'time': 'Date'},
                       title="Temporal Variation of Key Ocean Parameters")
        st.plotly_chart(fig2, use_container_width=True)

        # --------------------------------------------
        # 7️⃣ Download & Model-Ready Export
        # --------------------------------------------
        csv = df_combined.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Processed Dataset", csv, "OceanSense_MergedData.csv", "text/csv")

        st.info("✅ Data ready for further analysis or model ingestion!")

# --------------------------------------------
# Footer
# --------------------------------------------
st.markdown("---")
st.caption("Developed by Abhidyu Ajila | Powered by OBIS + NOAA + Streamlit 🌍")
