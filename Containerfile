# ==============================================================================
# BARE-METAL GIS BENCHMARKING OS (BOOTC)
# ==============================================================================
FROM quay.io/fedora/fedora-bootc:43

# Set environment variables for build and runtime
ENV JULIA_NUM_THREADS=8 \
    OPENBLAS_NUM_THREADS=8 \
    OMP_NUM_THREADS=8 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/usr/local/lib/python-deps" \
    JULIA_DEPOT_PATH="/usr/share/julia/depot"

# Copy the build script and other necessary files
COPY ./build_files/build.sh /tmp/build.sh
COPY ./firstboot/first-boot-setup.sh /usr/local/bin/first-boot-setup.sh
COPY ./firstboot/benchmark-firstboot.service /etc/systemd/system/benchmark-firstboot.service
COPY ./native_benchmark.sh /usr/local/bin/native_benchmark.sh
COPY ./native_helper.sh /usr/local/bin/native_helper.sh

# Run the consolidated build script
RUN chmod +x /tmp/build.sh && \
    /tmp/build.sh && \
    rm /tmp/build.sh

# Final OS configuration
RUN chmod +x /usr/local/bin/first-boot-setup.sh && \
    chmod +x /usr/local/bin/native_benchmark.sh && \
    chmod +x /usr/local/bin/native_helper.sh && \
    systemctl enable benchmark-firstboot.service

# Setup writable data and benchmark partitions
RUN mkdir -p /var/data && ln -s /var/data /data && \
    mkdir -p /var/benchmarks && ln -s /var/benchmarks /benchmarks

# Ensure PATH and PYTHONPATH are available for login shells
RUN echo "export PYTHONPATH=/usr/local/lib/python-deps:\$PYTHONPATH" >> /etc/profile.d/benchmark.sh && \
    echo "export JULIA_DEPOT_PATH=/usr/share/julia/depot" >> /etc/profile.d/benchmark.sh

