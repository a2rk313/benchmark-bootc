#!/bin/bash
set -eou pipefail

echo "=== 1. Installing System Dependencies via dnf5 ==="
dnf5 install -y --skip-unavailable \
    gdal gdal-devel proj proj-devel geos geos-devel \
    hdf5 hdf5-devel fftw fftw-devel openblas openblas-devel lapack blas \
    libpq-devel sqlite-devel netcdf-devel udunits2-devel gsl-devel \
    libtiff-devel libjpeg-turbo-devel git cmake wget curl

dnf5 clean all

echo "=== 2. Installing mise (version manager for Julia, Python) ==="
curl -LsSf https://astral.sh/mise/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

echo "=== 3. Installing asdf for R ==="
git clone https://github.com/asdf-vm/asdf.git ~/.asdf --branch v0.14.0
source ~/.asdf/asdf.sh

echo "=== 4. Installing Julia, Python, R via mise/asdf ==="
mise install julia 1.11.4
mise install python 3.13.0
asdf plugin add r || true
asdf install r 4.5.3
asdf global r 4.5.3

mise reshim

echo "=== 5. Installing Python Dependencies ==="
mise exec python -- pip install \
    numpy scipy pandas matplotlib scikit-learn \
    shapely pyproj fiona rasterio geopandas rioxarray xarray \
    psutil tqdm h5py

echo "=== 6. Installing R Dependencies ==="
mkdir -p /usr/share/doc/R/html

mise exec -- rscript -e "install.packages(c('terra', 'sf', 'data.table'), repos='https://cloud.r-project.org/', Ncpus=parallel::detectCores())"

echo "=== 7. Pre-installing Julia packages ==="
export PATH="$HOME/.local/share/mise/shims:$PATH"

julia -e 'using Pkg; Pkg.add([
    "BenchmarkTools", "CSV", "DataFrames", "SHA", "MAT", "JSON3",
    "NearestNeighbors", "LibGEOS", "Shapefile", "ArchGDAL", "GeoDataFrames"
])'

echo "=== Build script finished successfully! ==="