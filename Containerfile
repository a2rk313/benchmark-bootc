# 1. Setup a dummy context layer to mount our build script
FROM scratch AS ctx
COPY build_files /

# 2. Swap to the OFFICIAL Fedora Silverblue base (GNOME Desktop)
FROM quay.io/fedora/fedora-silverblue:43

# 3. Set Environment Variables for Performance
ENV JULIA_NUM_THREADS=8 \
    OPENBLAS_NUM_THREADS=8 \
    OMP_NUM_THREADS=8 \
    R_MAX_VSIZE=16G \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR \
    GDAL_CACHEMAX=512 \
    NPY_BLAS_ORDER=openblas \
    NPY_LAPACK_ORDER=openblas

# 4. Copy OS-level Orchestration Scripts (Must exist in this repo)
COPY run_benchmarks.sh native_benchmark.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/run_benchmarks.sh /usr/local/bin/native_benchmark.sh

# Copy first-boot setup scripts 
COPY firstboot/first-boot-setup.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/first-boot-setup.sh

COPY firstboot/benchmark-firstboot.service /etc/systemd/system/
RUN systemctl enable benchmark-firstboot.service

# 5. Create MUTABLE directories for runtime cloning and data
# Because the root filesystem (/) is read-only in Silverblue, we must 
# route these to the writable /var partition.
RUN mkdir -p /var/data && ln -s /var/data /data && \
    mkdir -p /var/benchmarks && ln -s /var/benchmarks /benchmarks

# 6. Execute the massive dependency build script
RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=cache,dst=/var/cache/libdnf5 \
    --mount=type=cache,dst=/var/cache/rpm-ostree \
    --mount=type=tmpfs,dst=/tmp \
    /ctx/build.sh
