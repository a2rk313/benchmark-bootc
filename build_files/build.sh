#!/bin/bash
# Fail on any error, undefined variable, or pipeline failure
set -eou pipefail

echo "=== 1. Installing System Dependencies via dnf5 ==="
dnf5 install -y --skip-unavailable \
    python3 python3-pip python3-devel \
    R-core R-core-devel \
    gdal gdal-devel proj proj-devel geos geos-devel \
    hdf5 hdf5-devel fftw fftw-devel openblas openblas-devel lapack blas \
    libpq-devel sqlite-devel netcdf-devel udunits2-devel gsl-devel \
    libtiff-devel libjpeg-turbo-devel git cmake wget curl

# Clean cache to reduce final image size
dnf5 clean all

echo "=== 2. Installing 'uv' Package Manager ==="
# Force the uv binary directly into the immutable /usr/bin directory
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/bin" sh

echo "=== 3. Installing Python Dependencies ==="
# Use --prefix=/usr to force Python packages into the immutable OS tree 
# rather than the ephemeral /usr/local symlink.
uv pip install --system --prefix=/usr \
    numpy scipy pandas matplotlib scikit-learn \
    shapely pyproj fiona rasterio geopandas rioxarray xarray \
    psutil tqdm h5py

echo "=== 4. Installing Julia (Architecture Aware) ==="
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

# Extract directly into the immutable /usr/lib and symlink to /usr/bin
mkdir -p /usr/lib/julia
tar -xzf /tmp/julia.tar.gz -C /usr/lib/julia --strip-components=1
ln -s /usr/lib/julia/bin/julia /usr/bin/julia
rm /tmp/julia.tar.gz

echo "=== 5. Installing R Dependencies ==="
mkdir -p /usr/share/doc/R/html

# Force R packages to install into /usr/lib64/R/library instead of /usr/local
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
