#!/bin/bash
set -eou pipefail

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
    numactl kernel-tools

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

curl -LsSf "https://github.com/astral-sh/uv/releases/latest/download/uv-${UV_ARCH}.tar.gz" | tar -xz -C /usr/bin --strip-components=1 "uv-${UV_ARCH}/uv" "uv-${UV_ARCH}/uvx"

echo "=== 3. Installing Python Dependencies ==="
export UV_CACHE_DIR="/tmp/uv-cache"
uv pip install --system --prefix=/usr --no-cache \
    numpy scipy pandas matplotlib seaborn scikit-learn \
    shapely pyproj fiona rasterio geopandas rioxarray xarray \
    psutil tqdm h5py

echo "=== 4. Installing Julia ==="
JULIA_VERSION="1.12.6"
if [ "$ARCH" = "x86_64" ]; then
    JULIA_ARCH="x64"; JULIA_TAR_ARCH="x86_64"
elif [ "$ARCH" = "aarch64" ]; then
    JULIA_ARCH="aarch64"; JULIA_TAR_ARCH="aarch64"
fi

JULIA_MINOR=$(echo "$JULIA_VERSION" | cut -d. -f1,2)
curl -fsSL "https://julialang-s3.julialang.org/bin/linux/${JULIA_ARCH}/${JULIA_MINOR}/julia-${JULIA_VERSION}-linux-${JULIA_TAR_ARCH}.tar.gz" -o /tmp/julia.tar.gz

mkdir -p /usr/lib/julia
tar -xzf /tmp/julia.tar.gz -C /usr/lib/julia --strip-components=1
ln -s /usr/lib/julia/bin/julia /usr/bin/julia
rm -f /tmp/julia.tar.gz

echo "=== 5. Installing R Dependencies ==="
mkdir -p /usr/share/doc/R/html
echo "CXX14FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site
echo "CXX17FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site
echo "CXX20FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site

Rscript -e "install.packages(c('terra', 'sf', 'data.table', 'R.matlab', 'FNN', 'jsonlite', 'digest'), lib='/usr/lib64/R/library', repos='https://cloud.r-project.org/', Ncpus=parallel::detectCores(), clean=TRUE)"

echo "=== 6. Pre-installing Julia packages globally ==="
export JULIA_DEPOT_PATH="/usr/share/julia/depot"
mkdir -p $JULIA_DEPOT_PATH

# Install globally and force precompilation of the entire dependency graph
julia -e 'using Pkg; Pkg.add([
    "BenchmarkTools", "CSV", "DataFrames", "SHA", "MAT", "JSON3",
    "NearestNeighbors", "LibGEOS", "Shapefile", "ArchGDAL", "GeoDataFrames"
])'

# Warmup: Actually load the heavy packages to trigger binary cache generation
echo "Triggering deep precompilation (Warmup)..."
julia -e 'using ArchGDAL, GeoDataFrames, LibGEOS, DataFrames; println("✓ Heavy GIS packages loaded successfully")'
julia -e 'using Pkg; Pkg.precompile()'

# CLEANUP: Only remove transient data, KEEP registries/, compiled/ and artifacts/
# registries/ is needed for runtime package resolution
# compiled/ contains the .ji and .so files
# artifacts/ contains the underlying C++ shared libraries (GDAL, GEOS, etc.)
rm -rf $JULIA_DEPOT_PATH/scratchspaces/*
rm -rf $JULIA_DEPOT_PATH/logs/*
julia -e 'using Pkg, Dates; Pkg.gc(collect_delay=Day(0))'

echo "=== 7. Final Deep Clean ==="
rm -rf /tmp/*
rm -rf /var/roothome/.cache/*

echo "=== Build script finished successfully! ==="
