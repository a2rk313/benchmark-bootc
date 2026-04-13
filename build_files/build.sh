#!/bin/bash
set -euxo pipefail

dnf5 install -y R R-core R-core-devel python3 python3-pip

dnf5 install -y --skip-unavailable \
    gdal gdal-devel proj proj-devel geos geos-devel \
    hdf5 hdf5-devel fftw fftw-devel \
    openblas-openmp openblas-openmp-devel lapack blas \
    libpq-devel sqlite-devel netcdf-devel udunits2-devel gsl-devel \
    libtiff-devel libjpeg-turbo-devel git cmake

dnf5 clean all

rm -rf ~/.juliaup ~/.julia
curl -fsSL https://install.julialang.org | sh -s -- -y
export PATH="$HOME/.juliaup/bin:$PATH"
juliaup add julia-1.12
juliaup default julia-1.12

julia -e 'using Pkg; Pkg.add([
    "BenchmarkTools","CSV","DataFrames","SHA","MAT","JSON3",
    "NearestNeighbors","LibGEOS","Shapefile","ArchGDAL","GeoDataFrames"
])'

uv pip install --system \
    numpy scipy pandas matplotlib seaborn scikit-learn \
    shapely pyproj fiona rasterio geopandas rioxarray xarray \
    psutil tqdm h5py json3

R --no-save -e 'install.packages(c(
    "data.table","jsonlite","FNN","digest"
), repos="https://cloud.r-project.org")'

R --no-save -e 'install.packages(c(
    "terra","sf","stars","raster"
), repos="https://cloud.r-project.org")'

R --no-save -e 'install.packages("R.matlab", repos="https://cloud.r-project.org")' || true

COPY benchmarks/ /benchmarks/
COPY tools/ /tools/
COPY validation/ /validation/
COPY run_benchmarks.sh native_benchmark.sh run-container.sh /usr/local/bin/
COPY Project.toml Manifest.toml /benchmarks/

chmod +x /usr/local/bin/run_benchmarks.sh
chmod +x /usr/local/bin/native_benchmark.sh
chmod +x /usr/local/bin/run-container.sh