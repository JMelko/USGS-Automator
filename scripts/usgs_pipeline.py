import requests
import pandas as pd
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
    logging.info("--- Starting USGS Daily ETL Pipeline ---")
    
    # Extract
    site_code = "09471000"
    days_back = 2 
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

    # Load (The Flat File Data Lake)
    logging.info("Writing data to local CSV Data Lake...")
    try:
        output_dir = 'data/processed'
        os.makedirs(output_dir, exist_ok=True)
        file_path = f"{output_dir}/san_pedro_flow.csv"
        
        # Check if the file already exists so we don't duplicate column headers
        file_exists = os.path.isfile(file_path)
        
        # Append the new data
        df.to_csv(file_path, mode='a', index=False, header=not file_exists)
        
        # Read the whole file, drop any overlapping duplicate timestamps, and re-save
        full_df = pd.read_csv(file_path)
        full_df = full_df.drop_duplicates(subset=['timestamp'], keep='last')
        full_df.to_csv(file_path, index=False)
        
        logging.info(f"Data successfully appended to {file_path}. Total historical records: {len(full_df)}")
    except Exception as e:
        logging.error(f"CSV export failed: {e}")
        return

    logging.info("--- Pipeline Execution Complete ---")

if __name__ == "__main__":
    run_pipeline()