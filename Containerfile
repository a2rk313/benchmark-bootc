# 1. Setup a dummy context layer to mount our build script
FROM scratch AS ctx
COPY build_files /

# 2. Base OS
FROM ghcr.io/ublue-os/silverblue-main:latest

# 3. Execute the build script with cache mounts
RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=cache,dst=/var/cache/libdnf5 \
    --mount=type=cache,dst=/var/cache/rpm-ostree \
    --mount=type=tmpfs,dst=/tmp \
    /ctx/build.sh

# 4. Copy first-boot setup scripts
COPY firstboot/ /opt/firstboot/
RUN chmod +x /opt/firstboot/first-boot-setup.sh

# 5. Install systemd service for first-boot setup
COPY firstboot/benchmark-firstboot.service /etc/systemd/system/
RUN systemctl enable benchmark-firstboot.service

# 6. Copy native benchmark script
COPY native_benchmark.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/native_benchmark.sh

# 7. Create directories
RUN mkdir -p /benchmarks /data

# Set environment
ENV JULIA_NUM_THREADS=8
ENV OPENBLAS_NUM_THREADS=8
ENV OMP_NUM_THREADS=8
