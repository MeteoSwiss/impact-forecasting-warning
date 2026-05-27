"""
Copyright (c) 2025 MeteoSwiss, contributors listed in AUTHORS

Distributed under the terms of the BSD 3-Clause License.

SPDX-License-Identifier: BSD-3-Clause

Generic hazard forecast creation from weather data.
"""

from datetime import datetime, timedelta
import xarray as xr

from climada.hazard.forecast import HazardForecast  # pylint: disable=import-error  # TODO: Fix climada.hazard.forecast import


def create_hazard_forecast(da_forecast: xr.DataArray,
                           hazard_type: str,
                           intensity_unit: str,
                           variable_name: str | None = None) -> tuple:
    """
    Convert weather forecast data to CLIMADA HazardForecast object.
    
    Works for any hazard type: wind, precipitation, temperature, etc.

    :param da_forecast: DataArray containing forecast data with dimensions (eps, lead_time, lat, lon).
    :type da_forecast: xr.DataArray
    :param hazard_type: CLIMADA hazard type code (e.g., "WS" for wind, "RF" for rainfall).
    :type hazard_type: str
    :param intensity_unit: Unit of intensity (e.g., "m/s", "mm", "°C").
    :type intensity_unit: str
    :param variable_name: Name of the variable in the dataset (defaults to da_forecast.name).
    :type variable_name: str
    :return: Tuple containing (HazardForecast object, reference_time, ref_time_str, 
             valid_time_strs, valid_time_prints, base_strs, base_strs_output_data).
    :rtype: tuple
    """
    if variable_name is None:
        variable_name = da_forecast.name

    # Extract reference time
    reference_time = str(da_forecast.ref_time.values[0])[:-13]
    ref_time_str = reference_time.replace('-', '').replace('T', '').replace(':', '')[:-2]

    # Calculate number of forecast days
    n_days = int(len(da_forecast.lead_time) / 24)

    # Calculate valid times
    valid_time_strs = [(datetime.fromisoformat(reference_time) + timedelta(days=i)).strftime("%Y%m%d")
                       for i in range(n_days)]
    valid_time_prints = [
        valid_time_str[:4] + "-" + valid_time_str[4:6] + "-" + valid_time_str[6:] for valid_time_str in valid_time_strs
    ]

    # Create output paths
    base_strs = [
        f"results/plots/{hazard_type}_C2E_run{ref_time_str}_event{valid_time_str}_Switzerland"
        for valid_time_str in valid_time_strs
    ]
    base_strs_output_data = [
        f"results/output_data/{hazard_type}_C2E_run{ref_time_str}_event{valid_time_str}"
        for valid_time_str in valid_time_strs
    ]

    # Group by days and take maximum per day
    da_forecast = da_forecast.groupby("lead_time.days").max(dim="lead_time").rename({"days": "forecast_day"})
    da_forecast = da_forecast.assign_coords(
        forecast_day=(da_forecast.forecast_day.values.astype("timedelta64[D]").astype("timedelta64[ns]")))

    # Create HazardForecast object from DataArray
    haz_fc = HazardForecast.from_xarray_raster(
        da_forecast.to_dataset(name=variable_name),
        hazard_type=hazard_type,
        intensity_unit=intensity_unit,
        coordinate_vars={
            "longitude": "lon",
            "latitude": "lat",
            "lead_time": "forecast_day",
            "member": "eps",
        },
        intensity=variable_name,
    )

    return haz_fc, reference_time, ref_time_str, valid_time_strs, valid_time_prints, base_strs, base_strs_output_data
