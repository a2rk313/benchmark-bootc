# 1. Setup a dummy context layer to mount our build script
FROM scratch AS ctx
COPY build_files /

# 2. Swap to the OFFICIAL Fedora Silverblue base (GNOME Desktop)
FROM quay.io/fedora/fedora-silverblue:43

# 3. Set Environment Variables for Performance
# (Placed early so they are available to the OS globally)
# 3. Set Environment Variables for Performance & Tuning
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

# 4. Execute the optimized build script FIRST
# Doing this before copying your local scripts means Docker/Podman will cache
# this massive 10-minute compilation layer. If you only edit a python script 
# later, it won't have to rebuild Julia/R/GDAL from scratch!
RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=cache,dst=/var/cache/libdnf5 \
    --mount=type=cache,dst=/var/cache/rpm-ostree \
    --mount=type=tmpfs,dst=/tmp \
    /ctx/build.sh

# 5. Copy project files into the container's immutable tree
COPY benchmarks/ /benchmarks/
COPY tools/ /tools/
COPY validation/ /validation/

# 6. Copy first-boot setup scripts (Safely into /usr/local/bin, NOT /opt)
COPY firstboot/first-boot-setup.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/first-boot-setup.sh

# 7. Install systemd service for first-boot setup
COPY firstboot/benchmark-firstboot.service /etc/systemd/system/
RUN systemctl enable benchmark-firstboot.service

# 8. Copy native benchmark scripts
COPY run_benchmarks.sh native_benchmark.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/run_benchmarks.sh /usr/local/bin/native_benchmark.sh

# 9. Create mutable data directories safely
# In Silverblue, the root directory (/) is immutable. To have a writable /data 
# directory, we create it in /var and symlink it to the root.
RUN mkdir -p /var/data && ln -s /var/data /data
