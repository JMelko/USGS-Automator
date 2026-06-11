-- Enable Spatial Extensions
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create the Regional Streamflow Telemetry Table
CREATE TABLE IF NOT EXISTS usgs_streamflow (
    id SERIAL PRIMARY KEY,
    site_code VARCHAR(12) NOT NULL,
    station_name VARCHAR(100),
    timestamp TIMESTAMPTZ NOT NULL,
    discharge_cfs NUMERIC(10, 2),
    stage_ft NUMERIC(6, 2),
    geom GEOMETRY(Point, 4326),
    inserted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Enforce a composite unique constraint for reliable deduplication
    CONSTRAINT unique_site_time UNIQUE (site_code, timestamp)
);

-- Optimize Queries using Databases Indices
CREATE INDEX IF NOT EXISTS idx_streamflow_site_time 
ON usgs_streamflow (site_code, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_streamflow_geom 
ON usgs_streamflow USING gist(geom);