#!/bin/bash
# Fail on any error, undefined variable, or pipeline failure
set -eou pipefail

# ==============================================================================
# THE OSTREE MAGIC FIX:
# In Silverblue, /root is a symlink to /var/roothome. During a container build,
# /var is empty, making /root a broken symlink. This causes ANY tool that writes
# to ~/.cache, ~/.config, or ~/.local to instantly crash.
# Creating this directory makes the symlink valid, acting as a temporary
# scratchpad that OSTree will automatically discard in the final image.
# ==============================================================================
mkdir -p /var/roothome

echo "=== 1. Installing System Dependencies via dnf5 ==="
dnf5 install -y --skip-unavailable \
    python3 python3-pip python3-devel \
    R-core R-core-devel \
    gdal gdal-devel proj proj-devel geos geos-devel \
    hdf5 hdf5-devel fftw fftw-devel openblas openblas-devel lapack blas \
    libpq-devel sqlite-devel netcdf-devel udunits2-devel gsl-devel \
    libtiff-devel libjpeg-turbo-devel git cmake wget curl tar gzip

dnf5 clean all

echo "=== 2. Installing 'uv' Package Manager ==="
# We bypass the installer script entirely and grab the static binaries.
# This is much safer for immutable container builds.
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    UV_ARCH="x86_64-unknown-linux-gnu"
elif [ "$ARCH" = "aarch64" ]; then
    UV_ARCH="aarch64-unknown-linux-gnu"
else
    echo "Unsupported architecture for uv: $ARCH"
    exit 1
fi

echo "Downloading uv for $UV_ARCH..."
curl -LsSf "https://github.com/astral-sh/uv/releases/latest/download/uv-${UV_ARCH}.tar.gz" | tar -xz -C /usr/bin --strip-components=1 "uv-${UV_ARCH}/uv" "uv-${UV_ARCH}/uvx"

echo "=== 3. Installing Python Dependencies ==="
# Force uv to use /tmp for caching to avoid any lingering permission issues
export UV_CACHE_DIR="/tmp/uv-cache"

# Use --prefix=/usr to force Python packages into the immutable OS tree
uv pip install --system --prefix=/usr \
    numpy scipy pandas matplotlib scikit-learn \
    shapely pyproj fiona rasterio geopandas rioxarray xarray \
    psutil tqdm h5py

echo "=== 4. Installing Julia (Architecture Aware) ==="
JULIA_VERSION="1.11.4"

if [ "$ARCH" = "x86_64" ]; then
    JULIA_ARCH="x64"
    JULIA_TAR_ARCH="x86_64"
elif [ "$ARCH" = "aarch64" ]; then
    JULIA_ARCH="aarch64"
    JULIA_TAR_ARCH="aarch64"
fi

JULIA_MINOR=$(echo "$JULIA_VERSION" | cut -d. -f1,2)

echo "Downloading Julia ${JULIA_VERSION} for ${ARCH}..."
curl -fsSL "https://julialang-s3.julialang.org/bin/linux/${JULIA_ARCH}/${JULIA_MINOR}/julia-${JULIA_VERSION}-linux-${JULIA_TAR_ARCH}.tar.gz" -o /tmp/julia.tar.gz

# Extract directly into the immutable /usr/lib and symlink to /usr/bin
mkdir -p /usr/lib/julia
tar -xzf /tmp/julia.tar.gz -C /usr/lib/julia --strip-components=1
ln -s /usr/lib/julia/bin/julia /usr/bin/julia
rm /tmp/julia.tar.gz

echo "=== 5. Installing R Dependencies ==="
mkdir -p /usr/share/doc/R/html

# Force R packages to install into /usr/lib64/R/library
Rscript -e "install.packages(c('terra', 'sf', 'data.table'), lib='/usr/lib64/R/library', repos='https://cloud.r-project.org/', Ncpus=parallel::detectCores())"

echo "=== 6. Pre-installing Julia packages ==="
# Redirect Julia's package depot to a global, immutable system directory
export JULIA_DEPOT_PATH="/usr/share/julia/depot"
mkdir -p $JULIA_DEPOT_PATH

julia -e 'using Pkg; Pkg.add([
    "BenchmarkTools", "CSV", "DataFrames", "SHA", "MAT", "JSON3",
    "NearestNeighbors", "LibGEOS", "Shapefile", "ArchGDAL", "GeoDataFrames"
])'

# Precompile to bake binaries into the image and save runtime during benchmarks
julia -e 'using Pkg; Pkg.precompile()'

echo "=== Build script finished successfully! ==="
