#!/bin/bash
set -euo pipefail

# DEBUG: Log all commands for troubleshooting
export PS4='+ ${BASH_SOURCE}:${LINENO}: '
set -x

# ==============================================================================
# THE OSTREE MAGIC FIX
# ==============================================================================
mkdir -p /var/roothome

echo "=== 1. Installing System Dependencies via dnf5 ==="
dnf5 install -y --skip-unavailable --setopt=install_weak_deps=False \
    python3 python3-pip python3-devel \
    R-core R-core-devel \
    gdal gdal-devel proj proj-devel geos geos-devel \
    hdf5 hdf5-devel fftw fftw-devel openblas openblas-devel lapack blas \
    libpq-devel sqlite-devel netcdf-devel udunits2-devel gsl-devel \
    libtiff-devel libjpeg-turbo-devel git cmake wget curl tar gzip \
    time hyperfine spatialindex spatialindex-devel \
    numactl kernel-tools \
    gcc-c++ libcurl-devel libxml2-devel openssl-devel \
    readline-devel bzip2-devel xz-devel zlib-devel \
    pcre2-devel sqlite-devel \
    libarrow-devel \
    openmpi-devel \
    pugixml-devel \
    tiledb-devel \
    python3-setuptools python3-wheel

dnf5 clean all
rm -rf /var/cache/libdnf5/*

echo "=== 2. Installing 'uv' Package Manager (Pinned v0.6.4) ==="
ARCH=$(uname -m)
UV_VERSION="0.6.4"
if [ "$ARCH" = "x86_64" ]; then
    UV_ARCH="x86_64-unknown-linux-gnu"
elif [ "$ARCH" = "aarch64" ]; then
    UV_ARCH="aarch64-unknown-linux-gnu"
else
    echo "Unsupported architecture for uv: $ARCH"
    exit 1
fi

curl -LsSf "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz" | tar -xz -C /usr/bin --strip-components=1 "uv-${UV_ARCH}/uv" "uv-${UV_ARCH}/uvx"

echo "=== 3. Installing Python Dependencies ==="
export UV_CACHE_DIR="/tmp/uv-cache"
# Use --no-build-isolation to avoid pip trying to build dependencies separately
uv pip install --system --prefix=/usr --no-cache --no-build-isolation \
    setuptools wheel \
    numpy scipy pandas matplotlib seaborn scikit-learn \
    shapely pyproj fiona rasterio geopandas rioxarray xarray \
    psutil tqdm h5py \
    || { echo "Python installation failed"; exit 1; }

echo "=== 4. Installing Julia ==="
JULIA_VERSION="1.12.6"
if [ "$ARCH" = "x86_64" ]; then
    JULIA_ARCH="x64"; JULIA_TAR_ARCH="x86_64"
elif [ "$ARCH" = "aarch64" ]; then
    JULIA_ARCH="aarch64"; JULIA_TAR_ARCH="aarch64"
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi

JULIA_MINOR=$(echo "$JULIA_VERSION" | cut -d. -f1,2)
echo "Fetching Julia $JULIA_VERSION for $JULIA_ARCH..."
curl -fsSL "https://julialang-s3.julialang.org/bin/linux/${JULIA_ARCH}/${JULIA_MINOR}/julia-${JULIA_VERSION}-linux-${JULIA_TAR_ARCH}.tar.gz" -o /tmp/julia.tar.gz

mkdir -p /usr/lib/julia
tar -xzf /tmp/julia.tar.gz -C /usr/lib/julia --strip-components=1
ln -s /usr/lib/julia/bin/julia /usr/bin/julia
rm -f /tmp/julia.tar.gz
echo "Julia installed successfully"

echo "=== 5. Installing R Dependencies ==="
mkdir -p /usr/share/doc/R/html
echo "CXX14FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site
echo "CXX17FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site
echo "CXX20FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site

# Ensure R uses the same OpenBLAS backend as everyone else via FlexiBLAS
if command -v flexiblas &> /dev/null; then
    flexiblas set OPENBLAS
fi

Rscript -e "install.packages(c('terra', 'sf', 'data.table', 'R.matlab', 'FNN', 'jsonlite', 'digest'), lib='/usr/lib64/R/library', repos='https://cloud.r-project.org/', Ncpus=parallel::detectCores(), clean=TRUE)"

echo "=== 6. Pre-installing Julia packages globally ==="
# Move Julia depot to /var/lib/julia/depot for bootc persistence
export JULIA_DEPOT_PATH="/var/lib/julia/depot"
export JULIA_NUM_THREADS=1  # Single thread for build stability
mkdir -p "$JULIA_DEPOT_PATH"
# Symlink for standard location visibility
mkdir -p /usr/share/julia
ln -sf "$JULIA_DEPOT_PATH" /usr/share/julia/depot

# High Priority: Add memory check before precompilation
TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
if [ "$TOTAL_MEM" -lt 4000 ]; then
    echo "⚠ WARNING: Less than 4GB RAM detected ($TOTAL_MEM MB). Julia precompilation may fail."
fi

# Install packages with error handling and retry logic
echo "Installing Julia packages (with retry logic)..."
julia --threads=1 -e '
using Pkg
pkgs = ["BenchmarkTools", "CSV", "DataFrames", "SHA", "MAT", "JSON3", 
        "NearestNeighbors", "LibGEOS", "Shapefile", "ArchGDAL", "GeoDataFrames"]
Pkg.add(pkgs)
'

# Warmup: Actually load the heavy packages to trigger binary cache generation
echo "Triggering deep precompilation (Warmup)..."
julia --threads=1 -e 'using ArchGDAL, GeoDataFrames, LibGEOS, DataFrames; println("Heavy GIS packages loaded")' || { echo "JuliaWarmup failed"; exit 1; }
julia --threads=1 -e 'using Pkg; Pkg.precompile()' || { echo "Julia precompile failed"; exit 1; }

# CLEANUP: Only remove transient data, KEEP registries/, compiled/ and artifacts/
# registries/ is needed for runtime package resolution
# compiled/ contains the .ji and .so files
# artifacts/ contains the underlying C++ shared libraries (GDAL, GEOS, etc.)
echo "Cleaning up build artifacts..."
rm -rf "$JULIA_DEPOT_PATH/scratchspaces"/*
rm -rf "$JULIA_DEPOT_PATH/logs"/*

echo "=== 7. Final Deep Clean ==="
rm -rf /tmp/*
rm -rf /var/roothome/.cache/*

# Verify installations
echo "=== Verifying installations ==="
python3 -c "import numpy; print(f'NumPy {numpy.__version__} OK')"
julia -e 'println("Julia OK")'
Rscript -e 'cat("R OK\n")'

echo "=== Build script finished successfully! ==="
