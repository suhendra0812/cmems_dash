var timestamp_tooltip = document.querySelector('.rc-slider-tooltip-inner');
var data_ts = parseInt(timestamp_tooltip.innerHTML) * 3600000;
var delta_ts = new Date("1970-01-01") - new Date("1950-01-01");
var data_dt = new Date(data_ts - delta_ts);
timestamp_tooltip.innerHTML = data_dt.toISOString();