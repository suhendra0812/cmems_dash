from datetime import datetime, timedelta
import os

from dateutil.relativedelta import relativedelta
from dash import Dash, Input, Output, html, dcc
import dash_leaflet as dl
from owslib.wms import WebMapService
import numpy as np
import pandas as pd
from lxml import etree
from shapely.geometry import Point

app = Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,
)


param_df = pd.read_csv("data/sources.csv")

DEFAULT_ID = 0
DEFAULT_PARAM = param_df.loc[DEFAULT_ID, "parameter"]
DEFAULT_TEMPORAL = param_df.loc[DEFAULT_ID, "temporal"]
DEFAULT_WMS_URL = param_df.loc[DEFAULT_ID, "wms_nrt"]
DEFAULT_OPENDAP_URL = param_df.loc[DEFAULT_ID, "opendap_nrt"]
DEFAULT_VALUE_RANGE = list(map(int, param_df.loc[DEFAULT_ID, "value_range"].split(",")))

TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

TODAY = datetime.today()


def get_wms_info(wms_url, layer_name):
    wms = WebMapService(wms_url, version="1.3.0")
    item_data = {}
    for item in wms.items():
        key, value = item
        item_data[key] = value
    layer_info = item_data[layer_name]
    return layer_info


def get_feature_info(wms_url, layer_name, xy, time, depth=None):
    bbox = Point(xy).buffer(1e-07).bounds
    wms = WebMapService(wms_url, version="1.3.0")

    feature_info = wms.getfeatureinfo(
        layers=[layer_name],
        styles=["boxfill/rainbow"],
        srs="EPSG:4326",
        bbox=bbox,
        xy=(0, 0),
        size=(1, 1),
        info_format="text/xml",
        time=time,
        elevation=depth,
    )

    root = etree.fromstring(feature_info.read())
    value = float(root.find(".//value").text)
    longitude = float(root.find(".//longitude").text)
    latitude = float(root.find(".//latitude").text)

    info_dict = {"value": value, "longitude": longitude, "latitude": latitude}

    return info_dict


def generate_time_list(times):
    time_range = []
    for time in times:
        split_time = time.split("/")
        if len(split_time) == 1:
            dt = pd.to_datetime(split_time[0]).to_pydatetime()
            time_range.append(dt)
        else:
            start, end, freq = split_time
            freq = freq.replace("P", "").replace("T", "")
            date_range = pd.date_range(start, end, freq=freq).to_pydatetime()
            time_range.extend(date_range)

    return sorted(map(lambda x: x.replace(tzinfo=None), time_range))


param_box = html.Div(
    className="param_box",
    children=[
        html.H3("Parameter"),
        dcc.Dropdown(
            id="dd_param",
            options=[
                {"value": p, "label": a}
                for p, a in zip(param_df.parameter.unique(), param_df.title.unique())
            ],
            value=DEFAULT_PARAM,
        ),
    ],
)


temporal_box = html.Div(
    className="temporal_box",
    children=[
        html.H3("Temporal"),
        dcc.Dropdown(
            id="dd_temporal",
            options=[
                {"value": p, "label": p.capitalize()}
                for p in param_df.temporal.unique()
            ],
            value=DEFAULT_TEMPORAL,
        ),
    ],
)


value_box = html.Div(
    className="value_box",
    children=[
        html.H3("Value Range"),
        html.Div(
            style={
                "display": "flex",
                "flex-direction": "row",
                "justify-content": "space-between",
                "align-items": "center",
            },
            children=[
                html.H5("Min"),
                dcc.Input(
                    id="value_min",
                    type="number",
                    value=DEFAULT_VALUE_RANGE[0],
                    step=0.001,
                ),
                html.H5("Max"),
                dcc.Input(
                    id="value_max",
                    type="number",
                    value=DEFAULT_VALUE_RANGE[1],
                    step=0.001,
                ),
            ],
        ),
    ],
)


style_box = html.Div(
    className="style_box",
    children=[
        html.H3("Style"),
        dcc.Dropdown(
            id="dd_style",
            options=[
                {"value": "contour", "label": "Contour"},
            ],
            value="contour",
        ),
    ],
)


opacity_box = html.Div(
    className="opacity_box",
    children=[
        html.H3("Opacity"),
        dcc.Slider(
            id="opacity_slider",
            min=0,
            max=1,
            step=0.1,
            value=1,
            marks={0: "0", 0.5: "0.5", 1: "1"},
        ),
    ],
)


x_box = html.Div(
    className="x_box",
    children=[
        dcc.Input(
            id="xmin",
            type="number",
            value=0,
            step=0.001,
        ),
        dcc.Input(
            id="xmax",
            type="number",
            value=0,
            step=0.001,
        ),
    ],
)


ymax_box = html.Div(
    className="ymax_box",
    children=[
        dcc.Input(
            id="ymax",
            type="number",
            value=0,
            step=0.001,
        ),
    ],
)

ymin_box = html.Div(
    className="ymin_box",
    children=[
        dcc.Input(
            id="ymin",
            type="number",
            value=0,
            step=0.001,
        ),
    ],
)


bounding_box = html.Div(
    className="bounding_box",
    children=[ymax_box, x_box, ymin_box],
)


download_box = html.Div(
    className="download_box",
    children=[
        html.H3("Download"),
        html.Div(
            className="download_menu",
            children=[html.H5("Bounding Box"), bounding_box],
        ),
    ],
)


map_layout = dl.Map(
    id="map",
    center=[0, 116],
    zoom=5,
    style={"width": "100%", "height": "100%"},
    children=[
        dl.TileLayer(url=TILE_URL, attribution=TILE_ATTRIBUTION),
        dl.FeatureGroup(children=[dl.EditControl(id="edit_control")]),
        dl.MeasureControl(
            position="topleft",
            primaryLengthUnit="kilometers",
            primaryAreaUnit="hectares",
            activeColor="#214097",
            completedColor="#972158",
        ),
        dl.LayerGroup(
            id="wms_layers",
        ),
        dl.LayerGroup(
            id="vector_layers",
        ),
    ],
)


menu_layout = html.Div(
    className="menu_box",
    children=[param_box, temporal_box, value_box, style_box, opacity_box, download_box],
)


depth_layout = html.Div(
    className="depth_box",
    id="depth_box",
    children=[
        html.Div(
            style={"display": "flex", "flex-direction": "row"},
            children=[
                html.P("Depth: ", style={"font-weight": "bold", "margin-right": "5px"}),
                html.P(id="data_depth"),
            ],
        ),
        dcc.Slider(
            id="depth_slider",
            min=-5000,
            max=0,
            step=100,
            marks={v: f"{v * -1}" for v in range(-5000, 0, 1000)},
            value=0,
            vertical=True,
            verticalHeight=200,
            tooltip={"placement": "left"},
        ),
    ],
)


time_layout = html.Div(
    id="time_box",
    className="time_box",
)


@app.callback(
    [Output("dd_temporal", "options"), Output("dd_temporal", "value")],
    [Input("dd_param", "value")],
)
def update_temporal(param):
    temporal_list = param_df.query("parameter == @param").temporal.unique()
    temporal_options = [{"value": t, "label": t.capitalize()} for t in temporal_list]
    temporal_default = temporal_list[0]
    return temporal_options, temporal_default


@app.callback(
    Output("dd_style", "options"),
    [Input("dd_param", "value")],
)
def update_style_options(param):
    if param == "sea_water_velocity":
        return [
            {"value": "contour", "label": "Contour"},
            {"value": "vector", "label": "Vector"},
            {"value": "mixed", "label": "Contour and Vector"},
        ]
    return [
        {"value": "contour", "label": "Contour"},
    ]


@app.callback(
    [
        Output("wms_layers", "children"),
        Output("data_time", "children"),
        Output("data_depth", "children"),
    ],
    [
        Input("dd_param", "value"),
        Input("dd_temporal", "value"),
        Input("time_slider", "value"),
        Input("depth_slider", "value"),
        Input("value_min", "value"),
        Input("value_max", "value"),
        Input("opacity_slider", "value"),
        Input("dd_style", "value"),
    ],
)
def update_wms_layers(
    param,
    temporal,
    end_time,
    depth,
    value_min,
    value_max,
    opacity,
    style,
):
    end_date = datetime(1950, 1, 1) + timedelta(hours=end_time)

    value_range = f"{value_min},{value_max}"

    wms_url = param_df.query("parameter == @param and temporal == @temporal")[
        "wms_nrt"
    ].values[0]

    wms_info = get_wms_info(wms_url, param)
    time_values = wms_info.dimensions["time"]["values"]
    time_list = np.asanyarray(generate_time_list(time_values))
    time_idx = np.argmin(np.abs(time_list - end_date))

    data_time = time_list[time_idx].strftime("%Y-%m-%dT%H:%M:%S.0Z")

    if style == "vector":
        style_wms = "linevec/rainbow"
    elif style == "mixed":
        style_wms = "vector/rainbow"
    else:
        style_wms = "boxfill/rainbow"

    extraProps = {
        "colorscalerange": value_range,
        "time": data_time,
    }

    depth_text = None

    if not param in ["ZSD", "VHM0"]:
        elevation_values = wms_info.dimensions["elevation"]["values"]
        elevation_unit = wms_info.dimensions["elevation"]["units"]
        elevation_list = np.asanyarray(list(map(float, elevation_values)))
        elevation_idx = np.argmin(np.abs(elevation_list - depth))
        data_depth = elevation_list[elevation_idx]

        extraProps["elevation"] = data_depth
        depth_text = f"{round(data_depth, 1)} {elevation_unit}"

    wms_layer = dl.WMSTileLayer(
        id="wms_layer",
        url=wms_url,
        layers=param,
        opacity=opacity,
        transparent=True,
        version="1.3.0",
        format="image/png",
        styles=style_wms,
        extraProps=extraProps,
    )

    return ([wms_layer], f"{data_time}", depth_text)


@app.callback(
    [
        Output("value_min", "value"),
        Output("value_max", "value"),
        Output("time_box", "style"),
        Output("time_box", "children"),
        Output("depth_box", "style"),
    ],
    [Input("dd_param", "value"), Input("dd_temporal", "value")],
)
def update_values(param, temporal):
    wms_url = param_df.query("parameter == @param and temporal == @temporal")[
        "wms_nrt"
    ].values[0]

    wms_info = get_wms_info(wms_url, param)

    time_list = wms_info.dimensions["time"]["values"]
    time_range = np.asanyarray(generate_time_list(time_list))

    value_range = list(
        map(
            float,
            param_df.query("parameter == @param and temporal == @temporal")[
                "value_range"
            ]
            .values[0]
            .split(","),
        )
    )

    timestamp_range = np.asanyarray(
        list(
            map(
                lambda x: (x.date() - datetime(1950, 1, 1).date()).days * 24, time_range
            )
        )
    )
    today_idx = np.argmin(np.abs(time_range - TODAY))
    today_timestamp = timestamp_range[today_idx]

    start_time_mark = time_range[0] - relativedelta(months=3)
    end_time_mark = time_range[-1] + relativedelta(months=3)

    time_marks = {}
    start_year = time_range[0].year
    for v in pd.date_range(start_time_mark, end_time_mark, periods=12):
        time_stamp = (v.date() - datetime(1950, 1, 1).date()).days * 24
        if v.year == start_year:
            time_marks[time_stamp] = v.strftime("%B")
        else:
            time_marks[time_stamp] = v.strftime("%Y")
            start_year = v.year

    time_box = [
        html.Div(
            style={"display": "flex", "flex-direction": "row"},
            children=[
                html.P(
                    "Time: ",
                    style={"font-weight": "bold", "margin-right": "5px"},
                ),
                html.P(id="data_time"),
            ],
        ),
        dcc.Slider(
            id="time_slider",
            min=timestamp_range[0],
            max=timestamp_range[-1],
            step=24,
            value=today_timestamp,
            marks=time_marks,
            tooltip={"always_visible": False, "placement": "top"},
        ),
    ]

    depth_display = None
    if not param in ["ZSD", "VHM0"]:
        depth_display = "block"

    return (
        value_range[0],
        value_range[1],
        {"display": "block"},
        time_box,
        {"display": depth_display},
    )


@app.callback(
    Output("wms_layer", "opacity"),
    Input("opacity_slider", "value"),
)
def update_opacity(opacity):
    return opacity


@app.callback(
    [
        Output("xmin", "value"),
        Output("xmax", "value"),
        Output("ymin", "value"),
        Output("ymax", "value"),
    ],
    [Input("map", "bounds")],
)
def get_bounds(bounds):
    ((ymin, xmin), (ymax, xmax)) = bounds
    xmin = round(xmin, 3)
    xmax = round(xmax, 3)
    ymin = round(ymin, 3)
    ymax = round(ymax, 3)
    return (xmin, xmax, ymin, ymax)


app.layout = html.Div(
    style={"display": "grid", "width": "100%", "height": "100vh"},
    children=[map_layout, menu_layout, depth_layout, time_layout],
)

if __name__ == "__main__":
    app.run(debug=None)
