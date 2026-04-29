# ==============================================================================
# BARE-METAL GIS BENCHMARKING OS (KINOITE GUI + SERVER)
# ==============================================================================
# Version: Python 3.14.4, Julia 1.12.6, R 4.5.3
# Architecture Target: LLVM FAT BINARY (Multi-Architecture)
# ==============================================================================

# ==============================================================================
# STAGE 1: THE HEAVY BUILDER (Julia packages only)
# ==============================================================================
FROM registry.fedoraproject.org/fedora:43 AS builder

# 1. LLVM MULTIVERSIONING TARGET
# Instructs Julia to compile a fat binary that supports baseline x86-64, 
# SandyBridge (AVX), and Haswell (AVX2). This prevents hardware-mismatch 
# cache invalidation across disparate deployment targets.
ENV JULIA_CPU_TARGET="generic;sandybridge,-xsaveopt,clone_all;haswell,-rdrnd,base(1)"

# Note: JULIA_PKG_OFFLINE is intentionally omitted here so Pkg can resolve dependencies.

# Install compilers and development headers
RUN dnf5 install -y \
    gcc gcc-c++ make cmake git curl wget tar \
    clang19 clang19-devel llvm19-devel \
    python3 python3-pip \
    R-core R-core-devel \
    gdal-devel proj-devel geos-devel \
    hdf5-devel fftw-devel openblas-devel sqlite-devel \
    libtiff-devel libjpeg-turbo-devel spatialindex-devel udunits2-devel gsl-devel \
    flexiblas-devel

# Install Julia 1.12.6
RUN curl -fsSL "https://julialang-s3.julialang.org/bin/linux/x64/1.12/julia-1.12.6-linux-x86_64.tar.gz" | \
    tar -xz -C /usr/lib && \
    mv /usr/lib/julia-* /usr/lib/julia

# PATH PARITY
ENV JULIA_DEPOT_PATH="/usr/share/julia/depot"
ENV PATH="/usr/lib/julia/bin:$PATH"

# 2. STRICT PRECOMPILATION (WITH NETWORK ACCESS)
# We enforce strict=true so the build fails if any package fails to compile,
# ensuring no deferred JIT compilation leaks into the benchmark phase.
RUN mkdir -p /usr/share/julia/depot && \
    julia -e 'using Pkg; Pkg.add(["BenchmarkTools", "CSV", "DataFrames", "SHA", "MAT", "JSON3", "NearestNeighbors", "LibGEOS", "Shapefile", "ArchGDAL", "GeoDataFrames"])' && \
    julia -e 'using ArchGDAL, GeoDataFrames, LibGEOS, DataFrames; println("✓ Heavy GIS packages loaded")' && \
    julia -e 'using Pkg; Pkg.precompile(strict=true)'

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
    NPY_LAPACK_ORDER=openblas

# 3. IMMUTABLE BUILD PATH
# During build, we strictly write to the immutable tree. No /var paths here.
ENV JULIA_DEPOT_PATH="/usr/share/julia/depot" \
    PATH="/usr/lib/julia/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Install native runtime dependencies
RUN dnf5 install -y --skip-unavailable --setopt=install_weak_deps=False \
    python3 python3-numpy python3-scipy python3-pandas python3-matplotlib python3-seaborn \
    python3-scikit-learn python3-shapely python3-pyproj python3-fiona python3-rasterio \
    python3-geopandas python3-xarray python3-h5py python3-tqdm python3-psutil \
    python3-pyarrow python3-setuptools python3-wheel \
    R-core gdal proj geos hdf5 fftw openblas udunits2 gsl \
    time hyperfine git \
    grub2-common grub2-efi-x64 shim-x64 efibootmgr \
    numactl kernel-tools flexiblas && \
    dnf5 clean all

# Copy built artifacts from the builder stage
COPY --from=builder /opt/R-deps /usr/lib64/R/library
COPY --from=builder /usr/lib/julia /usr/lib/julia
COPY --from=builder /usr/share/julia/depot /usr/share/julia/depot

# 4. DYNAMIC /VAR PROVISIONING (bootc fix)
# Tells systemd to create the writable layer at boot time, bypassing the 
# ephemeral nature of /var during OCI image building.
RUN echo "d /var/lib/julia 0755 root root -" > /usr/lib/tmpfiles.d/julia-depot.conf

# 5. CACHE PERMISSION LOCKDOWN
# Ensure deep traversal permissions so the runtime user can read the .ji files.
RUN chmod -R a+rX /usr/share/julia/depot

# Precompile final artifacts strictly into /usr/share
RUN julia --threads=1 -e 'using Pkg; Pkg.precompile(strict=true)' && \
    julia --threads=1 -e 'using BenchmarkTools, CSV, DataFrames, SHA, MAT, JSON3, NearestNeighbors, LibGEOS, Shapefile, ArchGDAL, GeoDataFrames; println("✓ All Julia packages natively baked into immutable OS layer")'

RUN ln -s /usr/lib/julia/bin/julia /usr/bin/julia && \
    touch /etc/benchmark-bootc-release

# 6. RUNTIME ENVIRONMENT INJECTION & CACHE FREEZE
# This script injects the split-depot and offline cache protections only when the user logs in.
RUN echo '# Benchmark Environment Initialization' > /etc/profile.d/benchmark.sh && \
    echo 'export JULIA_DEPOT_PATH="/var/lib/julia:/usr/share/julia/depot"' >> /etc/profile.d/benchmark.sh && \
    echo 'export JULIA_PKG_OFFLINE="true"' >> /etc/profile.d/benchmark.sh && \
    echo 'export JULIA_COMPILED_MODULES=1' >> /etc/profile.d/benchmark.sh && \
    echo 'export JULIA_NUM_THREADS=8' >> /etc/profile.d/benchmark.sh && \
    echo 'export OPENBLAS_NUM_THREADS=8' >> /etc/profile.d/benchmark.sh && \
    echo 'export FLEXIBLAS_NUM_THREADS=8' >> /etc/profile.d/benchmark.sh && \
    echo 'export GOTO_NUM_THREADS=8' >> /etc/profile.d/benchmark.sh && \
    echo 'export OMP_NUM_THREADS=8' >> /etc/profile.d/benchmark.sh && \
    echo 'export FLEXIBLAS=OPENBLAS-OPENMP' >> /etc/profile.d/benchmark.sh && \
    echo 'export PYTHONDONTWRITEBYTECODE=1' >> /etc/profile.d/benchmark.sh && \
    echo 'export GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR' >> /etc/profile.d/benchmark.sh

# 8. GLOBAL ENVIRONMENT (non-login shells, scripts, systemd services)
# /etc/environment is read by PAM for ALL sessions, ensuring JULIA_DEPOT_PATH
# is available regardless of how Julia is invoked.
RUN echo 'JULIA_DEPOT_PATH=/var/lib/julia:/usr/share/julia/depot' >> /etc/environment && \
    echo 'JULIA_PKG_OFFLINE=true' >> /etc/environment

# Run the bootc linter to avoid encountering certain bugs and maintain content quality.
RUN bootc container lint
