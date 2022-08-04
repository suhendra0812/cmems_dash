# import python builtin modules
from datetime import datetime, timedelta

# import third party modules
from dateutil.relativedelta import relativedelta
from flask import Flask
import numpy as np
import pandas as pd

# import dash modules
from dash import Dash, Input, Output, State, html, dcc
from dash.exceptions import PreventUpdate
from dash_extensions.javascript import Namespace
import dash_auth
import dash_leaflet as dl
import requests

# import own modules
from utils import generate_time_list, get_wms_info, get_feature_info, get_timestamp

VALID_USERNAME_PASSWORD_PAIRS = {
    'bpisdkp': 'bpisdkp'
}

# initialize server
server = Flask(__name__)

# initialize dash app
app = Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,
    server=server
)

app.title = "BPISDKP Ocean Data Viewer"

auth = dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)

# read information from csv file
param_df = pd.read_csv("./assets/sources.csv")

# set initial state of information
DEFAULT_ID = 0
DEFAULT_PARAM = param_df.loc[DEFAULT_ID, "parameter"]
DEFAULT_TEMPORAL = param_df.loc[DEFAULT_ID, "temporal"]
DEFAULT_WMS_URL = param_df.loc[DEFAULT_ID, "wms_nrt"]
DEFAULT_OPENDAP_URL = param_df.loc[DEFAULT_ID, "opendap_nrt"]
DEFAULT_VALUE_RANGE = [
    float(param_df.loc[DEFAULT_ID, "value_min"]),
    float(param_df.loc[DEFAULT_ID, "value_max"])
]
TODAY = datetime.today()
TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

param_box = html.Div(
    className="menu-item",
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
    className="menu-item",
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
    className="menu-item",
    children=[
        html.Div(
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
    ],
)


style_box = html.Div(
    className="menu-item",
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
    className="menu-item",
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

date_box = html.Div(
    className="menu-item",
    children=[
        html.H3("Date Range"),
        dcc.DatePickerRange(
            id="date_range",
            start_date=(TODAY - relativedelta(months=1)).date().isoformat(),
            end_date=(TODAY + relativedelta(months=1)).date().isoformat(),
            display_format="DD MMMM YYYY",
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
    className="menu-item",
    children=[
        html.H3("Bounding Box"),
        html.Div(
            className="download_menu",
            children=[bounding_box],
        ),
    ],
)

test_box = html.Div(id="menu-item")

wpp_ns = Namespace("layerStyle", "wppLayerStyle")

map_layout = dl.Map(
    id="map",
    center=[0, 116],
    zoom=5,
    style={"width": "100%", "height": "100%"},
    children=[
        dl.TileLayer(url=TILE_URL, attribution=TILE_ATTRIBUTION),
        dl.GeoJSON(url="./assets/WPP_NRI.geojson", options=dict(style=wpp_ns("style"))),
        dl.FeatureGroup(id="feat_group", children=[dl.EditControl(id="edit_control")]),
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
    className="menu-container",
    children=[
        param_box,
        temporal_box,
        value_box,
        style_box,
        opacity_box,
        date_box,
        download_box,
        test_box,
    ],
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

legend_layout = html.Div(
    id="legend_box",
    className="legend_box"
)

app.layout = html.Div(
    style={"display": "grid", "width": "100%", "height": "100vh"},
    children=[
        map_layout,
        menu_layout,
        depth_layout,
        legend_layout,
        time_layout,
        dcc.Store(id="store_param"),
    ],
)


@app.callback(
    Output("store_param", "data"),
    Input("dd_param", "value"),
)
def get_param(param):
    selected_param_df = param_df.query("parameter == @param")
    return selected_param_df.to_json(date_format="iso", orient="split")


@app.callback(
    Output("dd_temporal", "options"),
    Output("dd_temporal", "value"),
    Input("store_param", "data"),
)
def update_temporal(data):
    selected_param_df = pd.read_json(data, orient="split")
    temporal_list = selected_param_df.temporal.unique()
    temporal_options = [{"value": t, "label": t.capitalize()} for t in temporal_list]
    temporal_default = temporal_list[0]
    return temporal_options, temporal_default


@app.callback(
    Output("dd_style", "options"),
    Input("dd_param", "value"),
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
    Output("wms_layers", "children"),
    Output("data_time", "children"),
    Output("data_depth", "children"),
    Input("store_param", "data"),
    Input("dd_temporal", "value"),
    Input("time_slider", "value"),
    Input("depth_slider", "value"),
    Input("value_min", "value"),
    Input("value_max", "value"),
    Input("opacity_slider", "value"),
    Input("dd_style", "value"),
)
def update_wms_layers(
    data,
    temporal,
    end_time,
    depth,
    value_min,
    value_max,
    opacity,
    style,
):
    value_range = f"{value_min},{value_max}"

    selected_param_df = pd.read_json(data, orient="split")
    temporal_param_df = selected_param_df.query("temporal == @temporal")

    param = temporal_param_df["parameter"].values[0]
    nrt_date = pd.to_datetime(temporal_param_df["nrt_date"].values[0]).to_pydatetime()
    init_date = pd.to_datetime(temporal_param_df["init_date"].values[0]).to_pydatetime()
    
    end_date = init_date + timedelta(hours=end_time)

    if end_date < nrt_date:
        wms_url = temporal_param_df["wms_my"].values[0]
    else:
        wms_url = temporal_param_df["wms_nrt"].values[0]

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
    Output("value_min", "value"),
    Output("value_max", "value"),
    Output("time_box", "style"),
    Output("time_box", "children"),
    Output("depth_box", "style"),
    Output("legend_box", "style"),
    Output("legend_box", "children"),
    Input("store_param", "data"),
    Input("dd_temporal", "value"),
    Input("date_range", "start_date"),
    Input("date_range", "end_date"),
)
def update_values(data, temporal, start_date, end_date):
    start_date = pd.to_datetime(start_date).to_pydatetime()
    end_date = pd.to_datetime(end_date).to_pydatetime()

    if end_date >= TODAY:
        current_date = TODAY
    else:
        current_date = end_date

    selected_param_df = pd.read_json(data, orient="split")
    temporal_param_df = selected_param_df.query("temporal == @temporal")

    param = temporal_param_df["parameter"].values[0]
    value_min = temporal_param_df["value_min"].values[0]
    value_max = temporal_param_df["value_max"].values[0]
    nrt_date = pd.to_datetime(temporal_param_df["nrt_date"].values[0]).to_pydatetime()
    init_date = pd.to_datetime(temporal_param_df["init_date"].values[0]).to_pydatetime()

    date_range = pd.date_range(start_date, end_date, freq="1D")
    datestamp_range = get_timestamp(date_range, init_date)

    wms_urls = []
    if end_date < nrt_date:
        wms_urls.append(
            temporal_param_df["wms_my"].values[0]
        )
    elif start_date >= nrt_date:
        wms_urls.append(
            temporal_param_df["wms_nrt"].values[0]
        )
    else:
        wms_urls.append(
            temporal_param_df["wms_my"].values[0]
        )
        wms_urls.append(
            temporal_param_df["wms_nrt"].values[0]
        )

    time_list = []
    for wms_url in wms_urls:
        wms_info = get_wms_info(wms_url, param)
        times = wms_info.dimensions["time"]["values"]
        time_list.extend(times)

    time_range = np.asanyarray(generate_time_list(time_list))

    value_range = [
        float(temporal_param_df["value_min"].values[0]),
        float(temporal_param_df["value_max"].values[0])
    ]

    timestamp_range = get_timestamp(time_range, init_date)
    today_idx = np.argmin(np.abs(time_range - current_date))
    today_timestamp = timestamp_range[today_idx]

    start_time_mark = start_date - relativedelta(months=1)
    end_time_mark = end_date + relativedelta(months=1)

    time_marks = {}
    start_year = time_range[0].year
    for v in pd.date_range(start_time_mark, end_time_mark, periods=12):
        time_stamp = (v.date() - init_date.date()).days * 24
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
            min=datestamp_range[0],
            max=datestamp_range[-1],
            step=24,
            value=today_timestamp,
            marks=time_marks,
            tooltip={"always_visible": False, "placement": "top"},
        ),
    ]

    depth_display = None
    legend_left = "10px"
    if not param in ["ZSD", "VHM0"]:
        depth_display = "block"
        legend_left = "calc(40px + 10vh)"

    legend_params = dict(
        request="GetLegendGraphic",
        layer=param,
        colorscalerange=f"{value_min},{value_max}"
    )

    legend_res = requests.get(wms_url, params=legend_params)

    legend_box = [
        html.Div(
            id="data_legend",
            children=[
                html.Img(
                    src=legend_res.url
                )
            ]
        )
    ]

    return (
        value_range[0],
        value_range[1],
        {"display": "block"},
        time_box,
        {"display": depth_display},
        {"display": "block", "left": legend_left},
        legend_box
    )


@app.callback(
    Output("wms_layer", "opacity"),
    Input("opacity_slider", "value"),
)
def update_opacity(opacity):
    return opacity


@app.callback(
    Output("xmin", "value"),
    Output("xmax", "value"),
    Output("ymin", "value"),
    Output("ymax", "value"),
    Input("map", "bounds"),
)
def get_bounds(bounds):
    if not bounds:
        raise PreventUpdate
        
    ((ymin, xmin), (ymax, xmax)) = bounds
    xmin = round(xmin, 3)
    xmax = round(xmax, 3)
    ymin = round(ymin, 3)
    ymax = round(ymax, 3)
    return (xmin, xmax, ymin, ymax)


@app.callback(
    Output("test_box", "children"),
    Input("edit_control", "geojson"),
    Input("store_param", "data"),
    Input("temporal", "value"),
    Input("time_slider", "value"),
    Input("depth_slider", "value"),
    State("feat_group", "children"),
)
def get_info(geojson, data, temporal, end_time, depth, feat_group):
    if not geojson:
        raise PreventUpdate

    selected_param_df = pd.read_json(data, orient="split")
    temporal_param_df = selected_param_df.query("temporal == @temporal")

    param = temporal_param_df["parameter"].values[0]
    nrt_date = pd.to_datetime(temporal_param_df["nrt_date"].values[0]).to_pydatetime()
    init_date = pd.to_datetime(temporal_param_df["init_date"].values[0]).to_pydatetime()
    
    end_date = init_date + timedelta(hours=end_time)

    if end_date < nrt_date:
        wms_url = temporal_param_df["wms_my"].values[0]
    else:
        wms_url = temporal_param_df["wms_nrt"].values[0]

    info_list = []
    for feat in geojson["features"]:
        geom = feat["geometry"]
        geom_type = geom["type"]
        if geom_type == "Point":
            x, y = geom["coordinates"]
            info = get_feature_info(
                wms_url=wms_url,
                layer_name=param,
                xy=(x, y),
                time=end_date,
                depth=depth
            )
            info_list.append(info)

    return info_list

if __name__ == "__main__":
    app.run()
