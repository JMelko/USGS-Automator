# USGS Streamflow Automator v2: Regional Spatial ETL Pipeline

**Role:** Environmental Data Analyst  
**Focus:** American Southwest Watershed Compliance (San Pedro River)

## 📖 Project Objective
This project is an enterprise-grade overhaul of a baseline streamflow scraper. Version 2 transitions from flat-file storage to a fully spatial, idempotent ETL pipeline. It autonomously extracts regional hydrologic telemetry from the USGS REST API, engineers the data into geographic features, and securely loads it into a Dockerized PostGIS database. The pipeline features a live Python BI dashboard and a cloud-streaming raster pre-processor for downstream 2D hydraulic modeling.

## 🏗️ Technical Architecture
* **Extract:** Python (`requests`) queries the USGS API for multi-site, 15-minute telemetry.
* **Transform:** `GeoPandas` and `Shapely` enforce strict data typing and dynamically engineer EPSG:4326 geometric Point features from raw coordinates.
* **Load (Idempotent UPSERT):** `SQLAlchemy` and `GeoAlchemy2` establish a tunnel to a Dockerized PostGIS database. A raw SQL `UPSERT` safely appends new records while rejecting duplicates via database-level unique constraints.
* **Analyze (Database-Side SQL):** A persistent PostGIS `VIEW` utilizes SQL Window Functions to calculate a 7-day rolling average, automatically flagging dates where streamflow drops below the 2.0 CFS critical habitat minimum.

## 📊 Phase 2: Live BI Dashboard
* Built a native web application using `Streamlit`.
* Bypasses flat-file extraction by querying the PostGIS spatial view directly via `DirectQuery` methodology.
* Autonomously renders a live compliance map and real-time hydrograph charts split by stream gauge.

## 🌊 Phase 3: HEC-RAS Spatial Pre-Processor
* Engineered an automated terrain clipping script utilizing `rasterio` and HTTP Range Requests (Cloud-Optimized GeoTIFFs).
* Dynamically queries the local database for watershed gauge coordinates, projects an EPSG:32612 (UTM 12N) bounding box, and aligns CRS coordinates with the USGS National Map API.
* Memory-safely streams and clips regional Digital Elevation Models (DEMs) directly from the cloud into lightweight boundary condition files ready for HEC-RAS 2025.

## 🛠️ The Technology Stack
* **Language:** Python 3.11 (Pandas, GeoPandas, SQLAlchemy, Rasterio, Streamlit)
* **Database:** PostgreSQL 15 + PostGIS (Spatial Extensions)
* **Orchestration:** Docker & Docker Compose
* **Analytics Layer:** Advanced SQL (CTEs, Window Functions, GiST Indexing)

## 🚀 Execution Instructions
1. Spin up the spatial database infrastructure:
   ```bash
   docker-compose up -d
   ```
2. Activate the virtual environment and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Execute the daily ETL pipeline:
   ```bash
   python scripts/usgs_pipeline.py
   ```
4. Launch the live BI Compliance Dashboard:
   ```bash
   python -m streamlit run scripts/dashboard.py
   ```
5. Run the HEC-RAS Cloud Terrain Pre-processor:
   ```bash
   python scripts/hecras_preprocessor.py
   ```