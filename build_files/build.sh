#!/bin/bash
set -euxo pipefail

dnf5 install -y \
    R R-core R-core-devel \
    python3 python3-pip \
    curl tar gzip

dnf5 install -y --skip-unavailable \
    gdal gdal-devel proj proj-devel geos geos-devel \
    hdf5 hdf5-devel fftw fftw-devel \
    openblas-openmp openblas-openmp-devel lapack blas \
    libpq-devel sqlite-devel netcdf-devel udunits2-devel gsl-devel \
    libtiff-devel libjpeg-turbo-devel git cmake

dnf5 clean all

JULIA_VERSION="1.12.0"
JULIA_DIR="/opt/julia"
JULIA_DEPOT="/opt/julia-depot"

curl -fsSL \
  "https://julialang-s3.julialang.org/bin/linux/x64/1.12/julia-${JULIA_VERSION}-linux-x86_64.tar.gz" \
  -o /tmp/julia.tar.gz

mkdir -p "${JULIA_DIR}"
tar -xzf /tmp/julia.tar.gz -C "${JULIA_DIR}" --strip-components=1
rm -f /tmp/julia.tar.gz

ln -sf "${JULIA_DIR}/bin/julia" /usr/local/bin/julia

export JULIA_DEPOT_PATH="${JULIA_DEPOT}"
mkdir -p "${JULIA_DEPOT}"

julia --project=/benchmarks -e '
using Pkg
Pkg.instantiate()
Pkg.precompile()
'

uv pip install --system \
    numpy scipy pandas matplotlib scikit-learn \
    shapely pyproj fiona rasterio geopandas rioxarray xarray \
    psutil tqdm h5py

R --no-save -e 'install.packages(c(
    "data.table","jsonlite","FNN","digest",
    "terra","sf","stars","raster"
), repos="https://cloud.r-project.org")'

R --no-save -e 'install.packages(
    "R.matlab",
    repos="https://cloud.r-project.org"
)' || true