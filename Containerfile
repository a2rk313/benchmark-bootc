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

# Install uv (pinned v0.6.4 for reproducibility)
RUN curl -LsSf https://github.com/astral-sh/uv/releases/download/0.6.4/uv-x86_64-unknown-linux-gnu.tar.gz | \
    tar -xz -C /usr/bin --strip-components=1 "uv-x86_64-unknown-linux-gnu/uv" "uv-x86_64-unknown-linux-gnu/uvx"

# Build Python packages
# We explicitly install setuptools, wheel, and Cython because some packages (fiona, rasterio)
# may need to build from source on Python 3.14 if wheels are not yet available.
RUN uv pip install --system --python 3.14 --target=/opt/python-deps \
    setuptools wheel Cython && \
    uv pip install --system --python 3.14 --target=/opt/python-deps \
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

# Install Julia 1.12.6
RUN curl -fsSL "https://julialang-s3.julialang.org/bin/linux/x64/1.12/julia-1.12.6-linux-x86_64.tar.gz" | tar -xz -C /opt && \
    mv /opt/julia-* /opt/julia

ENV JULIA_DEPOT_PATH="/opt/julia-depot"
ENV PATH="/opt/julia/bin:$PATH"
RUN julia -e 'using Pkg; Pkg.add(["BenchmarkTools", "CSV", "DataFrames", "SHA", "MAT", "JSON3", "NearestNeighbors", "LibGEOS", "Shapefile", "ArchGDAL", "GeoDataFrames"])' && \
    julia -e 'using ArchGDAL, GeoDataFrames, LibGEOS, DataFrames; println("✓ Heavy GIS packages loaded")' && \
    julia -e 'using Pkg; Pkg.precompile()'

# Clean up transient data but KEEP registries, compiled, and artifacts
RUN rm -rf /opt/julia-depot/scratchspaces/* /opt/julia-depot/logs/* && \
    julia -e 'using Pkg, Dates; Pkg.gc(collect_delay=Day(0))'

# ==============================================================================
# STAGE 2: THE FINAL OS
# ==============================================================================
FROM quay.io/fedora/fedora-kinoite:43

# Set environment variables for runtime fairness
ENV JULIA_NUM_THREADS=8 \
    OPENBLAS_NUM_THREADS=8 \
    FLEXIBLAS_NUM_THREADS=8 \
    GOTO_NUM_THREADS=8 \
    OMP_NUM_THREADS=8 \
    PYTHONUNBUFFERED=1 \
    JULIA_DEPOT_PATH="/var/lib/julia/depot" \
    PYTHONPATH="/usr/local/lib/python-deps" \
    PATH="/usr/lib/julia/bin:$PATH"

# Install runtime dependencies and bootloader tools
RUN dnf5 install -y --skip-unavailable --setopt=install_weak_deps=False \
    python3 R-core gdal proj geos hdf5 fftw openblas udunits2 gsl \
    time hyperfine git \
    grub2-common grub2-efi-x64 shim-x64 efibootmgr \
    numactl kernel-tools flexiblas && \
    dnf5 clean all

# Set FlexiBLAS default to OpenBLAS backend for absolute parity
RUN if command -v flexiblas &> /dev/null; then \
        BACKEND=$(flexiblas list 2>/dev/null | grep -i openblas | head -n1 | awk '{print $1}'); \
        if [ -n "$BACKEND" ]; then flexiblas default "$BACKEND"; fi \
    fi

# Copy built artifacts from the builder stage
COPY --from=builder /opt/python-deps /usr/local/lib/python-deps
COPY --from=builder /opt/R-deps /usr/lib64/R/library
COPY --from=builder /opt/julia /usr/lib/julia
COPY --from=builder /opt/julia-depot /var/lib/julia/depot

# Link runtimes for global visibility
RUN ln -sf /usr/bin/python3 /usr/bin/python3 && \
    ln -s /usr/lib/julia/bin/julia /usr/bin/julia && \
    mkdir -p /usr/share/julia && \
    ln -sf /var/lib/julia/depot /usr/share/julia/depot

# Copy orchestrators and systemd units
COPY ./firstboot/first-boot-setup.sh /usr/local/bin/first-boot-setup.sh
COPY ./firstboot/benchmark-firstboot.service /etc/systemd/system/benchmark-firstboot.service
COPY ./firstboot/toggle_gui.sh /usr/local/bin/toggle_gui.sh
COPY ./native_benchmark.sh /usr/local/bin/native_benchmark.sh
COPY ./native_helper.sh /usr/local/bin/native_helper.sh

# Final OS configuration
RUN touch /etc/benchmark-bootc-release && \
    chmod +x /usr/local/bin/first-boot-setup.sh && \
    chmod +x /usr/local/bin/toggle_gui.sh && \
    chmod +x /usr/local/bin/native_benchmark.sh && \
    chmod +x /usr/local/bin/native_helper.sh && \
    systemctl enable benchmark-firstboot.service

# Setup writable benchmark partition (contains data/ folder)
RUN mkdir -p /var/benchmarks && ln -s /var/benchmarks /benchmarks && \
    ln -sf /benchmarks/data /data

# Ensure all thread vars and paths survive into login shells
RUN echo "export PYTHONPATH=/usr/local/lib/python-deps:\$PYTHONPATH" >> /etc/profile.d/benchmark.sh && \
    echo "export JULIA_DEPOT_PATH=/var/lib/julia/depot"            >> /etc/profile.d/benchmark.sh && \
    echo "export OPENBLAS_NUM_THREADS=8"                             >> /etc/profile.d/benchmark.sh && \
    echo "export FLEXIBLAS_NUM_THREADS=8"                            >> /etc/profile.d/benchmark.sh && \
    echo "export GOTO_NUM_THREADS=8"                                 >> /etc/profile.d/benchmark.sh && \
    echo "export OMP_NUM_THREADS=8"                                  >> /etc/profile.d/benchmark.sh && \
    echo "export JULIA_NUM_THREADS=8"                                >> /etc/profile.d/benchmark.sh
