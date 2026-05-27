"""Shared pytest fixtures for impact_forecasting_warning tests."""
from typing import Any
import pytest
import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
from pathlib import Path
from shapely.geometry import Point, Polygon


@pytest.fixture
def mock_hazard_forecast() -> Any:
    """Create a mock HazardForecast object for testing.
    
    Returns:
        Mock HazardForecast with multiple ensemble members.
    """
    # TODO: Implement mock HazardForecast object
    pass


@pytest.fixture
def mock_exposure() -> Any:
    """Create a mock LitPop exposure object for testing.
    
    Returns:
        Mock Exposures object with sample Swiss data.
    """
    # TODO: Implement mock Exposures object
    pass


@pytest.fixture
def mock_geodataframes() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, dict[str, Any]]:
    """Create mock GeoDataFrames for cantons and warning regions.
    
    Returns:
        Tuple of (warning_regions_gdf, cantons_gdf, label_shift_dict).
    """
    # TODO: Implement mock GeoDataFrames
    pass


@pytest.fixture
def mock_xarray_forecast() -> xr.DataArray:
    """Create a synthetic weather forecast DataArray for testing.
    
    Returns:
        xarray DataArray with dimensions (eps, lead_time, lat, lon).
    """
    # TODO: Implement synthetic forecast DataArray
    pass


@pytest.fixture
def mock_api_response() -> Any:
    """Create a mock response for earthkit.data API calls.
    
    Returns:
        Mock API response object.
    """
    # TODO: Implement mock API response
    pass


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for plot outputs.
    
    Args:
        tmp_path: pytest's built-in temporary directory fixture.
    
    Returns:
        Path to temporary output directory.
    """
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    return output_dir
