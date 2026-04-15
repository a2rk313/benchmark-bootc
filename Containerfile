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

# =====================================================================
# 4. COPY EVERYTHING FIRST
# (Doing this before the 15-minute build.sh prevents Buildah from 
# dropping the GitHub Actions workspace context)
# =====================================================================
COPY ./benchmarks/ /benchmarks/
COPY ./tools/ /tools/
COPY ./validation/ /validation/

# Copy main execution scripts
COPY ./run_benchmarks.sh ./native_benchmark.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/run_benchmarks.sh /usr/local/bin/native_benchmark.sh

# Copy first-boot setup scripts (Ensure these exist in your Git repo!)
COPY ./firstboot/first-boot-setup.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/first-boot-setup.sh

COPY ./firstboot/benchmark-firstboot.service /etc/systemd/system/
RUN systemctl enable benchmark-firstboot.service

# 5. Create mutable data directories safely
RUN mkdir -p /var/data && ln -s /var/data /data

# =====================================================================
# 6. RUN THE MASSIVE BUILD SCRIPT LAST
# =====================================================================
RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=cache,dst=/var/cache/libdnf5 \
    --mount=type=cache,dst=/var/cache/rpm-ostree \
    --mount=type=tmpfs,dst=/tmp \
    /ctx/build.sh
