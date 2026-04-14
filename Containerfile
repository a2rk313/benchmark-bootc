# Benchmark Bootc OS - Single stage build
# Base: Fedora Silverblue with Julia, Python, R for GIS benchmarking

# Setup context for build script
FROM scratch AS ctx
COPY build_files/ /ctx/

# Base OS
FROM ghcr.io/ublue-os/silverblue-main:latest

# Run build script to install all packages
RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=cache,dst=/var/cache/libdnf5 \
    --mount=type=cache,dst=/var/cache/rpm-ostree \
    --mount=type=tmpfs,dst=/tmp \
    /ctx/build.sh

# Copy first-boot setup script
COPY firstboot/ /opt/firstboot/
RUN chmod +x /opt/firstboot/first-boot-setup.sh

# Install systemd service for first-boot setup
COPY firstboot/benchmark-firstboot.service /etc/systemd/system/
RUN systemctl enable benchmark-firstboot.service

# Create directories
RUN mkdir -p /benchmarks /data

# Set environment
ENV JULIA_DEPOT_PATH="/usr/share/julia/depot"
ENV JULIA_NUM_THREADS=8
ENV OPENBLAS_NUM_THREADS=8
ENV OMP_NUM_THREADS=8

LABEL org.opencontainers.image.title="Benchmark Bootc OS"
LABEL io.containers.bootc="1"
