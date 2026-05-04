import requests
import pandas as pd
from sqlalchemy import create_engine, text
import logging
import sys

# 1. Setup Professional Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/pipeline.log'), # Removed the ../
        logging.StreamHandler(sys.stdout)            
    ]
)

def run_pipeline():
    logging.info("--- Starting USGS Daily ETL Pipeline ---")
    
    # Extract
    site_code = "09471000"
    days_back = 2 # In production, we only need to grab the last 48 hours to catch up
    url = f"https://waterservices.usgs.gov/nwis/iv/?format=json&sites={site_code}&parameterCd=00060&period=P{days_back}D"
    
    logging.info(f"Pinging USGS API for Site: {site_code}")
    response = requests.get(url)
    
    if response.status_code != 200:
        logging.error(f"API Connection Failed. Status Code: {response.status_code}")
        return
        
    raw_json = response.json()
    
    # Transform
    logging.info("Transforming JSON payload...")
    try:
        time_series = raw_json['value']['timeSeries'][0]
        measurements = time_series['values'][0]['value']
        
        df = pd.DataFrame(measurements)
        df = df.rename(columns={'value': 'discharge_cfs', 'dateTime': 'timestamp'})
        df = df[['timestamp', 'discharge_cfs']]
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['discharge_cfs'] = pd.to_numeric(df['discharge_cfs'])
        logging.info(f"Successfully transformed {len(df)} records.")
    except Exception as e:
        logging.error(f"Data transformation failed: {e}")
        return

    # Load
    logging.info("Connecting to PostGIS Database...")
    try:
        # Connect to your isolated container
        db_uri = 'postgresql://env_analyst:tucson_water@localhost:5433/usgs_water_data'
        engine = create_engine(db_uri)
        
        # We use 'append' now, so the database grows over time
        table_name = 'usgs_san_pedro_flow'
        df.to_sql(table_name, engine, if_exists='append', index=False)
        
        # Let's drop duplicate timestamps in case our 48-hour pull overlaps with yesterday
        with engine.connect() as con:
            # Wrap the raw string in text()
            query = text("DELETE FROM usgs_san_pedro_flow WHERE ctid NOT IN (SELECT max(ctid) FROM usgs_san_pedro_flow GROUP BY timestamp);")
            con.execute(query)
            con.commit() # Explicitly save the deletion (SQLAlchemy 2.0 requirement)
            
        logging.info(f"Data successfully appended to {table_name}.")
    except Exception as e:
        logging.error(f"Database injection failed: {e}")
        return

    logging.info("--- Pipeline Execution Complete ---")

if __name__ == "__main__":
    run_pipeline()