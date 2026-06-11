-- sql/compliance_view.sql

CREATE OR REPLACE VIEW vw_san_pedro_compliance AS
WITH daily_stats AS (
    -- Step 1: Condense 15-minute telemetry into Daily Mean Flow
    SELECT 
        site_code,
        station_name,
        DATE_TRUNC('day', timestamp) AS record_date,
        ROUND(AVG(discharge_cfs), 2) AS daily_mean_cfs,
        -- MAX(geom) safely passes the spatial point through the aggregate
        MAX(geom) AS geom
    FROM usgs_streamflow
    GROUP BY site_code, station_name, DATE_TRUNC('day', timestamp)
)
-- Step 2: Calculate 7-Day Rolling Average and Compliance Flags
SELECT 
    site_code,
    station_name,
    record_date,
    daily_mean_cfs,
    ROUND(AVG(daily_mean_cfs) OVER (
        PARTITION BY site_code 
        ORDER BY record_date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_7d_avg_cfs,
    CASE 
        WHEN daily_mean_cfs < 2.0 THEN TRUE 
        ELSE FALSE 
    END AS is_below_minimum,
    geom
FROM daily_stats;