import dash
from dash import html, Output, Input, State
from dash_extensions.javascript import assign
import dash_leaflet as dl

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
    ], style={'width': '800px', 'height': '500px'}, id="map",
    eventHandlers=eventHandlers),
    html.Div(id="click-info")
])

@app.callback(
    Output("click-info", "children"),
    Input("map", "n_clicks"),
    State("map", "clickData"),
)
def onclick(n_clicks, click_data):
    if not n_clicks is None:
        if n_clicks > 0:
            print(f"Detected click at: {click_data['latlng']}")
            lat, lon = click_data['latlng']['lat'], click_data['latlng']['lng']
            return f"Clicked at: Lat {lat:.4f}, Lng {lon:.4f}"
    return "Click on the map to get coordinates."


@app.callback(
    Output("map", "children"),
    Input("map", "n_clicks"),
    State("map", "clickData"),
    State("map", "children"),
)
def add_marker(n_clicks, click_data, current_children):
    if not n_clicks is None:
        if n_clicks > 0:
            lat, lon = click_data['latlng']['lat'], click_data['latlng']['lng']
            marker = dl.Marker(position=[lat, lon])
            current_children.append(marker)
    return current_children


if __name__ == '__main__':
    app.run(debug=True)
