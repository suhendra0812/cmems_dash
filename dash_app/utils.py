from lxml import etree
from owslib.wms import WebMapService
import pandas as pd
from shapely.geometry import Point


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
