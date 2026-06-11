import requests
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine, text
import logging
import sys
import os

# 1. Setup Professional Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/pipeline.log'),
        logging.StreamHandler(sys.stdout)            
    ]
)

def run_pipeline():
    logging.info("--- Starting USGS Regional Spatial ETL Pipeline ---")
    
    # ---------------------------------------------------------
    # PHASE 1: EXTRACT
    # ---------------------------------------------------------
    # Palominas, Charleston, Redington gauges on the San Pedro
    site_codes = "09470500,09471000,09471550" 
    days_back = 2 
    url = f"https://waterservices.usgs.gov/nwis/iv/?format=json&sites={site_codes}&parameterCd=00060&period=P{days_back}D"
    
    logging.info(f"Pinging USGS API for Regional Sites: {site_codes}")
    response = requests.get(url)
    
    if response.status_code != 200:
        logging.error(f"API Connection Failed. Status Code: {response.status_code}")
        return
        
    raw_json = response.json()
    
    # ---------------------------------------------------------
    # PHASE 2: TRANSFORM & SPATIAL ENGINEERING
    # ---------------------------------------------------------
    logging.info("Transforming JSON payload and building spatial features...")
    data_rows = []
    
    try:
        # The API returns a list of time series (one for each gauge)
        for time_series in raw_json['value']['timeSeries']:
            site_code = time_series['sourceInfo']['siteCode'][0]['value']
            station_name = time_series['sourceInfo']['siteName']
            
            # Extract spatial coordinates
            lat = time_series['sourceInfo']['geoLocation']['geogLocation']['latitude']
            lon = time_series['sourceInfo']['geoLocation']['geogLocation']['longitude']
            
            # Iterate through the actual flow measurements
            measurements = time_series['values'][0]['value']
            for m in measurements:
                data_rows.append({
                    'site_code': site_code,
                    'station_name': station_name,
                    'timestamp': m['dateTime'],
                    'discharge_cfs': m['value'],
                    'latitude': lat,
                    'longitude': lon
                })
        
        # Build DataFrame and enforce types
        df = pd.DataFrame(data_rows)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['discharge_cfs'] = pd.to_numeric(df['discharge_cfs'], errors='coerce')
        
        # Convert to GeoDataFrame (Creating the geometric Point features)
        gdf = gpd.GeoDataFrame(
            df, 
            geometry=gpd.points_from_xy(df.longitude, df.latitude),
            crs="EPSG:4326"
        )
        
        # Drop the raw lat/lon columns as PostGIS only needs the geometry column
        gdf = gdf.drop(columns=['latitude', 'longitude'])

        # FIX: Rename the active geometry column to match our PostGIS schema
        gdf = gdf.rename_geometry('geom')
        
        logging.info(f"Successfully engineered {len(gdf)} spatial records.")
        
    except Exception as e:
        logging.error(f"Data transformation failed: {e}")
        return

    # ---------------------------------------------------------
    # PHASE 3: LOAD (The PostgreSQL Upsert)
    # ---------------------------------------------------------
    logging.info("Opening database tunnel and executing Upsert...")
    try:
        # In a full production environment, this URI would be loaded from your .env file
        db_uri = 'postgresql://env_analyst:tucson_water@localhost:5433/usgs_water_data'
        engine = create_engine(db_uri)
        
        with engine.begin() as conn:
            # 1. Load data into a temporary staging table
            gdf.to_postgis('temp_streamflow', conn, if_exists='replace', index=False)
            
            # 2. Execute the UPSERT (Insert, on conflict do nothing)
            upsert_query = text("""
                INSERT INTO usgs_streamflow (site_code, station_name, timestamp, discharge_cfs, geom)
                SELECT site_code, station_name, timestamp, discharge_cfs, geom 
                FROM temp_streamflow
                ON CONFLICT (site_code, timestamp) DO NOTHING;
            """)
            result = conn.execute(upsert_query)
            
            # 3. Drop the staging table
            conn.execute(text("DROP TABLE temp_streamflow;"))
            
        logging.info(f"Database sync complete. {result.rowcount} new records securely appended.")
        
    except Exception as e:
        logging.error(f"Database load failed: {e}")
        return

    logging.info("--- Pipeline Execution Complete ---")

if __name__ == "__main__":
    run_pipeline()