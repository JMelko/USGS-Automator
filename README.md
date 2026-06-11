# USGS Streamflow Automator v2: Regional Spatial ETL Pipeline

**Role:** Environmental Data Analyst  
**Focus:** American Southwest Watershed Compliance (San Pedro River)

## 📖 Project Objective
This project is an enterprise-grade overhaul of a baseline streamflow scraper. Version 2 transitions from flat-file storage to a fully spatial, idempotent ETL pipeline. It autonomously extracts regional hydrologic telemetry from the USGS REST API, engineers the data into geographic features, and securely loads it into a Dockerized PostGIS database for real-time regulatory compliance dashboarding and downstream HEC-RAS modeling.

## 🏗️ Technical Architecture
* **Extract:** Python (`requests`) queries the USGS API for multi-site, 15-minute telemetry across the San Pedro watershed.
* **Transform:** `GeoPandas` and `Shapely` parse the nested JSON, enforce strict data typing, and dynamically engineer EPSG:4326 geometric Point features from raw API coordinates.
* **Load (Idempotent UPSERT):** `SQLAlchemy` and `GeoAlchemy2` establish a tunnel to a Dockerized PostGIS database. Data is loaded into an ephemeral staging table before a raw SQL `UPSERT` safely appends new records while rejecting duplicates via database-level unique constraints.
* **Analyze (Database-Side SQL):** A persistent PostGIS `VIEW` utilizes SQL Window Functions to aggregate daily mean flows and calculate a 7-day rolling average, automatically flagging dates where streamflow drops below the 2.0 CFS critical habitat minimum.

## 🛠️ The Technology Stack
* **Language:** Python 3.11 (Pandas, GeoPandas, SQLAlchemy, Requests)
* **Database:** PostgreSQL 15 + PostGIS (Spatial Extensions)
* **Orchestration:** Docker & Docker Compose
* **Analytics Layer:** Advanced SQL (CTEs, Window Functions, GiST Indexing)

## 🚀 Execution Instructions
1. Clone the repository and navigate to the project root.
2. Spin up the spatial database infrastructure:
   ```bash
   docker-compose up -d
   ```

   (Note: The ./sql/init.sql script will automatically execute on the first boot to generate the spatial schemas and constraints).
3. Activate the virtual environment and install dependencies:

    ```pip install -r requirements.txt ```

Execute the daily ETL pipeline:

   ```python scripts/usgs_pipeline.py ```


