#!/bin/bash

set -euxo pipefail

# =============================================================================
# Benchmark OS Build Script
# =============================================================================
# Installs R, Julia, Python and all GIS/benchmarking packages
# Base: Fedora 43 / Silverblue-main
# =============================================================================

### Install system packages via dnf5

# R (4.5.x from Fedora repos)
dnf5 install -y R R-core R-core-devel

# Julia (1.11.x from Fedora repos)
dnf5 install -y julia

# Python (3.14 in Fedora 43)
dnf5 install -y python3 python3-pip

# System GIS libraries
dnf5 install -y \
    gdal gdal-devel \
    proj proj-devel \
    geos geos-devel \
    hdf5 hdf5-devel \
    fftw fftw-devel \
    openblas openblas-devel \
    lapack blas \
    gcc gcc-c++ make cmake \
    git curl wget htop bc

# Cleanup
dnf5 clean all

### Install R packages

R --no-save -e 'install.packages(c(
    "terra",
    "sf",
    "stars",
    "raster",
    "data.table",
    "jsonlite",
    "FNN",
    "digest",
    "R.matlab"
), repos="https://cloud.r-project.org")'

### Install Julia packages

julia -e 'using Pkg; Pkg.add([
    "BenchmarkTools",
    "CSV",
    "DataFrames",
    "SHA",
    "MAT",
    "JSON3",
    "NearestNeighbors",
    "LibGEOS",
    "Shapefile",
    "ArchGDAL",
    "GeoDataFrames"
])'

### Install Python packages via pip

python3 -m pip install --break-system-packages \
    numpy scipy pandas matplotlib seaborn scikit-learn \
    shapely pyproj fiona rasterio geopandas rioxarray xarray \
    psutil tqdm h5py json3

### Copy benchmark files to image

# Copy benchmarks
COPY benchmarks/ /benchmarks/

# Copy tools
COPY tools/ /tools/

# Copy validation scripts
COPY validation/ /validation/

# Copy runner scripts
COPY run_benchmarks.sh /usr/local/bin/
COPY native_benchmark.sh /usr/local/bin/
COPY run-container.sh /usr/local/bin/

# Copy Julia/R project files
COPY Project.toml Manifest.toml /benchmarks/

# Make scripts executable
chmod +x /usr/local/bin/run_benchmarks.sh
chmod +x /usr/local/bin/native_benchmark.sh
chmod +x /usr/local/bin/run-container.sh
