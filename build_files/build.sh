#!/bin/bash
# Fail on any error, undefined variable, or pipeline failure
set -eou pipefail

# ==============================================================================
# THE OSTREE MAGIC FIX
# Fixes broken /root symlink allowing tools to write temporary cache/configs.
# ==============================================================================
mkdir -p /var/roothome

echo "=== 1. Installing System Dependencies via dnf5 ==="
# --setopt=install_weak_deps=False is MANDATORY.
# It stops R and GDAL from installing ~4GB of LaTeX and Java onto your Silverblue desktop.
dnf5 install -y --skip-unavailable --setopt=install_weak_deps=False \
    python3 python3-pip python3-devel \
    R-core R-core-devel \
    gdal gdal-devel proj proj-devel geos geos-devel \
    hdf5 hdf5-devel fftw fftw-devel openblas openblas-devel lapack blas \
    libpq-devel sqlite-devel netcdf-devel udunits2-devel gsl-devel \
    libtiff-devel libjpeg-turbo-devel git cmake wget curl tar gzip \
    time hyperfine spatialindex spatialindex-devel

# Aggressive DNF cleanup
dnf5 clean all
rm -rf /var/cache/libdnf5/*

echo "=== 2. Installing 'uv' Package Manager ==="
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
# Extract static binaries directly into the immutable /usr/bin directory
curl -LsSf "https://github.com/astral-sh/uv/releases/latest/download/uv-${UV_ARCH}.tar.gz" | tar -xz -C /usr/bin --strip-components=1 "uv-${UV_ARCH}/uv" "uv-${UV_ARCH}/uvx"

echo "=== 3. Installing Python Dependencies ==="
export UV_CACHE_DIR="/tmp/uv-cache"
# Use --no-cache to prevent storing downloaded wheels, saving space
uv pip install --system --prefix=/usr --no-cache \
    numpy scipy pandas matplotlib seaborn scikit-learn \
    shapely pyproj fiona rasterio geopandas rioxarray xarray \
    psutil tqdm h5py

echo "=== 4. Installing Julia (Architecture Aware) ==="
JULIA_VERSION="1.12.6"

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
rm -f /tmp/julia.tar.gz

echo "=== 5. Installing R Dependencies ==="
mkdir -p /usr/share/doc/R/html

# GCC 15 / Fedora 43 Fix for R's 's2' package compilation
echo "CXX14FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site
echo "CXX17FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site
echo "CXX20FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site

# Force R packages to install into /usr/lib64/R/library and clean downloaded tarballs immediately
Rscript -e "install.packages(c('terra', 'sf', 'data.table', 'R.matlab', 'FNN', 'jsonlite', 'digest'), lib='/usr/lib64/R/library', repos='https://cloud.r-project.org/', Ncpus=parallel::detectCores(), clean=TRUE)"

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

# Clean up Julia's downloaded archives (keeps binaries, drops zip files)
rm -rf /usr/share/julia/depot/packages/*/
julia -e 'using Pkg, Dates; Pkg.gc(collect_delay=Day(0))'

echo "=== 7. Final Deep Clean ==="
# Wipe out all temporary caches that might bloat the layer
rm -rf /tmp/*
rm -rf /var/roothome/.cache/*

echo "=== Build script finished successfully! ==="
