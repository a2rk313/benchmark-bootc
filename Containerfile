# ==============================================================================
# BARE-METAL GIS BENCHMARKING OS (KINOITE GUI + SERVER)
# ==============================================================================

# ==============================================================================
# STAGE 1: THE HEAVY BUILDER
# ==============================================================================
FROM registry.fedoraproject.org/fedora:43 AS builder

# Install compilers and development headers
RUN dnf5 install -y \
    gcc gcc-c++ make cmake git curl wget tar \
    python3 python3-pip python3-devel \
    R-core R-core-devel \
    gdal-devel proj-devel geos-devel \
    hdf5-devel fftw-devel openblas-devel sqlite-devel \
    libtiff-devel libjpeg-turbo-devel spatialindex-devel udunits2-devel gsl-devel \
    flexiblas-devel

# Install Julia 1.12.6
RUN curl -fsSL "https://julialang-s3.julialang.org/bin/linux/x64/1.12/julia-1.12.6-linux-x86_64.tar.gz" | tar -xz -C /opt && \
    mv /opt/julia-* /opt/julia

# PATH PARITY: Use the same path in builder as runtime to ensure cache validity
ENV JULIA_DEPOT_PATH="/usr/share/julia/depot"
ENV PATH="/opt/julia/bin:$PATH"

RUN mkdir -p /usr/share/julia/depot && \
    julia -e 'using Pkg; Pkg.add(["BenchmarkTools", "CSV", "DataFrames", "SHA", "MAT", "JSON3", "NearestNeighbors", "LibGEOS", "Shapefile", "ArchGDAL", "GeoDataFrames"])' && \
    julia -e 'using ArchGDAL, GeoDataFrames, LibGEOS, DataFrames; println("✓ Heavy GIS packages loaded")' && \
    julia -e 'using Pkg; Pkg.precompile()'

# Clean up transient data but KEEP registries, compiled, and artifacts
RUN rm -rf /usr/share/julia/depot/scratchspaces/* /usr/share/julia/depot/logs/* && \
    julia -e 'using Pkg, Dates; Pkg.gc(collect_delay=Day(0))'

# Build R dependencies
RUN mkdir -p /opt/R-deps && \
    echo "CXX14FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site && \
    echo "CXX17FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site && \
    echo "CXX20FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site && \
    Rscript -e "install.packages(c('terra', 'sf', 'data.table', 'R.matlab', 'FNN', 'jsonlite', 'digest'), lib='/opt/R-deps', repos='https://cloud.r-project.org/', Ncpus=parallel::detectCores())"

# ==============================================================================
# STAGE 2: THE FINAL OS (Appliance Only)
# ==============================================================================
FROM quay.io/fedora/fedora-kinoite:43

# ACADEMIC RIGOR: High-Performance Benchmarking Environment
ENV JULIA_NUM_THREADS=8 \
    OPENBLAS_NUM_THREADS=8 \
    FLEXIBLAS_NUM_THREADS=8 \
    GOTO_NUM_THREADS=8 \
    OMP_NUM_THREADS=8 \
    FLEXIBLAS=OPENBLAS-OPENMP \
    R_MAX_VSIZE=16G \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR \
    GDAL_CACHEMAX=512 \
    NPY_BLAS_ORDER=openblas \
    NPY_LAPACK_ORDER=openblas \
    JULIA_DEPOT_PATH="/usr/share/julia/depot" \
    PATH="/usr/lib/julia/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Install native runtime dependencies and tools
RUN dnf5 install -y --skip-unavailable --setopt=install_weak_deps=False \
    python3 \
    python3-numpy python3-scipy python3-pandas python3-matplotlib python3-seaborn \
    python3-scikit-learn python3-shapely python3-pyproj python3-fiona python3-rasterio \
    python3-geopandas python3-xarray python3-h5py python3-tqdm python3-psutil \
    python3-pyarrow \
    R-core gdal proj geos hdf5 fftw openblas udunits2 gsl \
    time hyperfine git \
    grub2-common grub2-efi-x64 shim-x64 efibootmgr \
    numactl kernel-tools flexiblas && \
    dnf5 clean all

# Copy built artifacts from the builder stage
COPY --from=builder /opt/R-deps /usr/lib64/R/library
COPY --from=builder /opt/julia /usr/lib/julia
COPY --from=builder /usr/share/julia/depot /usr/share/julia/depot

# Link runtimes and setup release ID
RUN ln -s /usr/lib/julia/bin/julia /usr/bin/julia && \
    chmod -R 755 /usr/share/julia/depot && \
    touch /etc/benchmark-bootc-release

# ACADEMIC RIGOR: Ensure environment survive into login shells
RUN echo '# Benchmark Environment Initialization' > /etc/profile.d/benchmark.sh && \
    echo "export JULIA_DEPOT_PATH=${JULIA_DEPOT_PATH}" >> /etc/profile.d/benchmark.sh && \
    echo "export JULIA_NUM_THREADS=${JULIA_NUM_THREADS}" >> /etc/profile.d/benchmark.sh && \
    echo "export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS}" >> /etc/profile.d/benchmark.sh && \
    echo "export FLEXIBLAS_NUM_THREADS=${FLEXIBLAS_NUM_THREADS}" >> /etc/profile.d/benchmark.sh && \
    echo "export GOTO_NUM_THREADS=${GOTO_NUM_THREADS}" >> /etc/profile.d/benchmark.sh && \
    echo "export OMP_NUM_THREADS=${OMP_NUM_THREADS}" >> /etc/profile.d/benchmark.sh && \
    echo "export FLEXIBLAS=${FLEXIBLAS}" >> /etc/profile.d/benchmark.sh && \
    echo "export PYTHONDONTWRITEBYTECODE=1" >> /etc/profile.d/benchmark.sh && \
    echo "export GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR" >> /etc/profile.d/benchmark.sh
