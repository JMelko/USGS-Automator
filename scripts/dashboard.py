import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# --- 1. Dashboard Configuration ---
st.set_page_config(page_title="USGS Compliance Tracker", layout="wide")
st.title("🌊 San Pedro Watershed Compliance")
st.markdown("Live spatial telemetry tracking for critical habitat flows, queried directly from PostGIS.")

# --- 2. Database Connection & Data Extraction ---
# Using the same SQL query from Power BI to project the geometries
@st.cache_data(ttl=3600) # Caches the data for 1 hour so we don't hammer the database
def load_data():
    engine = create_engine('postgresql://env_analyst:tucson_water@localhost:5433/usgs_water_data')
    query = """
        SELECT 
            station_name,
            record_date,
            rolling_7d_avg_cfs,
            is_below_minimum,
            ST_Y(geom) AS latitude,
            ST_X(geom) AS longitude
        FROM vw_san_pedro_compliance;
    """
    return pd.read_sql(query, engine)

df = load_data()

# --- 3. Rendering the Visuals ---
col1, col2 = st.columns([1, 2]) # Split the screen: 1/3 map, 2/3 chart

with col1:
    st.subheader("Gauge Network")
    # Streamlit natively maps any dataframe with 'latitude' and 'longitude' columns
    st.map(df) 

with col2:
    st.subheader("7-Day Rolling Average (CFS)")
    # Pivot the data so each river gauge gets its own line on the chart
    chart_data = df.pivot(index='record_date', columns='station_name', values='rolling_7d_avg_cfs')
    st.line_chart(chart_data)

st.caption("Data architecture: USGS REST API ➔ GeoPandas ➔ PostGIS ➔ Streamlit")