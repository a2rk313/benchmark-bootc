#!/bin/bash
set -eou pipefail

echo "=== 1. Installing System Dependencies via dnf5 ==="
dnf5 install -y --skip-unavailable \
    python3 python3-pip \
    R R-core R-core-devel \
    gdal gdal-devel proj proj-devel geos geos-devel \
    hdf5 hdf5-devel fftw fftw-devel openblas openblas-devel lapack blas \
    libpq-devel sqlite-devel netcdf-devel udunits2-devel gsl-devel \
    libtiff-devel libjpeg-turbo-devel git cmake wget curl tar gzip \
    hyperfine time

dnf5 clean all

echo "=== 2. Installing 'uv' Package Manager ==="
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

echo "=== 3. Installing Python Dependencies ==="
uv pip install --system \
    numpy scipy pandas matplotlib scikit-learn \
    shapely pyproj fiona rasterio geopandas rioxarray xarray \
    psutil tqdm h5py

echo "=== 4. Installing Julia (Architecture Aware) ==="
JULIA_VERSION="1.12.0"
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

mkdir -p /opt/julia
tar -xzf /tmp/julia.tar.gz -C /opt/julia --strip-components=1
ln -s /opt/julia/bin/julia /usr/local/bin/julia
julia --version

echo "=== 5. Installing R Dependencies ==="
mkdir -p /usr/share/doc/R/html

Rscript -e "install.packages(c('terra', 'sf', 'data.table'), repos='https://cloud.r-project.org/', Ncpus=parallel::detectCores())"

echo "=== Build script finished successfully! ==="