import base64
from io import BytesIO
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from pystac_client import Client
import matplotlib
matplotlib.use("Agg")  # Use non-GUI backend for Dash/Flask threads
import matplotlib.pyplot as plt
import dash
from dash import html, Output, Input, State
from dash_extensions.javascript import assign
import dash_leaflet as dl
from pyproj import Transformer

#
# Functions supporting the app
#

# --------- NDVI FETCH FUNCTION ---------
def fetch_ndvi(lat, lon, date="2025-07-01"):
    # 1. Search for Sentinel-2 L2A imagery over the point
    catalog = Client.open("https://earth-search.aws.element84.com/v1")
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        intersects={"type": "Point", "coordinates": [lon, lat]},
        datetime=f"{date}/2025-07-14",
        max_items=1,
        query={"eo:cloud_cover": {"lt": 99}}
    )

    items = list(search.items())
    if not items:
        raise ValueError("No Sentinel-2 imagery found for this date/location.")

    item = items[-1]
    red_href = item.assets["red"].href
    nir_href = item.assets["nir"].href

    # 2. Open bands directly from S3 without downloading whole file
    with rasterio.open(red_href) as red:
        # Transformer from WGS84 to raster's CRS
        transformer = Transformer.from_crs("EPSG:4326", red.crs, always_xy=True)
        minx, miny = transformer.transform(lon - 0.05, lat - 0.05)
        maxx, maxy = transformer.transform(lon + 0.05, lat + 0.05)
        window = from_bounds(minx, miny, maxx, maxy, red.transform)
        red_data = red.read(1, window=window).astype(np.float32)
    with rasterio.open(nir_href) as nir:
        nir_data = nir.read(1, window=window).astype(np.float32)

    # 3. Compute NDVI
    ndvi = (nir_data - red_data) / (nir_data + red_data)
    ndvi = np.clip(ndvi, -1, 1)

    return ndvi


# --------- HELPER: NDVI to Base64 Image ---------
def ndvi_to_base64(ndvi_array):
    fig, ax = plt.subplots(figsize=(4, 4))
    im = ax.imshow(ndvi_array, cmap="RdYlGn", vmin=-1, vmax=1)
    ax.axis("off")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="NDVI")
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode()

# -------------- THE APPLICATION ---------------
# To run the app locally, invoke: python app.py
# Then use a web browser to navigate to http://127.0.0.1:8050/

app = dash.Dash(__name__)

eventHandlers = dict(
    click=assign("function(e, ctx){console.log(`You clicked at ${e.latlng}.`);return [e.latlng.lat, e.latlng.lng];}"),
)

app.layout = html.Div([
    html.H1("CropWatch Location Picker"),
    dl.Map(center=[10.00, 110.00], zoom=4, children=[
        dl.TileLayer(),
        dl.LayerGroup(id="click-marker") 
    ], style={'width': '800px', 'height': '500px'}, id="map",
    eventHandlers=eventHandlers),
    html.Div(id="click-info", style={"marginTop": "10px"}),
    html.Div(id="ndvi-image", style={"marginTop": "10px"})
])


@app.callback(
    Output("click-info", "children"),
    Output("click-marker", "children"),
    Output("ndvi-image", "children"),
    Input("map", "n_clicks"),
    State("map", "clickData"),
    State("click-marker", "children"),
)
def map_click(n_clicks, click_data, current_children):
    # if coord is None:
    #     return "Click on the map to select a location.", [], None

    info = "Click on the map to select a location."
    marker = []
    img_component = html.Img(src="https://developers.elementor.com/docs/assets/img/elementor-placeholder-image.png", width=400)
    if not n_clicks is None:
        if n_clicks > 0:
            lat, lon = click_data['latlng']['lat'], click_data['latlng']['lng']
            # Longitude must be in [-180, 180].
            if lon < 0.0:
                lon += 360.0
            if lon > 180.0:
                lon -= 360.0

            info = f"Selected location: {lat:.4f}, {lon:.4f}"
            marker = dl.Marker(position=[lat, lon])
            current_children = [marker]

            ndvi_array = fetch_ndvi(lat, lon, date="2025-07-01")
            if ndvi_array is None:
                return info + " — No imagery found in time range.", [marker], None
            ndvi_base64 = ndvi_to_base64(ndvi_array)
            img_component = html.Img(src=ndvi_base64, style={"width": "400px", "border": "1px solid black"})

    return info, current_children, img_component


if __name__ == '__main__':
    app.run(debug=True)
