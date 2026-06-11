import geopandas as gpd
from sqlalchemy import create_engine
from shapely.geometry import box
import rasterio
from rasterio.mask import mask
import requests
import json
import os

# --- 1. Connect to PostGIS and Fetch Geometries ---
def fetch_gauge_bounds(buffer_meters=2500):
    print("Connecting to PostGIS to fetch active gauge geometries...")
    engine = create_engine('postgresql://env_analyst:tucson_water@localhost:5433/usgs_water_data')
    query = "SELECT station_name, geom FROM vw_san_pedro_compliance;"
    gdf = gpd.read_postgis(query, engine, geom_col='geom')
    
    print("Reprojecting geometries to EPSG:32612 (UTM 12N)...")
    gdf_metric = gdf.to_crs(epsg=32612)
    buffered_network = gdf_metric.buffer(buffer_meters)
    
    bounding_box = box(*buffered_network.total_bounds)
    bbox_gdf = gpd.GeoDataFrame({'geometry': [bounding_box]}, crs="EPSG:32612")
    return bbox_gdf

# --- 2. Query the USGS National Map API ---
def get_usgs_dem_url(bounds_gdf):
    print("\nQuerying USGS National Map API for regional terrain data...")
    # The API requires standard GPS coordinates (EPSG:4326), so we temporarily project back
    bounds_4326 = bounds_gdf.to_crs(epsg=4326)
    minx, miny, maxx, maxy = bounds_4326.total_bounds
    
    url = "https://tnmaccess.nationalmap.gov/api/v1/products"
    params = {
        "datasets": "National Elevation Dataset (NED) 1/3 arc-second",
        "bbox": f"{minx},{miny},{maxx},{maxy}",
        "prodFormats": "GeoTIFF"
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    # Extract the first matching high-resolution DEM download link
    download_url = data['items'][0]['downloadURL']
    print(f"Located active USGS endpoint: {download_url}")
    return download_url

# --- 3. The Core ETL: Cloud Streaming & Slicing ---
def clip_cloud_dem(remote_url, output_raster, crop_geometry):
    print("\nStreaming and clipping DEM directly from the cloud via Rasterio...")
    
    # The /vsicurl/ prefix tells Rasterio to stream the file via HTTP
    vsi_url = f"/vsicurl/{remote_url}"
    
    with rasterio.open(vsi_url) as src:
        # --- THE FIX: Dynamic CRS Alignment ---
        raster_crs = src.crs
        print(f"Aligning geometries: Reprojecting bounds to match USGS raster ({raster_crs})...")
        crop_geom_aligned = crop_geometry.to_crs(raster_crs)
        
        # Extract the polygon coordinates using the newly aligned geometry
        shapes = [feature["geometry"] for feature in json.loads(crop_geom_aligned.to_json())['features']]
        
        # Execute the windowed crop
        out_image, out_transform = mask(src, shapes, crop=True)
        out_meta = src.meta
        
    # Update the metadata for the newly clipped file
    out_meta.update({
        "driver": "GTiff",
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform
    })
    
    # Save the HEC-RAS ready output
    with rasterio.open(output_raster, "w", **out_meta) as dest:
        dest.write(out_image)
    print(f"✅ Success! Real topography boundary condition saved to: {output_raster}")
if __name__ == "__main__":
    print("🌊 Initiating HEC-RAS Spatial Pre-Processor...")
    os.makedirs("data/spatial", exist_ok=True)
    hecras_output_path = "data/spatial/san_pedro_hecras_real_input.tif"
    
    # 1. Calculate Bounding Box from Database
    project_bounds = fetch_gauge_bounds(buffer_meters=2500)
    
    # 2. Fetch the dynamic URL for the real terrain data
    usgs_url = get_usgs_dem_url(project_bounds)
    
    # 3. Stream and clip the real data directly to disk
    clip_cloud_dem(usgs_url, hecras_output_path, project_bounds)