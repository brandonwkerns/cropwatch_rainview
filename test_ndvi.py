from pystac_client import Client
import rasterio
from rasterio.windows import from_bounds
import numpy as np
import matplotlib.pyplot as plt
from pyproj import Transformer

def fetch_ndvi(lat, lon, date="2025-07-01"):
    # 1. Search for Sentinel-2 L2A imagery over the point
    catalog = Client.open("https://earth-search.aws.element84.com/v1")
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        intersects={"type": "Point", "coordinates": [lon, lat]},
        datetime=f"{date}/2025-07-14",
        max_items=1,
        query={"eo:cloud_cover": {"lt": 50}}
    )

    items = list(search.items())
    if not items:
        raise ValueError("No Sentinel-2 imagery found for this date/location.")

    item = items[-1]
    # help(item.assets["red"])
    red_href = item.assets["red"].href
    nir_href = item.assets["nir"].href

    # 2. Open bands directly from S3 without downloading whole file
    with rasterio.open(red_href) as red:
        # Transformer from WGS84 to raster's CRS
        transformer = Transformer.from_crs("EPSG:4326", red.crs, always_xy=True)
        minx, miny = transformer.transform(lon - 0.05, lat - 0.05)
        maxx, maxy = transformer.transform(lon + 0.05, lat + 0.05)
        window = from_bounds(minx, miny, maxx, maxy, red.transform)
        print(window)
        red_data = red.read(1, window=window).astype(np.float32)
    with rasterio.open(nir_href) as nir:
        nir_data = nir.read(1, window=window).astype(np.float32)

    # 3. Compute NDVI
    ndvi = (nir_data - red_data) / (nir_data + red_data)
    ndvi = np.clip(ndvi, -1, 1)

    return ndvi


if __name__ == "__main__":
    lat, lon = 0.5, 100.0  # Example Maritime Continent location
    ndvi = fetch_ndvi(lat, lon, date="2025-07-01")
    plt.imshow(ndvi, cmap="RdYlGn")
    plt.colorbar(label="NDVI")
    print("NDVI image saved as test_ndvi.png")
    plt.savefig('test_ndvi.png')
