# 1. Setup a dummy context layer to mount our build script
FROM scratch AS ctx
COPY build_files /

# 2. Base OS
FROM ghcr.io/ublue-os/silverblue-main:latest

# 3. Copy project files into the container
COPY benchmarks/ /benchmarks/
COPY tools/ /tools/
COPY validation/ /validation/

# 4. Copy execution scripts and ensure they are executable
COPY run_benchmarks.sh native_benchmark.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/run_benchmarks.sh /usr/local/bin/native_benchmark.sh

# 5. Execute the build script with cache mounts
RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=cache,dst=/var/cache/libdnf5 \
    --mount=type=cache,dst=/var/cache/rpm-ostree \
    --mount=type=tmpfs,dst=/tmp \
    /ctx/build.sh