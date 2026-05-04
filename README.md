# USGS Streamflow Automator (CI/CD Pipeline)

**Author:** [Your Name]
**Role:** Environmental Data Analyst

## Project Objective
Eliminate the manual download, transformation, and storage of regulatory environmental data. This project implements a fully automated, serverless ETL (Extract, Transform, Load) pipeline that continuously monitors critical habitat streamflow via the live USGS REST API.

## Technical Architecture
* **Extract:** Python (`requests`) connects to the USGS NWIS JSON API to pull real-time hydro-telemetry data for the San Pedro River.
* **Transform:** `pandas` parses the nested JSON payload, enforces strict data typing, handles timestamp normalization, and removes duplicate overlapping records.
* **Load (Data Lake):** Transforms the data into a flat-file CSV architecture, building a continuously appending historical record.
* **Orchestration (CI/CD):** Deployed via **GitHub Actions**. A `.yml` workflow spins up an Ubuntu cloud runner daily at 2:00 AM MST, executes the Python pipeline, and programmatically commits the new data back to the repository.

## The Output
The continuously updating data lake and pipeline execution logs can be viewed here:
* [Daily Streamflow Data (CSV)](data/processed/san_pedro_flow.csv)
* [Execution Logs](data/pipeline.log)