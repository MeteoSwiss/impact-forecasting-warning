"""
Pipeline for WiSchaWa based on OGD data

Created on Tue Apr 2026
@author: Valentin Gebhart, vgebhart@ethz.ch
"""

import cartopy.crs as ccrs
import geopandas as gpd
import matplotlib as mpl
import matplotlib.ticker as ticker
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from shapely.affinity import translate
import srtm
import xarray as xr
from datetime import datetime, timedelta


from climada import CONFIG
from climada.hazard.forecast import HazardForecast
from climada.engine import ImpactCalc
from climada.entity import LitPop, Exposures, ImpactFunc, ImpactFuncSet
from climada.engine.calibration_opt import init_impf

# import scClim as sc
# from scClim.constants import VARNAME_DICT, CH_EXTENT,CH_EXTENT_EPSG2056
import util_functions as u_func

# define data paths
path_to_warningregion_shapes = f"{CONFIG.local_data.data_dir}/warning_regions/Warningregions.shp"
path_to_canton_shapes = f"{CONFIG.local_data.data_dir}/ch_shapefile/swissTLMRegio_KANTONSGEBIET_LV95.shp"


####################################
######### get hazard data ##########
####################################

from earthkit.data import config
from meteodatalab import ogd_api
config.set("cache-policy", "temporary")

# lead_times = [f"P0DT{i}H" for i in np.arange(48, 72)] # lead times of ICON-CH2-EPS up 5d, here +48h, to +72h
lead_times = [f"P0DT{i}H" for i in np.arange(0, 5*24)] # lead times of ICON-CH2-EPS up 5d, here +48h, to +72h
lead_times_window = lead_times[0].lstrip("P0DT") + " - " + lead_times[-1].lstrip("P0DT")
model = "ogd-forecasting-icon-ch2"
nwp_var = "VMAX_10M"  # precip. "TOT_PREC", temperature: "T_2M", wind "VMAX_10M"
reftime = "latest"

req_det = ogd_api.Request(
    collection=model,
    variable=nwp_var,
    reference_datetime=reftime,
    perturbed=False,  # deterministic forecast
    lead_time=lead_times,
)
windfield_det =  ogd_api.get_from_ogd(req_det)

req_pert = ogd_api.Request(
    collection=model,
    variable=nwp_var,
    reference_datetime=reftime,
    perturbed=True,  # perturbed forecasts
    lead_time=lead_times,
)
windfield_pert =  ogd_api.get_from_ogd(req_pert)

da_forecast = xr.concat([windfield_det, windfield_pert], dim="eps")

reference_time = str(da_forecast.ref_time.values[0])[:-13]
ref_time_str = reference_time.replace('-', '').replace('T', '').replace(':', '')[:-2]
# valid_time_strs = [str(int(ref_time_str[:-2])+i) for i in range(5)]
valid_time_strs = [
    (datetime.fromisoformat(reference_time) + timedelta(days=i)).strftime("%Y%m%d")
    for i in range(5)
]
valid_time_prints = [valid_time_str[:4] + "-" + valid_time_str[4:6] + "-" + valid_time_str[6:] for valid_time_str in valid_time_strs]
base_strs = [f"{CONFIG.engine.forecast.plot_dir}/WS_C2E_run{ref_time_str}_event{valid_time_str}_Switzerland" for valid_time_str in valid_time_strs]
base_strs_output_data = [f"{CONFIG.engine.forecast.plot_dir}/output_data/WS_C2E_run{ref_time_str}_event{valid_time_str}" for valid_time_str in valid_time_strs]

da_forecast = da_forecast.groupby("lead_time.days").max(dim="lead_time").rename({"days": "forecast_day"})
da_forecast = da_forecast.assign_coords(
    forecast_day=(
        da_forecast.forecast_day.values.astype("timedelta64[D]")
                                 .astype("timedelta64[ns]")
    )
)

# create HazardForecast object from downloaded dataarray
haz_fc = HazardForecast.from_xarray_raster(
    da_forecast.to_dataset(name="VMAX_10M"),
    hazard_type="WS",
    intensity_unit="m/s",
    coordinate_vars={
        "longitude": "lon",
        "latitude": "lat",
        "lead_time": "forecast_day",
        "member": "eps",
    },
    intensity="VMAX_10M",
)

####################################
######### compute impacts ##########
####################################

# expsure for building values
exp_ch = LitPop.from_countries("CHE")
# convert to CHF
exp_ch.data["value"] = 0.78 * exp_ch.data["value"]
exp_ch.value_unit = "CHF"

exp_ch.assign_centroids(haz_fc, threshold=100)

def from_schwierz(impf_id=1):
    """Generate the impact function of Schwierz et al. 2010, doi:10.1007/s10584-009-9712-1"""
    impf = ImpactFunc()
    impf.name = "Schwierz 2010"
    impf.id = impf_id
    impf.intensity_unit = "m/s"
    impf.haz_type = "WS"
    impf.intensity = np.array([0, 20, 25, 30, 35, 40, 45, 50, 55, 60, 80, 100])
    impf.paa = np.array([
        0.0, 0.0, 0.001, 0.00676, 0.03921, 0.10707, 0.25357, 0.48869, 0.82907, 1.0, 1.0, 1.0,
    ])
    impf.mdd = np.array([
        0.0, 0.0, 0.001, 0.00177515, 0.00367253, 0.00749977, 0.01263556, 0.01849639, 0.02370487, 0.037253, 0.037253, 0.037253,
    ])
    impf.check()
    return impf

def from_welker(impf_id=1):
    """Return the impact function of Welker et al. 2021, doi:10.5194/nhess-21-279-2021"""
    temp_Impf = from_schwierz()
    scaling_factor = {"paa_scale": 1.332518, "mdd_scale": 1.332518}
    temp_Impf = init_impf(temp_Impf, scaling_factor)[0]
    temp_Impf.name = "Welker 2021"
    temp_Impf.id = impf_id
    temp_Impf.check()
    return temp_Impf

impf_set = ImpactFuncSet([from_welker()])

imp_fc = ImpactCalc(exp_ch, impf_set, haz_fc).impact(assign_centroids=False)

# Prepare exposure including different warning thresholds pased on elevation
haz_fc.centroids.set_region_id()
constant_exposure_gdf = haz_fc.centroids.gdf
constant_exposure_gdf = constant_exposure_gdf.loc[
    constant_exposure_gdf["region_id"] == 756
]  # numeric iso of CH
constant_exposure_gdf.drop(columns="on_land", inplace=True)
constant_exposure_gdf["value"] = 1.0
constant_exposure_gdf["impf_"] = 1
elev = srtm.get_data()
constant_exposure_gdf["elevation"] = [
    elev.get_elevation(lat, lon)
    for lon, lat in zip(
        constant_exposure_gdf.geometry.x, constant_exposure_gdf.geometry.y
    )
]

####################################
##### compute hazard warnings ######
####################################

constant_exposure = Exposures(constant_exposure_gdf)
# Locations points above 1600m elevation have different warning thresholds (encoded in the impact functions)
constant_exposure.data.loc[constant_exposure_gdf["elevation"] > 1600, "impf_"] = 2
constant_exposure.assign_centroids(haz_fc, threshold=100)

# Create impact functions corresponding to MeteoSwiss warning levels
imp_fun_low = ImpactFunc()
imp_fun_low.haz_type = "WS"
imp_fun_low.id = 1
imp_fun_low.name = "warn_level_low_elevation"
imp_fun_low.intensity_unit = "m/s"
imp_fun_low.intensity = np.array(
    [0.0, 19.439, 19.44, 24.999, 25.0, 30.549, 30.55, 38.879, 38.88, 100.0]
)
imp_fun_low.mdd = np.array([1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 4.0, 5.0, 5.0])
imp_fun_low.paa = np.ones_like(imp_fun_low.mdd)
imp_fun_low.check()

imp_fun_high = ImpactFunc()
imp_fun_high.haz_type = "WS"
imp_fun_high.id = 2
imp_fun_high.name = "warn_level_high_elevation"
imp_fun_high.intensity_unit = "m/s"
imp_fun_high.intensity = np.array(
    [0.0, 27.776, 27.777, 36.110, 36.111, 44.443, 44.444, 55.554, 55.555, 100.0]
)
imp_fun_high.mdd = np.array([1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 4.0, 5.0, 5.0])
imp_fun_high.paa = np.ones_like(imp_fun_high.mdd)

Hbw_impf_set = ImpactFuncSet([imp_fun_low, imp_fun_high])

# compute impacts
imp_warnings = (
    ImpactCalc(constant_exposure, Hbw_impf_set, haz_fc)
    .impact(assign_centroids=False)
)

####################################
### prepare gdfs for aggregation ###
####################################

gdf_warningregions = gpd.read_file(path_to_warningregion_shapes)
gdf_warningregions.crs = ccrs.epsg(21781)
gdf_warningregions = gdf_warningregions.dissolve(by="REGION_NAM", as_index=False)
gdf_warningregions = gdf_warningregions[["REGION_NAM", "geometry"]]
gdf_warningregions = gdf_warningregions.to_crs(epsg=4326)

# prepare canton shapes
gdf_cantons = gpd.read_file(path_to_canton_shapes)
gdf_cantons = gdf_cantons.to_crs(epsg=4326)
gdf_cantons = gdf_cantons.dissolve(by="NAME", as_index=False)
gdf_cantons = gdf_cantons.loc[gdf_cantons.ICC == "CH", :].reset_index(drop=True)
gdf_cantons = gdf_cantons[["NAME", "geometry"]]
shift_center_of_mass_by_name = {
    "Basel-Landschaft": np.array([0.05, 0]),
    "Obwalden": np.array([-0.02, 0]),
    "Nidwalden": np.array([0, 0.01]),
    "St. Gallen": np.array([-0.15, -0.001]),
    "Appenzell Ausserrhoden": np.array([-0.02, 0.05]),
    "Appenzell Innerrhoden": np.array([0.03, -0.04]),
}


for i in range(5): # iterate over lead time days:
# for i in range(1): # iterate over lead time days:
    forcast_day = i
    impact = imp_fc.select(lead_time=np.unique(imp_fc.lead_time)[i])
    mean_impact = np.mean(impact.at_event)
    valid_time_str = valid_time_strs[i]
    valid_time_print = valid_time_prints[i]
    base_str = base_strs[i]
    base_str_output_data = base_strs_output_data[i]

    imp_warning = imp_warnings.select(lead_time=np.unique(imp_warnings.lead_time)[i]).median()

    ####################################
    ######### national plots ###########
    ####################################

    shift_bins = max(np.round(np.log10(np.mean(impact.at_event))) - 3, 0)
    bins = np.geomspace(10**shift_bins, 10 ** (5 + shift_bins), 11)

    ax = u_func.plot_impact_log_hist(
        impact,
        title=f"National impact-based forecast for $\\bf{{{valid_time_print}}}$ (init time: {reference_time})",
        impact_label=f"Total building damages ({exp_ch.value_unit})",
        bins=bins,
        ticks=bins[::2],
        figsize=(6,4),
    )
    ax.text(0.6, 0.9, f"mean damage: {exp_ch.value_unit} {mean_impact:,.0f}".replace(",", "'"), transform=ax.transAxes, fontdict={"fontsize": 12},
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor="black")
    )
    ax.get_figure().savefig(base_str + f"_histbin.svg", dpi=300, bbox_inches='tight')

    ####################################
    ######### cantonal plots ###########
    ####################################

    init_time = reference_time
    bins = np.geomspace(0.00005, 0.005, 5)

    ax = u_func.plot_member_piechart_per_region(
        impact,
        gdf_cantons,
        "sum",
        pie_rel_size=0.15,
        bins=bins,
        figsize=(8.5, 5.5),
        title=f"Cantonal impact-based forecast for $\\bf{{{valid_time_print}}}$ (init time: {reference_time})",
        cbar_title="Relative impact",
        exposure_for_normalization=exp_ch,
        shift_center_of_mass_by_name=shift_center_of_mass_by_name,
    )
    ax.set_xticks([])
    ax.set_yticks([]);
    ax.get_figure().savefig(base_str + "_canton_impact_map.jpeg", dpi=300, bbox_inches='tight',
        # pil_kwargs={"quality": 95}
    )

    impact_per_canton = u_func.aggregate_impacts_by_gdf(impact, gdf_cantons, "sum")
    median_col_name = f"median_estimated_damage [{exp_ch.value_unit}]"
    impact_per_canton[median_col_name] = np.median(impact_per_canton[range(1+21*i, 22+21*i)], axis=1)
    impact_per_canton.rename(columns={"NAME": "canton"})[["canton", median_col_name]].set_index("canton").to_csv(
        f"{base_str_output_data}_canton_medians.csv"
    )


    ####################################
    ########## warning plots ###########
    ####################################

    ax = u_func.plot_impact_polygons(
        imp_warning,
        gdf_warningregions,
        agg_func="median",
        title=f"Hazard-based warning for $\\bf{{{valid_time_print}}}$ (init time: {reference_time})",
        figsize=(8.5, 5.5),
    )
    ax.set_xticks([])
    ax.set_yticks([]);
    ax.get_figure().savefig(base_str + "_warn_map.jpeg", dpi=300, bbox_inches='tight',
        # pil_kwargs={"quality": 95}
    )

    ####################################
    ###### impact-based warnings #######
    ####################################

    for impact_warning_thresholds, label in zip(
        [np.array([1e4,1e5,1e6,1e7]), np.array([1e4,1e5,1e6,1e7])/10],
        ["large_thresh", "small_thresh"]
    ):
        impact_warning_labels = ["1: Minimal or no damage"] + [
            f"{k+2}: Damage above {u_func.print_large_amounts(thresh)}" for k, thresh in enumerate(impact_warning_thresholds)
        ]

        ax = u_func.plot_impact_polygons(
            impact.mean(),
            gdf_warningregions,
            agg_func="sum",
            title=f"Impact-based warning for $\\bf{{{valid_time_print}}}$ (init time: {reference_time})",
            figsize=(8.5, 5.5),
            warning_thresholds=impact_warning_thresholds,
            warning_labels=impact_warning_labels
        )
        ax.set_xticks([])
        ax.set_yticks([]);
        ax.get_figure().savefig(base_str + f"_impact_warn_map_{label}.jpeg", dpi=300, bbox_inches='tight',)

    ####################################
    ## relative-impact-based warnings ##
    ####################################

    for relative_impact_warning_thresholds, label in zip(
        [np.array([1e-5,1e-4,1e-3,1e-2]), np.array([1e-5,1e-4,1e-3,1e-2])/10],
        ["large_thresh", "small_thresh"]
    ):
        relative_impact_warning_labels = ["1: Minimal or no damage"] + [
            f"{k+2}: Damage above " + (f"{thresh*100:.3f} %" if label=="large_thresh" else f"{thresh*100:.4f} %") for k, thresh in enumerate(relative_impact_warning_thresholds)
        ]

        ax = u_func.plot_impact_polygons(
            impact.mean(),
            gdf_warningregions,
            agg_func="sum",
            exposure_for_normalization=exp_ch,
            title=f"Relative-impact-based warning for $\\bf{{{valid_time_print}}}$ (init time: {reference_time})",
            figsize=(8.5, 5.5),
            warning_thresholds=relative_impact_warning_thresholds,
            warning_labels=relative_impact_warning_labels
        )
        ax.set_xticks([])
        ax.set_yticks([]);
        ax.get_figure().savefig(base_str + f"_rel_impact_warn_map_{label}.jpeg", dpi=300, bbox_inches='tight',)

    ####################################
    ##### impact-based forecasts #######
    ####################################

    ax = u_func.plot_impact_with_region_shapes(
        impact.mean(),
        gdf_warningregions,
        title=f"Impact-based forecast for $\\bf{{{valid_time_print}}}$ (init time: {reference_time})",
        cbar_title=f"Building damages ({exp_ch.value_unit}), mean over forecast members",
        vmin=100,
        vmax=1e5,
    )
    ax.set_xticks([])
    ax.set_yticks([]);
    ax.get_figure().savefig(base_str + "_impact_map.jpeg", dpi=300, bbox_inches='tight',)
