"""
Util functions for aggregation and plotting of impact-based forecasts

Created on Tue Apr 2026
@author: Valentin Gebhart, vgebhart@ethz.ch
"""

import geopandas as gpd
import matplotlib as mpl
import matplotlib.ticker as ticker
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from shapely.affinity import translate
import srtm
import xarray as xr

def print_large_amounts(x):
    return (
        f'{x/1e9:.1f}B' if x>=1e9 else
        f'{x/1e6:.0f}M' if x>=1e6 else
        f'{x/1e3:.0f}k' if x>=1e3 else
        f'{x:.0f}'
    )

def aggregate_impacts_by_gdf(
    impact,
    gdf,
    agg_func,
):
    """
    Aggregate impacts by geographical data frame (GDF) regions.

    This function aggregates impact data from an impact object onto a given GeoDataFrame
    by performing a spatial join and applying an aggregation function.

    Parameters
    ----------
    impact : Impact
        The impact object containing impact matrix and coordinates.
    gdf : GeoDataFrame
        The geographical regions to aggregate impacts over.
    agg_func : callable
        The aggregation function to apply (e.g., 'sum', 'mean').

    Returns
    -------
    GeoDataFrame
        A copy of the input GDF with added columns for aggregated impacts per event.
    """
    gdf_result = gdf.copy()
    gdf_impact = gpd.GeoDataFrame(
        impact.imp_mat.T.todense(),
        columns=impact.event_id,
        geometry=gpd.points_from_xy(
            impact.coord_exp[:, 1], impact.coord_exp[:, 0], crs=impact.crs
        ),
    )

    joined_gdf = gpd.sjoin(gdf, gdf_impact, how="inner", predicate="intersects")
    gdf_result[impact.event_id] = joined_gdf.groupby(level=0)[[*impact.event_id]].agg(
        agg_func
    )

    return gdf_result


def aggregate_exposures_by_gdf(
    exposure,
    gdf,
    agg_func="sum",
):
    """
    Aggregate exposures by geographical data frame (GDF) regions.

    This function aggregates exposure values from an exposure object onto a given GeoDataFrame
    by performing a spatial join and applying an aggregation function.

    Parameters
    ----------
    exposure : Exposure
        The exposure object containing exposure data and geometry.
    gdf : GeoDataFrame
        The geographical regions to aggregate exposures over.
    agg_func : str or callable, optional
        The aggregation function to apply (default is 'sum').

    Returns
    -------
    GeoDataFrame
        A copy of the input GDF with an added 'value' column for aggregated exposures.
    """
    gdf_result = gdf.copy()
    joined_gdf = gpd.sjoin(
        gdf, exposure.gdf[["geometry", "value"]], how="inner", predicate="intersects"
    )
    gdf_result["value"] = joined_gdf.groupby(level=0)[["value"]].agg(agg_func)
    return gdf_result

def plot_impact_log_hist(
    imp_fc,
    bins=None,
    ax=None,
    fit_gaussian_kernel_for_logs=True,
    ci_quantiles=None,
    title=None,
    impact_label=None,
    kwargs_hist=None,
    kwargs_cis=None,
    ticks=None,
    xticklabels=None,
    legend_label=None,
    **kwargs,
):
    """
    Plot logarithmic histogram of impact forecast with confidence intervals.

    This function generates a histogram of impact values on a log scale, with optional
    Gaussian kernel density estimation, scatter plot, and confidence interval bars.

    Parameters
    ----------
    imp_fc : ImpactForecast
        The impact forecast object.
    bins : array-like, optional
        Bins for the histogram (default geometric (log) spacing).
    ax : matplotlib Axes, optional
        Axes to plot on (default creates new figure).
    fit_gaussian_kernel_for_logs : bool, optional
        Whether to fit a Gaussian kernel (default True).
    ci_quantiles : array-like, optional
        Quantiles for confidence intervals (default [[0.05, 0.95], [0.25, 0.75]]).
    title : str, optional
        Plot title.
    impact_label : str, optional
        Label for x-axis.
    kwargs_hist : dict, optional
        Additional kwargs for histogram.
    kwargs_cis : dict, optional
        Additional kwargs for confidence intervals.
    ticks : array-like, optional
        X-axis ticks.
    xticklabels : list, optional
        X-axis tick labels.
    legend_label : str, optional
        Label for legend.
    **kwargs : dict
        Additional plotting kwargs.

    Returns
    -------
    matplotlib Axes
        The axes object with the plot.
    """

    # cut damages to bins
    if bins is None:
        if imp_fc.at_event.max() <= 1.0:
            raise ValueError("Largest aggregated impact below 1. Provide bins.")
        bins = np.geomspace(1, imp_fc.at_event.max(), 11)
    bins_log = np.log10(bins)
    impact_clipped = imp_fc.at_event.clip(min=bins[0], max=bins[-1])

    if fit_gaussian_kernel_for_logs:
        imp_log = np.log10(impact_clipped)
        kernel = (
            stats.gaussian_kde(imp_log)
            if any(imp_log > bins_log[0] + 1e-4)
            else stats.gaussian_kde([0] * 10 + [1e-3])
        )  # compute quantiles
    # compute quantiles
    if ci_quantiles is None:
        ci_quantiles = np.array([[0.05, 0.95], [0.25, 0.75]])
    imp_quantiles = np.array([np.quantile(impact_clipped, q) for q in ci_quantiles])

    fig, ax = (
        plt.subplots(1, 1, figsize=kwargs.get("figsize", (10, 6)))
        if ax is None
        else (ax.get_figure(), ax)
    )
    ax_pos = [0, 0.2, 1.1, 0.8]
    ax.set_position(ax_pos)
    ax.set_xscale("log")

    # plot histograms

    if kwargs_hist is None:
        kwargs_hist = {}
    kwargs_hist = {
        "color": np.array([230, 50, 30, 255]) / 255,
        "alpha": 0.9,
        "rescale_height": 1.0,
    } | (kwargs_hist or {})
    xlims = (bins[0], bins[-1])

    counts, _, rectangles = ax.hist(
        impact_clipped,
        bins=bins,
        edgecolor="black",
        **{k: v for k, v in kwargs_hist.items() if k not in ["rescale_height"]},
    )
    for r in rectangles:
        r.set_height(r.get_height() * kwargs_hist["rescale_height"])

    # plot fits
    if fit_gaussian_kernel_for_logs:
        outline = mpl.patheffects.withStroke(linewidth=6, foreground="black")
        normalization = (
            len(impact_clipped) * (bins_log[-1] - bins_log[0]) / (len(bins) - 1)
        )
        ax.plot(
            np.geomspace(bins[0], bins[-1], 1000),
            normalization * kernel(np.linspace(bins_log[0], bins_log[-1], 1000)),
            color=kwargs_hist["color"],
            linewidth=4,
            path_effects=[outline],
        )

    # plot scatter impacts
    ax_scatter = fig.add_axes([0, ax_pos[1] / 2, ax_pos[2], ax_pos[1] / 2])
    ax_scatter.set_xscale("log")
    ax_scatter.scatter(
        impact_clipped,
        [1.0] * len(impact_clipped),
        s=30,
        color=kwargs_hist["color"],
        alpha=kwargs_hist["alpha"],
    )
    ax_scatter.set_ylim(0.9, 1.1)

    # plot confidence intervals
    if kwargs_cis is None:
        kwargs_cis = {}
    kwargs_cis = {"colors": np.full(len(ci_quantiles), "darkgray")} | kwargs_cis
    ax_intervals = fig.add_axes([0, 0, ax_pos[2], ax_pos[1] / 2])
    ax_intervals.set_xscale("log")
    ax_intervals.set_ylim(0.0, len(ci_quantiles))
    anchors = np.linspace(0.0, len(ci_quantiles) - 1, len(ci_quantiles))[::-1]
    for i, (p_min, p_max) in enumerate(ci_quantiles):
        ax_intervals.add_patch(
            mpl.patches.Rectangle(
                (imp_quantiles[i, 0], anchors[i]),
                imp_quantiles[i, 1] - imp_quantiles[i, 0],
                1.0,
                facecolor=kwargs_cis["colors"][i],
            )
        )
        ax_intervals.annotate(
            f"({p_min}-{p_max}) confidence interval",
            (0.95 * xlims[1], anchors[i] + 0.5),
            color="k",
            ha="right",
            va="center",
        )

    # Unified axis settings
    for a in [ax, ax_scatter, ax_intervals]:
        a.set_xlim(*xlims)
    ax.set_ylim(0, len(impact_clipped) * kwargs_hist["rescale_height"])
    ax.set_yticks(np.array([0.2 * i for i in range(6)]) * len(impact_clipped))
    ax.set_yticklabels([f"{20*i}%" for i in range(6)])
    ax.set_ylabel("probability")
    ax_scatter.set_yticks([])
    ax_intervals.set_yticks([])
    ax.set_xticklabels([])
    ax_scatter.set_xticklabels([])
    if ticks is None:
        ticks = bins
    ax_intervals.set_xticks(ticks)
    if xticklabels:
        ax_intervals.set_xticklabels(xticklabels)
    else:
        ax_intervals.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: print_large_amounts(x))
)

    impact_label = impact_label or f"Impact ({imp_fc.unit})"
    ax_intervals.set_xlabel(impact_label)

    # add a legend
    if legend_label:
        patch = mpl.patches.Patch(color=kwargs_hist["color"], label=legend_label)
        legend = ax.get_legend()
        if legend:
            handles, labels = legend.legend_handles, [
                t.get_text() for t in legend.get_texts()
            ]
            ax.legend(handles + [patch], labels + [legend_label])
        else:
            ax.legend([patch], [legend_label], loc="upper right")

    ax.set_title(title)
    return ax

def plot_member_piechart_per_region(
    impact_forecast,
    gdf_regions,
    agg_func,
    bins=None,
    ax=None,
    exposure_for_normalization=None,
    pie_rel_size=0.1,
    title=None,
    cbar_title=None,
    cmap=None,
    shift_center_of_mass_by_name=None,
    kwargs_pie=None,
    **kwargs,
):
    """
    Plot pie charts for each region showing impact forecast member distributions.

    This function creates a map with pie charts centered in each region, where each pie
    represents the distribution of impact forecast members, optionally normalized by exposure.

    Parameters
    ----------
    impact_forecast : ImpactForecast
        The impact forecast object.
    gdf_regions : GeoDataFrame
        The geographical regions for plotting.
    agg_func : callable
        Aggregation function for impacts.
    bins : array-like, optional
        Bins for categorizing impact values (default auto-generated).
    ax : matplotlib Axes, optional
        Axes to plot on (default creates new figure).
    exposure_for_normalization : Exposure, optional
        Exposure data for normalizing impacts.
    pie_rel_size : float, optional
        Relative size of pie charts (default 0.1).
    title : str, optional
        Plot title.
    cbar_title : str, optional
        Colorbar title.
    cmap : matplotlib colormap, optional
        Colormap for pie colors (default 'Reds').
    shift_center_of_mass_by_name : dict, optional
        Dictionary to shift pie centers by region name.
    kwargs_pie : dict, optional
        Additional kwargs for pie charts.
    **kwargs : dict
        Additional plotting kwargs.

    Returns
    -------
    matplotlib Axes
        The axes object with the plot.
    """
    if isinstance(cmap, str):
        cmap = plt.get_cmap(cmap)
    if cmap is None:
        cmap = plt.get_cmap("Reds")
    if kwargs_pie is None:
        kwargs_pie = {}
    kwargs_pie = {
        "startangle": 90,
        "wedgeprops": {"linewidth": 0.3, "edgecolor": "black", "alpha": 1.0},
    } | kwargs_pie
    if ax is not None and hasattr(ax, "projection"):
        current_crs = ax.projection
    else:
        current_crs = gdf_regions.crs

    if ax is None:
        ax = gdf_regions.geometry.plot(
            facecolor="white", edgecolor="black", figsize=kwargs.get("figsize", (10, 6))
        )
    else:
        gdf_regions.geometry.to_crs(current_crs).plot(
            ax=ax, facecolor="white", edgecolor="black"
        )
    bbox = (*ax.get_xlim(), *ax.get_ylim())

    gdf_impact_agg = aggregate_impacts_by_gdf(impact_forecast, gdf_regions, agg_func)
    gdf_impact_agg["centerofmass"] = gdf_impact_agg.geometry.to_crs(
        current_crs
    ).centroid
    if shift_center_of_mass_by_name is not None:
        for name, shift in shift_center_of_mass_by_name.items():
            gdf_impact_agg.loc[gdf_impact_agg["NAME"] == name, "centerofmass"] = (
                gdf_impact_agg.loc[
                    gdf_impact_agg["NAME"] == name, "centerofmass"
                ].apply(lambda g: translate(g, *shift))
            )

    if exposure_for_normalization is not None:
        agg_exp = aggregate_exposures_by_gdf(exposure_for_normalization, gdf_regions)
        if (
            gdf_impact_agg[list(impact_forecast.event_id)].shape[0]
            != agg_exp["value"].shape[0]
        ):
            raise ValueError(
                f"Number of columns of aggregated impact matrix "
                f"(shape {gdf_impact_agg[list(impact_forecast.event_id)].shape})"
                f"does not correspond to number of columns of aggregated exposure "
                f"({agg_exp['value'].shape[0]})."
            )
        gdf_impact_agg[list(impact_forecast.event_id)] = gdf_impact_agg[
            list(impact_forecast.event_id)
        ].div(agg_exp["value"], axis=0)

    max_values = gdf_impact_agg[list(impact_forecast.event_id)].values.max()
    if bins is None:
        bins = np.linspace(0, max_values, 5)
    pie_width = pie_rel_size * min(bbox[1] - bbox[0], bbox[3] - bbox[2])

    for idx, row in gdf_impact_agg.iterrows():
        x_loc, y_loc = row["centerofmass"].x, row["centerofmass"].y
        inset_ax = ax.inset_axes(
            [x_loc - pie_width / 2, y_loc - pie_width / 2, pie_width, pie_width],
            transform=ax.transData,
        )
        values = row[list(impact_forecast.event_id)].values
        indices = np.searchsorted(bins, np.sort(values))
        colors = cmap(indices / len(bins))
        inset_ax.pie(
            np.ones(len(impact_forecast.member)),
            labels=None,
            colors=colors,
            **kwargs_pie,
        )

    cbax = ax.inset_axes([1.05, 0, 0.05, 1])
    norm = mpl.colors.BoundaryNorm(bins, cmap.N, extend="both")
    cbar = ax.get_figure().colorbar(
        mpl.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cbax, orientation="vertical"
    )
    cbar.set_label(cbar_title)
    ax.set_title(title)
    return ax

def plot_impact_polygons(
    impact,
    gdf_regions,
    agg_func="max",
    exposure_for_normalization=None,
    ax=None,
    title=None,
    warning_thresholds=None,
    warning_colors=None,
    warning_labels=None,
    kwargs_legend=None,
    **kwargs
):
    """
    Plot warning polygons based on impact thresholds.

    This function visualizes warning regions colored by aggregated impact levels,
    using a discrete colormap for hazard severity.

    Parameters
    ----------
    impact : Impact
        The impact object.
    gdf_regions : GeoDataFrame
        The regions GeoDataFrame.
    agg_func : str or callable, optional
        Aggregation function (default 'max').
    exposure_for_normalization : Exposure, optional
        Exposure data for normalizing impacts.
    ax : matplotlib Axes, optional
        Axes to plot on (default creates new figure).
    title : str, optional
        Plot title (default auto-generated).
    warning_threshold : array-like, optional
        Threshold above which different warning colors are plotted.
    warning_colors : array-like, optional
        RGBA colors for warning levels (default predefined). Number must be one more that warning_threshold.
    warning_labels : list, optional
        Labels for warning levels (default predefined). Number must be one more that warning_threshold.
    kwargs_legend : dict, optional
        Additional kwargs for legend.
    **kwargs : dict
        Additional plotting kwargs.

    Returns
    -------
    matplotlib Axes
        The axes object with the plot.
    """

    gdf_impact = aggregate_impacts_by_gdf(
        impact, gdf_regions, agg_func=agg_func
    )

    if exposure_for_normalization is not None:
        agg_exp = aggregate_exposures_by_gdf(exposure_for_normalization, gdf_regions)
        if (
            gdf_impact[list(impact.event_id)].shape[0]
            != agg_exp["value"].shape[0]
        ):
            raise ValueError(
                f"Number of columns of aggregated impact matrix "
                f"(shape {gdf_impact[list(impact.event_id)].shape})"
                f"does not correspond to number of columns of aggregated exposure "
                f"({agg_exp['value'].shape[0]})."
            )
        gdf_impact[list(impact.event_id)] = gdf_impact[
            list(impact.event_id)
        ].div(agg_exp["value"], axis=0)

    figsize = kwargs.pop("figsize", (10, 6))
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    if warning_colors is None:
        warning_colors = (
            np.array(
                [
                    [204, 255, 102, 255],  # green
                    [255, 255, 0, 255],  # yellow
                    [255, 153, 0, 255],  # orange
                    [255, 0, 0, 255],  # red
                    [128, 0, 0, 255],  # dark red
                ]
            )
            / 255
        )
    if warning_labels is None:
        warning_labels = [
            "1: Minimal or no hazard",
            "2: Moderate hazard",
            "3: Significant hazard",
            "4: Severe hazard",
            "5: Very severe hazard",
        ]
    
    if warning_thresholds is None:
        warning_thresholds = [2., 3., 4., 5.]

    cmap = mpl.colors.ListedColormap(warning_colors)
    # norm = mpl.colors.BoundaryNorm(np.arange(0.5, 6.5, 1), cmap.N)

    bounds = [-np.inf] + list(warning_thresholds) + [np.inf]
    norm = mpl.colors.BoundaryNorm(bounds, cmap.N)

    gdf_impact.plot(
        column=1, cmap=cmap, norm=norm, edgecolor="black", linewidth=0.5, ax=ax
    )

    legend_elements = [
        mpl.patches.Patch(facecolor=color, edgecolor="k", label=label)
        for color, label in zip(warning_colors, warning_labels)
    ]
    if kwargs_legend is None:
        kwargs_legend = {}
    kwargs_legend = {
        "loc": "lower right",
        "framealpha": 0.5,
        "bbox_to_anchor": (1.100, -0.02),
    } | kwargs_legend
    ax.legend(handles=legend_elements, **kwargs_legend)
    if title is None:
        title = "Impact-threshold based warning per warning region"
    ax.set_title(title)
    return ax

def plot_impact_with_region_shapes(
    impact,
    gdf_regions,
    ax=None,
    title=None,
    cbar_title=None,
    cmap=None,
    **kwargs,
):
    """
    Plot pie charts for each region showing impact forecast member distributions.

    This function creates a map with pie charts centered in each region, where each pie
    represents the distribution of impact forecast members, optionally normalized by exposure.

    Parameters
    ----------
    impact : ImpactForecast
        The impact object with only one event.
    gdf_regions : GeoDataFrame
        The geographical regions for plotting.
    ax : matplotlib Axes, optional
        Axes to plot on (default creates new figure).
    title : str, optional
        Plot title.
    cbar_title : str, optional
        Colorbar title.
    cmap : matplotlib colormap, optional
        Colormap for pie colors (default 'Reds').
    **kwargs : dict
        Additional plotting kwargs.

    Returns
    -------
    matplotlib Axes
        The axes object with the plot.
    """
    if isinstance(cmap, str):
        cmap = plt.get_cmap(cmap)
    if cmap is None:
        cmap = plt.get_cmap("viridis")
    if ax is not None and hasattr(ax, "projection"):
        current_crs = ax.projection
    else:
        current_crs = gdf_regions.crs
    if ax is None:
        ax = gdf_regions.geometry.plot(
            facecolor="white", edgecolor="black", figsize=kwargs.get("figsize", (10, 6))
        )
    else:
        gdf_regions.geometry.to_crs(current_crs).plot(
            ax=ax, facecolor="white", edgecolor="black"
        )
    bbox = (*ax.get_xlim(), *ax.get_ylim())

    imp = np.asarray(impact.imp_mat.todense()).ravel()
    x = impact.coord_exp[:, 1]
    y = impact.coord_exp[:, 0]
    if np.all(imp <= 0):
        raise ValueError("No positive impact values available for hexbin plotting.")

    norm = mpl.colors.LogNorm(
        vmin=kwargs.get("vmin", imp[imp > 0].min()),
        vmax=kwargs.get("vmax", imp.max()),
    )

    cmap.set_under((0, 0, 0, 0))
    mask = imp > 0
    vmin = kwargs.get("vmin", imp[mask].min())
    mask &= imp >= vmin
    print(sum(mask), np.any(mask))
    n = np.count_nonzero(mask)
    if n >= 3:
        ax.hexbin(
            x[mask],
            y[mask],
            C=imp[mask],
            gridsize=kwargs.get("gridsize", 80),
            cmap=cmap,
            norm=norm,
            mincnt=1,
            linewidths=0,
            alpha=1,
            zorder=2,
        )
    elif n > 0:
        # fallback for 1–2 points
        ax.scatter(
            x[mask],
            y[mask],
            c=imp[mask],
            cmap=cmap,
            norm=norm,
            s=20,
            linewidths=0,
            zorder=2,
        )

    cbax = ax.inset_axes([1.05, 0, 0.05, 1])
    cbar = ax.get_figure().colorbar(
        mpl.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cbax, orientation="vertical", extend="max",
    )
    cbax.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda x, _: print_large_amounts(x))
    )
    cbar.set_label(cbar_title)
    ax.set_title(title)
    return ax
