.. image:: https://img.shields.io/pypi/v/Open-Source-Template.svg
    :target: https://pypi.org/project/Open-Source-Template/

.. image:: https://img.shields.io/pypi/pyversions/Open-Source-Template.svg
    :target: https://pypi.org/project/Open-Source-Template/

.. image:: https://img.shields.io/pypi/l/Open-Source-Template.svg
    :target: https://pypi.org/project/Open-Source-Template/

.. image:: https://github.com/MeteoSwiss/Open-Source-Template/actions/workflows/github-code-scanning/codeql/badge.svg
    :target: https://github.com/MeteoSwiss/Open-Source-Template/actions/workflows/github-code-scanning/codeql

.. image:: https://github.com/MeteoSwiss/Open-Source-Template/actions/workflows/CI_test.yaml/badge.svg
    :target: https://github.com/MeteoSwiss/Open-Source-Template/actions/workflows/CI_test.yaml

.. image:: https://github.com/MeteoSwiss/Open-Source-Template/actions/workflows/CI_publish_dev_documentation.yaml/badge.svg
    :target: https://github.com/MeteoSwiss/Open-Source-Template/actions/workflows/CI_publish_dev_documentation.yaml

===============
Getting Started
===============

A demo for the OSS template at MeteoSwiss.

The template can be use as an example how to configure MeteoSwiss Github projects.

It uses:

* Github actions to execute the CI/CD pipelines
* Github pages to host the documentation
* PyPI to publish the python packages

Project Structure
-----------------

The project is organized into the following modules:

.. code-block:: text

    impact_forecasting_warning/
    ├── exposure/
    │   ├── exposure_creation.py    # Create LitPop and elevation-based exposures
    │   └── exposure_data.py         # Load Swiss geodata (cantons, warning regions)
    ├── hazard/
    │   ├── weather_api.py           # Fetch weather forecasts from OGD API
    │   └── hazard_forecast.py       # Convert forecasts to CLIMADA HazardForecast
    ├── vulnerability/
    │   └── wind.py                  # Wind impact functions (Schwierz, Welker, warnings)
    ├── pipelines/
    │   └── wind_impact_forecast.py  # Main orchestration and pipeline execution
    └── visualization/
        ├── plots.py                 # 6 plot creation functions
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

Development Setup with Poetry
-----------------------------

Building the Project
''''''''''''''''''''
.. code-block:: console

    $ cd open-source-template
    $ poetry install

Run Tests
'''''''''

.. code-block:: console

    $ poetry run pytest

Run Quality Tools
'''''''''''''''''

.. code-block:: console

    $ poetry run pylint open_source_template
    $ poetry run mypy open_source_template

Generate Documentation
''''''''''''''''''''''

.. code-block:: console

    $ poetry run sphinx-build doc doc/_build

Then open the index.html file generated in *open-source-template/doc/_build/*.

Build wheels
''''''''''''

.. code-block:: console

    $ poetry build

Using the Library
-----------------

To install open-source-template in your project, run this command in your terminal:

.. code-block:: console

    $ poetry add open-source-template

You can then use the library in your project through

    import open_source_template

Releasing
---------

* Adapt CHANGELOG.rst with release information
* Adapt ``doc/_static/switcher_config.json`` adding the new documentation URL for the release
* Create a new Release in the Github project