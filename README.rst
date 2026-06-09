===========================
Impact Forecasting & Warning
===========================

A system for forecasting and visualizing weather impact warnings for Switzerland using CLIMADA.

Getting Started
===============

Setup
-----

**Clone the repository:**

.. code-block:: console

    $ git clone https://github.com/MeteoSwiss/impact-forecasting-warning.git
    $ cd impact-forecasting-warning

Environment Setup
-----------------

This project requires CLIMADA's ``forecast-class`` branch (not available on PyPI). You need to set up a conda environment with CLIMADA from source, then configure Poetry to use that environment.

**1. Create conda environment and install CLIMADA forecast-class:**

Use the provided ``environment.yml`` file:

.. code-block:: console

    # Create conda environment from environment.yml
    $ conda env create -f environment.yml
    $ conda activate climada_env

This installs Python 3.11, all base dependencies (numpy, pandas, xarray, matplotlib, cartopy, geopandas), and CLIMADA's forecast-class branch from GitHub.

**Alternative: Manual installation** (if you need to install CLIMADA in editable mode):

.. code-block:: console

    # Create conda environment (miniforge/miniconda/anaconda)
    $ conda create -n climada_env python=3.11 -y
    $ conda activate climada_env

    # Install base dependencies in conda environment
    $ pip install numpy pandas xarray matplotlib cartopy geopandas

    # Clone and install CLIMADA forecast-class branch
    $ cd ~/git_projects  # or your preferred location
    $ git clone https://github.com/CLIMADA-project/climada_python.git
    $ cd climada_python
    $ git checkout forecast-class
    $ pip install -e .

**2. Configure Poetry to use the conda environment:**

Create a ``poetry.toml`` file in the project root:

.. code-block:: toml

    [virtualenvs]
    create = false

This prevents Poetry from creating its own virtual environment and forces it to use the active conda environment.

**3. Install project dependencies with Poetry:**

.. code-block:: console

    $ cd ~/git_projects/impact-forecasting-warning  # back to project directory
    $ conda activate climada_env  # ensure conda env is active
    $ poetry install

This installs all project dependencies (from ``pyproject.toml``) into the conda environment alongside CLIMADA.

**4. Run the pipeline:**

Always use the conda environment's Python explicitly to avoid conflicts with pyenv or other Python installations:

.. code-block:: console

    $ conda activate climada_env
    $ $CONDA_PREFIX/bin/python -m impact_forecasting_warning.pipelines.wind_impact_forecast --n-days 5

Or use the full path:

.. code-block:: console

    $ /path/to/miniforge3/envs/climada_env/bin/python -m impact_forecasting_warning.pipelines.wind_impact_forecast --n-days 5

**Note:** Use ``--n-days 2`` or higher (minimum 2 days) due to a known issue with CLIMADA's forecast module when handling single-day forecasts.

Scheduling with Cron
---------------------

To run the pipeline automatically on a schedule, create a wrapper script:

.. code-block:: bash

    #!/bin/bash
    # wind_forecast_cron.sh
    
    # Initialize conda
    source ~/miniforge3/etc/profile.d/conda.sh
    conda activate climada_env
    
    # Set up logging
    LOG_DIR="$HOME/git_projects/impact-forecasting-warning/logs"
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/wind_forecast_$(date +%Y%m%d_%H%M%S).log"
    
    # Run pipeline
    cd ~/git_projects/impact-forecasting-warning
    $CONDA_PREFIX/bin/python -m impact_forecasting_warning.pipelines.wind_impact_forecast --n-days 5 >> "$LOG_FILE" 2>&1

Make the script executable and add to crontab:

.. code-block:: console

    $ chmod +x wind_forecast_cron.sh
    $ crontab -e
    
    # Add line to run daily at 6 AM:
    0 6 * * * /path/to/wind_forecast_cron.sh

Run Tests
---------

.. code-block:: console

    $ conda activate climada_env
    $ poetry run pytest

Or use the conda Python explicitly:

.. code-block:: console

    $ $CONDA_PREFIX/bin/python -m pytest

Run Quality Tools
-----------------

.. code-block:: console

    $ conda activate climada_env
    $ poetry run pylint impact_forecasting_warning
    $ poetry run mypy impact_forecasting_warning

Generate Documentation
----------------------

.. code-block:: console

    $ conda activate climada_env
    $ poetry run sphinx-build doc doc/_build

Then open the index.html file generated in *doc/_build/*.

Build Wheels
------------

.. code-block:: console

    $ conda activate climada_env
    $ poetry build

Project Structure
=================

The project is organized into the following modules:

.. code-block:: text

    impact_forecasting_warning/
    ├── exposure/
    │   ├── exposure_creation.py     # Create CLIMADA Exposures from geodata
    │   └── exposure_data.py         # Load Swiss geodata (cantons, warning regions)
    ├── hazard/
    │   ├── weather_api.py           # Fetch weather forecasts from OGD API
    │   └── hazard_forecast.py       # Convert forecasts to CLIMADA HazardForecast
    ├── vulnerability/
    │   └── wind.py                  # CLIMADA impact functions definitions (wind only for now)
    ├── pipelines/
    │   └── wind_impact_forecast.py  # Main orchestration and pipeline execution (1 for now)
    └── visualization/
        ├── plots.py                 # Plot creation functions
        └── util_functions.py        # Aggregation and plotting utilities

**Module Responsibilities:**

* **exposure**: Geographic data handling and exposure creation for Switzerland
* **hazard**: Weather forecast fetching and conversion to CLIMADA objects
* **vulnerability**: Impact functions defining damage curves and warning levels
* **pipelines**: Orchestration layer connecting all modules, main entry point
* **visualization**: Plot generation and spatial aggregation utilities

Test Structure
--------------

Tests are organized into unit and integration tests:

.. code-block:: text

    test/
    ├── conftest.py                      # Shared pytest fixtures
    ├── unit/                            # Unit tests for individual modules
    │   ├── test_exposure.py             # Tests for exposure module
    │   ├── test_hazard.py               # Tests for hazard module
    │   └── test_vulnerability.py        # Tests for vulnerability module
    └── integration/                     # Integration tests
        ├── test_pipelines.py            # Pipeline orchestration tests
        └── test_visualization.py        # Visualization output tests

**Test Organization:**

* **Unit tests**: Test individual functions and classes in isolation with mocked dependencies
* **Integration tests**: Test complete workflows and inter-module interactions
* **Shared fixtures**: Common test data and mocks in ``conftest.py`` (HazardForecast, Exposures, GeoDataFrames, etc.)

Output Structure
----------------

Pipeline outputs are organized into separate directories:

.. code-block:: text

    results/
    ├── plots/              # Visualization outputs (JPEG, SVG)
    │   ├── *_histbin.svg                           # National impact histograms
    │   ├── *_canton_impact_map.jpeg                # Cantonal pie chart maps
    │   ├── *_warn_map.jpeg                         # Hazard-based warning maps
    │   ├── *_impact_warn_map_*.jpeg                # Impact-based warning maps
    │   ├── *_rel_impact_warn_map_*.jpeg            # Relative impact warning maps
    │   └── *_impact_map.jpeg                       # Continuous impact maps
    └── output_data/        # CSV data exports
        └── *_canton_medians.csv                    # Median impacts per canton

**Output Organization:**

* **plots/**: All visualizations (histograms, maps, charts) in JPEG and SVG formats
* **output_data/**: Quantitative results exported as CSV files for further analysis

Releasing
===============

* Adapt CHANGELOG.rst with release information
* Adapt ``doc/_static/switcher_config.json`` adding the new documentation URL for the release
* Create a new Release in the Github project