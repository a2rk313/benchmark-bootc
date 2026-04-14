# ============================================================
# STAGE 1: Builder (has all dev tools, compiles packages)
# ============================================================
FROM ghcr.io/ublue-os/silverblue-main:latest AS builder

# Copy build script for this stage
FROM scratch AS ctx
COPY build_files/ /ctx/

# Install all packages including dev headers in builder
RUN --mount=type=cache,dst=/var/cache/libdnf5 \
    --mount=type=cache,dst=/var/cache/rpm-ostree \
    --mount=type=tmpfs,dst=/tmp \
    --mount=type=bind,from=ctx,source=/,target=/ctx \
    /ctx/build.sh

# ============================================================
# STAGE 2: Runtime (minimal, only runtime essentials)
# ============================================================
FROM ghcr.io/ublue-os/silverblue-main:latest AS runtime

# Copy installed binaries and libraries from builder
COPY --from=builder /usr/bin/julia /usr/bin/julia
COPY --from=builder /usr/bin/uv /usr/bin/uv
COPY --from=builder /usr/bin/hyperfine /usr/bin/hyperfine
COPY --from=builder /usr/bin/time /usr/bin/time

# Copy Julia installation
COPY --from=builder /usr/lib/julia /usr/lib/julia

# Copy Julia depot (precompiled packages)
COPY --from=builder /usr/share/julia /usr/share/julia

# Copy Python packages installed by uv
COPY --from=builder /usr/lib/python3.13 /usr/lib/python3.13
COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13 2>/dev/null || true
COPY --from=builder /usr/local/bin/uvx /usr/local/bin/uvx 2>/dev/null || true

# Copy R packages
COPY --from=builder /usr/lib64/R /usr/lib64/R

# Copy benchmark files (data downloaded at runtime)
COPY benchmarks/ /benchmarks/
COPY tools/ /tools/
COPY validation/ /validation/

# Copy scripts
COPY native_benchmark.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/native_benchmark.sh

# Create symlinks for Julia depot
ENV JULIA_DEPOT_PATH="/usr/share/julia/depot"

# Set thread configuration for benchmarking
ENV JULIA_NUM_THREADS=8
ENV OPENBLAS_NUM_THREADS=8
ENV OMP_NUM_THREADS=8

# Cleanup unnecessary files
RUN rm -rf /var/cache/* /tmp/* /root/.cache 2>/dev/null || true

LABEL org.opencontainers.image.title="Benchmark Bootc OS"
LABEL io.containers.bootc="1"
