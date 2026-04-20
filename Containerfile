# ==============================================================================
# STAGE 1: THE HEAVY BUILDER
# ==============================================================================
FROM registry.fedoraproject.org/fedora:43 AS builder

# Install compilers and development headers
RUN dnf5 install -y \
    gcc gcc-c++ make cmake git curl wget tar \
    python3.13 python3.13-pip python3.13-devel \
    R-core R-core-devel \
    gdal-devel proj-devel geos-devel \
    hdf5-devel fftw-devel openblas-devel sqlite-devel \
    libtiff-devel libjpeg-turbo-devel spatialindex-devel

# Install uv and Python dependencies
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Use uv to install Python packages targeting Python 3.13
RUN uv pip install --system --python 3.13 --target=/opt/python-deps \
    "numpy>=2.2" "scipy>=1.15" "pandas>=2.2" "matplotlib>=3.9" \
    "seaborn>=0.13" "scikit-learn>=1.6" "shapely>=2.0" "pyproj>=3.6" \
    "fiona>=1.10" "rasterio>=1.4" "geopandas>=1.0" "rioxarray>=0.18" \
    "xarray>=2024.1" "psutil>=6.0" "tqdm>=4.66" "h5py>=3.11"

# Install R dependencies
RUN mkdir -p /opt/R-deps && \
    echo "CXX14FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site && \
    echo "CXX17FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site && \
    echo "CXX20FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site && \
    Rscript -e "install.packages(c('terra', 'sf', 'data.table', 'R.matlab', 'FNN', 'jsonlite', 'digest'), lib='/opt/R-deps', repos='https://cloud.r-project.org/', Ncpus=parallel::detectCores())"

# Install Julia 1.12.3 (Thesis expectation)
RUN curl -fsSL "https://julialang-s3.julialang.org/bin/linux/x64/1.12/julia-1.12.6-linux-x86_64.tar.gz" | tar -xz -C /opt && \
    mv /opt/julia-* /opt/julia

ENV JULIA_DEPOT_PATH="/opt/julia-depot"
ENV PATH="/opt/julia/bin:$PATH"
RUN julia -e 'using Pkg; Pkg.add(["BenchmarkTools", "CSV", "DataFrames", "SHA", "MAT", "JSON3", "NearestNeighbors", "LibGEOS", "Shapefile", "ArchGDAL", "GeoDataFrames"])' && \
    julia -e 'using Pkg; Pkg.precompile()'

# ==============================================================================
# STAGE 2: THE FINAL BOOTC OS
# ==============================================================================
FROM quay.io/fedora/fedora-kinoite:43

ENV JULIA_NUM_THREADS=8 \
    OPENBLAS_NUM_THREADS=8 \
    OMP_NUM_THREADS=8 \
    PYTHONUNBUFFERED=1 \
    JULIA_DEPOT_PATH="/usr/share/julia/depot" \
    PYTHONPATH="/usr/local/lib/python-deps" \
    PATH="/usr/lib/julia/bin:$PATH"

RUN dnf5 install -y --skip-unavailable --setopt=install_weak_deps=False \
    python3.13 R-core gdal proj geos hdf5 fftw openblas \
    time hyperfine git && \
    dnf5 clean all

COPY --from=builder /opt/python-deps /usr/local/lib/python-deps
COPY --from=builder /opt/R-deps /usr/lib64/R/library
COPY --from=builder /opt/julia /usr/lib/julia
COPY --from=builder /opt/julia-depot /usr/share/julia/depot

# Link python3 to python3.13 for consistency
RUN ln -sf /usr/bin/python3.13 /usr/bin/python3

COPY ./firstboot/first-boot-setup.sh /usr/local/bin/first-boot-setup.sh
COPY ./firstboot/benchmark-firstboot.service /etc/systemd/system/benchmark-firstboot.service

RUN chmod +x /usr/local/bin/first-boot-setup.sh && \
    systemctl enable benchmark-firstboot.service

RUN mkdir -p /var/data && ln -s /var/data /data && \
    mkdir -p /var/benchmarks && ln -s /var/benchmarks /benchmarks
