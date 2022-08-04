from datetime import datetime

from lxml import etree
import numpy as np
from owslib.wms import WebMapService
from owslib.map.common import AbstractContentMetadata
import pandas as pd
from shapely.geometry import Point


def get_wms_info(wms_url: str, layer_name: str) -> AbstractContentMetadata:
    wms = WebMapService(wms_url, version="1.3.0")
    item_data = {}
    for item in wms.items():
        key, value = item
        item_data[key] = value
    layer_info = item_data[layer_name]
    return layer_info


def get_feature_info(
    wms_url: str, layer_name: str, xy: tuple, time: datetime, depth: float = None
) -> dict[str, float]:
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
        time=time.strftime("%Y-%m-%dT%H:%M:%S.0Z"),
        elevation=depth,
    )

    root = etree.fromstring(feature_info.read())
    value = float(root.find(".//value").text)
    longitude = float(root.find(".//longitude").text)
    latitude = float(root.find(".//latitude").text)

    info_dict = {"value": value, "longitude": longitude, "latitude": latitude}

    return info_dict


def generate_time_list(times: list[str]) -> list[datetime]:
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


def get_timestamp(time_range: datetime, init_date: datetime) -> np.ndarray:
    timestamp_range = np.asanyarray(
        list(
            map(
                lambda x: (x.date() - init_date.date()).days * 24, time_range
            )
        )
    )

    return timestamp_range
