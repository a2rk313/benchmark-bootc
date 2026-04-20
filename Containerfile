# ==============================================================================
# STAGE 1: THE HEAVY BUILDER
# Uses standard Fedora 43. No read-only filesystem.
# ==============================================================================
FROM registry.fedoraproject.org/fedora:43 AS builder

# Install compilers and development headers
RUN dnf5 install -y \
    gcc gcc-c++ make cmake git curl wget tar \
    python3 python3-pip python3-devel \
    R-core R-core-devel \
    gdal-devel proj-devel geos-devel \
    hdf5-devel fftw-devel openblas-devel sqlite-devel \
    libtiff-devel libjpeg-turbo-devel spatialindex-devel

# Install uv and Python dependencies (using version ranges for compatibility)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Use uv to install Python packages
# We specify minimum versions to ensure required features, but let uv pick the exact patch
RUN uv pip install --system --target=/opt/python-deps \
    "numpy>=2.2" \
    "scipy>=1.15" \
    "pandas>=2.2" \
    "matplotlib>=3.9" \
    "seaborn>=0.13" \
    "scikit-learn>=1.6" \
    "shapely>=2.0" \
    "pyproj>=3.6" \
    "fiona>=1.10" \
    "rasterio>=1.4" \
    "geopandas>=1.0" \
    "rioxarray>=0.18" \
    "xarray>=2024.1" \
    "psutil>=6.0" \
    "tqdm>=4.66" \
    "h5py>=3.11"

# Install R dependencies
RUN mkdir -p /opt/R-deps && \
    echo "CXX14FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site && \
    echo "CXX17FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site && \
    echo "CXX20FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site && \
    Rscript -e "install.packages(c('terra', 'sf', 'data.table', 'R.matlab', 'FNN', 'jsonlite', 'digest'), lib='/opt/R-deps', repos='https://cloud.r-project.org/', Ncpus=parallel::detectCores())"

# Install Julia 1.11.9 and precompile packages
RUN curl -fsSL "https://julialang-s3.julialang.org/bin/linux/x64/1.11/julia-1.11.9-linux-x86_64.tar.gz" | tar -xz -C /opt && \
    mv /opt/julia-* /opt/julia

ENV JULIA_DEPOT_PATH="/opt/julia-depot"
ENV PATH="/opt/julia/bin:$PATH"
RUN julia -e 'using Pkg; Pkg.add(["BenchmarkTools", "CSV", "DataFrames", "SHA", "MAT", "JSON3", "NearestNeighbors", "LibGEOS", "Shapefile", "ArchGDAL", "GeoDataFrames"])' && \
    julia -e 'using Pkg; Pkg.precompile()' && \
    julia -e 'using Pkg, Dates; Pkg.gc(collect_delay=Day(0))' && \
    rm -rf /opt/julia-depot/packages/*/ && \
    rm -rf /opt/julia-depot/artifacts/*/

# ==============================================================================
# STAGE 2: THE FINAL BOOTC OS (SILVERBLUE)
# ==============================================================================
FROM quay.io/fedora/fedora-kinoite:43

# Set environment variables
ENV JULIA_NUM_THREADS=8 \
    OPENBLAS_NUM_THREADS=8 \
    OMP_NUM_THREADS=8 \
    R_MAX_VSIZE=16G \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR \
    GDAL_CACHEMAX=512 \
    NPY_BLAS_ORDER=openblas \
    NPY_LAPACK_ORDER=openblas \
    JULIA_DEPOT_PATH="/usr/share/julia/depot" \
    PYTHONPATH="/usr/local/lib/python-deps" \
    PATH="/usr/lib/julia/bin:$PATH"

# Install ONLY runtime dependencies
RUN dnf5 install -y --skip-unavailable --setopt=install_weak_deps=False \
    python3 R-core gdal proj geos hdf5 fftw openblas \
    sqlite netcdf udunits2 gsl libtiff libjpeg-turbo \
    time hyperfine spatialindex git && \
    dnf5 clean all && \
    rm -rf /var/cache/libdnf5/*

# Transplant compiled artifacts from builder stage
COPY --from=builder /opt/python-deps /usr/local/lib/python-deps
COPY --from=builder /opt/R-deps /usr/lib64/R/library
COPY --from=builder /opt/julia /usr/lib/julia
COPY --from=builder /opt/julia-depot /usr/share/julia/depot

# Verify critical components
RUN python3 -c "import numpy, geopandas; print('Python OK')"
RUN /usr/lib/julia/bin/julia -e 'using BenchmarkTools, ArchGDAL; println("Julia OK")'
RUN Rscript -e "library(terra); library(data.table); cat('R OK\n')"

# Create bootc marker file for detection
RUN echo "benchmark-bootc v1.0" > /etc/benchmark-bootc-release

# Copy first-boot setup scripts
COPY ./firstboot/first-boot-setup.sh /usr/local/bin/first-boot-setup.sh
COPY ./firstboot/benchmark-firstboot.service /etc/systemd/system/benchmark-firstboot.service

RUN chmod +x /usr/local/bin/first-boot-setup.sh && \
    systemctl enable benchmark-firstboot.service

# Create mutable runtime directories
RUN mkdir -p /var/data && ln -s /var/data /data && \
    mkdir -p /var/benchmarks && ln -s /var/benchmarks /benchmarks
