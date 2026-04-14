#!/bin/bash
# Fail on any error, undefined variable, or pipeline failure
set -eou pipefail

echo "=== 1. Installing System Dependencies via dnf5 ==="
# We add python3, python3-devel, R-core, and R-core-devel directly via DNF.
# Fedora 43 (which you are using) already ships with R 4.5+ and Python 3.13+ natively.
dnf5 install -y --skip-unavailable \
    python3 python3-pip python3-devel \
    R-core R-core-devel \
    gdal gdal-devel proj proj-devel geos geos-devel \
    hdf5 hdf5-devel fftw fftw-devel openblas openblas-devel lapack blas \
    libpq-devel sqlite-devel netcdf-devel udunits2-devel gsl-devel \
    libtiff-devel libjpeg-turbo-devel git cmake wget curl

# Clean up cache to keep the final container image small
dnf5 clean all

echo "=== 2. Installing 'uv' for Python Package Management ==="
# Instead of mise, we install uv system-wide via pip
pip3 install uv

echo "=== 3. Installing Python Dependencies ==="
# uv will install these packages globally into the system python environment
uv pip install --system \
    numpy scipy pandas matplotlib scikit-learn \
    shapely pyproj fiona rasterio geopandas rioxarray xarray \
    psutil tqdm h5py

echo "=== 4. Installing Julia (Architecture Aware) ==="
# The container-native way to install Julia is pulling the official tarball 
# and placing it in /opt (accessible to all users, avoiding ~/).
JULIA_VERSION="1.11.4"
ARCH=$(uname -m)

if [ "$ARCH" = "x86_64" ]; then
    JULIA_ARCH="x64"
    JULIA_TAR_ARCH="x86_64"
elif [ "$ARCH" = "aarch64" ]; then
    JULIA_ARCH="aarch64"
    JULIA_TAR_ARCH="aarch64"
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi

JULIA_MINOR=$(echo "$JULIA_VERSION" | cut -d. -f1,2)

echo "Downloading Julia ${JULIA_VERSION} for ${ARCH}..."
curl -fsSL "https://julialang-s3.julialang.org/bin/linux/${JULIA_ARCH}/${JULIA_MINOR}/julia-${JULIA_VERSION}-linux-${JULIA_TAR_ARCH}.tar.gz" -o /tmp/julia.tar.gz

# Extract to /opt/julia and symlink so it is in the global PATH
mkdir -p /opt/julia
tar -xzf /tmp/julia.tar.gz -C /opt/julia --strip-components=1
ln -s /opt/julia/bin/julia /usr/local/bin/julia
rm /tmp/julia.tar.gz

echo "=== 5. Installing R Dependencies ==="
# Ensure documentation folder exists to prevent R install warnings
mkdir -p /usr/share/doc/R/html

# Use system Rscript to install globally
Rscript -e "install.packages(c('terra', 'sf', 'data.table'), repos='https://cloud.r-project.org/', Ncpus=parallel::detectCores())"

echo "=== 6. Pre-installing Julia packages ==="
# CRITICAL: We redirect Julia's package depot to a global system directory.
# This prevents Julia from trying to write to the broken /root/.julia symlink during the build.
export JULIA_DEPOT_PATH="/usr/local/share/julia"
mkdir -p $JULIA_DEPOT_PATH

# Install the packages into the global depot
julia -e 'using Pkg; Pkg.add([
    "BenchmarkTools", "CSV", "DataFrames", "SHA", "MAT", "JSON3",
    "NearestNeighbors", "LibGEOS", "Shapefile", "ArchGDAL", "GeoDataFrames"
])'

# Precompile to save time during actual benchmarking runs
julia -e 'using Pkg; Pkg.precompile()'

echo "=== Build script finished successfully! ==="
