# ==============================================================================
# BARE-METAL GIS BENCHMARKING OS (KINOITE GUI + SERVER)
# ==============================================================================

# ==============================================================================
# STAGE 1: THE HEAVY BUILDER (R & Julia only)
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
# STAGE 2: THE FINAL OS (Native Python Packages)
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
    PATH="/usr/lib/julia/bin:$PATH"

# Install native Python packages and runtime dependencies
RUN dnf5 install -y --skip-unavailable --setopt=install_weak_deps=False \
    python3 uv \
    python3-numpy python3-scipy python3-pandas python3-matplotlib python3-seaborn \
    python3-scikit-learn python3-shapely python3-pyproj python3-fiona python3-rasterio \
    python3-geopandas python3-xarray python3-h5py python3-tqdm python3-psutil \
    R-core gdal proj geos hdf5 fftw openblas udunits2 gsl \
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
COPY --from=builder /opt/R-deps /usr/lib64/R/library
COPY --from=builder /opt/julia /usr/lib/julia
COPY --from=builder /opt/julia-depot /var/lib/julia/depot

# Link runtimes for global visibility
RUN ln -sf /usr/bin/python3 /usr/bin/python3 && \
    ln -s /usr/lib/julia/bin/julia /usr/bin/julia && \
    mkdir -p /usr/share/julia && \
    ln -sf /var/lib/julia/depot /usr/share/julia/depot

# Copy orchestrators and scripts
COPY ./firstboot/setup-benchmarks.sh /usr/local/bin/setup-benchmarks.sh
COPY ./firstboot/toggle_gui.sh /usr/local/bin/toggle_gui.sh
COPY ./native_benchmark.sh /usr/local/bin/native_benchmark.sh
COPY ./native_helper.sh /usr/local/bin/native_helper.sh

# Final OS configuration
RUN touch /etc/benchmark-bootc-release && \
    chmod +x /usr/local/bin/setup-benchmarks.sh && \
    chmod +x /usr/local/bin/toggle_gui.sh && \
    chmod +x /usr/local/bin/native_benchmark.sh && \
    chmod +x /usr/local/bin/native_helper.sh

# Setup writable benchmark partition (contains data/ folder)
RUN mkdir -p /var/benchmarks && ln -s /var/benchmarks /benchmarks && \
    ln -sf /benchmarks/data /data

# Ensure all thread vars and paths survive into login shells
RUN echo "export JULIA_DEPOT_PATH=/var/lib/julia/depot"            >> /etc/profile.d/benchmark.sh && \
    echo "export OPENBLAS_NUM_THREADS=8"                             >> /etc/profile.d/benchmark.sh && \
    echo "export FLEXIBLAS_NUM_THREADS=8"                            >> /etc/profile.d/benchmark.sh && \
    echo "export GOTO_NUM_THREADS=8"                                 >> /etc/profile.d/benchmark.sh && \
    echo "export OMP_NUM_THREADS=8"                                  >> /etc/profile.d/benchmark.sh && \
    echo "export JULIA_NUM_THREADS=8"                                >> /etc/profile.d/benchmark.sh
