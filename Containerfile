# Allow build scripts to be referenced without being copied into the final image
FROM scratch AS ctx
COPY build_files /

# Base Image: Silverblue main (minimal, no desktop)
FROM ghcr.io/ublue-os/silverblue-main:latest

### MODIFICATIONS
## Copy benchmark files
COPY benchmarks/ /benchmarks/
COPY tools/ /tools/
COPY validation/ /validation/
COPY run_benchmarks.sh native_benchmark.sh run-container.sh /usr/local/bin/
COPY Project.toml Manifest.toml /benchmarks/

## Install benchmark packages via build.sh
RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=cache,dst=/var/cache/libdnf5 \
    --mount=type=cache,dst=/var/cache/rpm-ostree \
    --mount=type=tmpfs,dst=/tmp \
    /ctx/build.sh

## Make scripts executable
RUN chmod +x /usr/local/bin/run_benchmarks.sh \
    /usr/local/bin/native_benchmark.sh \
    /usr/local/bin/run-container.sh

### LINTING
## Verify final image and contents are correct.
RUN bootc container lint