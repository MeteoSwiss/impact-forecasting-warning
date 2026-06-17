"""
Copyright (c) 2025 MeteoSwiss, contributors listed in AUTHORS

Distributed under the terms of the BSD 3-Clause License.

SPDX-License-Identifier: BSD-3-Clause

Wind impact forecast pipeline: Orchestration and CLI entry point.
"""

import argparse
from pathlib import Path

import numpy as np

from climada.engine import ImpactCalc
from climada.engine.impact_forecast import ImpactForecast
from climada.entity import ImpactFuncSet
from climada.hazard.forecast import HazardForecast  # pylint: disable=import-error  # TODO: Fix climada.hazard.forecast import

from impact_forecasting_warning.hazard.weather_api import fetch_ogd_forecast
from impact_forecasting_warning.hazard.hazard_forecast import create_hazard_forecast
from impact_forecasting_warning.exposure.exposure_data import create_litpop_exposure, load_geodataframes
from impact_forecasting_warning.exposure.exposure_creation import prepare_elevation_based_exposure
from impact_forecasting_warning.vulnerability.wind import from_welker, create_warning_impact_functions
from impact_forecasting_warning.visualization.plots import (
    create_national_plot,
    create_cantonal_plot,
    create_warning_plot,
    create_impact_warning_plots,
    create_relative_impact_warning_plots,
    create_impact_map,
)


def wind_dmg_fc_to_buildings(haz_fc: HazardForecast) -> tuple:
    """
    Compute building damage impacts for Switzerland.

    :param haz_fc: HazardForecast object containing wind speed data.
    :type haz_fc: HazardForecast
    :return: Tuple containing (exposure, impact_forecast).
    :rtype: tuple
    """
    # Create exposure for building values
    exp_ch = create_litpop_exposure(convert_to_chf=True)
    exp_ch.assign_centroids(haz_fc, threshold=100)

    # Create impact function set
    impf_set = ImpactFuncSet([from_welker()])

    # Calculate impact
    imp_fc = ImpactCalc(exp_ch, impf_set, haz_fc).impact(assign_centroids=False)

    return exp_ch, imp_fc


def wind_hazard_based_warning(haz_fc: HazardForecast) -> ImpactForecast:
    """
    Compute hazard-based warnings using elevation-dependent thresholds.

    :param haz_fc: HazardForecast object.
    :type haz_fc: HazardForecast
    :return: Warning impacts.
    :rtype: ImpactForecast
    """
    # Prepare elevation-based exposure
    constant_exposure = prepare_elevation_based_exposure(haz_fc)

    # Create warning impact functions
    impf_set = create_warning_impact_functions()

    # Calculate warning impacts
    imp_warnings = ImpactCalc(constant_exposure, impf_set, haz_fc).impact(assign_centroids=False)

    return imp_warnings


def run_pipeline(n_days: int = 5) -> None:
    """
    Run the complete wind impact forecast pipeline.
    
    This pipeline performs the following steps:
    1. Fetch wind forecast data from OGD API
    2. Create HazardForecast object
    3. Compute building damage impacts
    4. Compute hazard-based warnings
    5. Generate visualizations for each forecast day
    
    Output files are saved to ``results/plots`` (visualizations) and
    ``results/output_data`` (CSV exports).

    :param n_days: Number of forecast days to process.
    :type n_days: int
    :return: None
    :rtype: None
    """
    # Step 1: Fetch weather forecast data
    da_forecast = fetch_ogd_forecast(model="ogd-forecasting-icon-ch2",
                                     variable="VMAX_10M",
                                     reftime="latest",
                                     n_days=n_days)

    # Step 2: Create HazardForecast object
    haz_fc, reference_time, _, valid_time_strs, valid_time_prints, base_strs, base_strs_output_data = (
        create_hazard_forecast(da_forecast, hazard_type="WS", intensity_unit="m/s", variable_name="VMAX_10M"))

    # Step 3: Compute building impacts
    exp_ch, imp_fc = wind_dmg_fc_to_buildings(haz_fc)

    # Step 4: Compute hazard warnings
    imp_warnings = wind_hazard_based_warning(haz_fc)

    # Step 5: Load geodata for visualization
    gdf_warningregions, gdf_cantons, shift_center_of_mass_by_name = load_geodataframes()

    # Create output directories
    for base_str in base_strs:
        Path(base_str).parent.mkdir(parents=True, exist_ok=True)
    for base_str in base_strs_output_data:
        Path(base_str).parent.mkdir(parents=True, exist_ok=True)

    # Step 6: Iterate over forecast days and create visualizations
    for i in range(n_days):
        forecast_day = i
        impact = imp_fc.select(lead_time=np.unique(imp_fc.lead_time)[i])
        valid_time_print = valid_time_prints[i]
        base_str = base_strs[i]
        base_str_output_data = base_strs_output_data[i]

        imp_warning = imp_warnings.select(lead_time=np.unique(imp_warnings.lead_time)[i]).median()

        # Create all plots for this forecast day
        create_national_plot(impact, exp_ch, reference_time, valid_time_print, base_str)
        create_cantonal_plot(impact, exp_ch, gdf_cantons, shift_center_of_mass_by_name, reference_time,
                             valid_time_print, base_str, base_str_output_data, forecast_day)
        create_warning_plot(imp_warning, gdf_warningregions, reference_time, valid_time_print, base_str)
        create_impact_warning_plots(impact.mean(), gdf_warningregions, reference_time, valid_time_print, base_str)
        create_relative_impact_warning_plots(impact.mean(), exp_ch, gdf_warningregions, reference_time,
                                             valid_time_print, base_str)
        create_impact_map(impact.mean(), exp_ch, gdf_warningregions, reference_time, valid_time_print, base_str)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run wind impact forecast pipeline for Switzerland")
    parser.add_argument("--n-days", type=int, default=5, help="Number of forecast days to process (default: 5)")
    args = parser.parse_args()

    run_pipeline(n_days=args.n_days)
