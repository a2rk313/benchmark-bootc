# ==============================================================================
# BARE-METAL GIS BENCHMARKING OS (KINOITE GUI + SERVER)
# ==============================================================================
FROM quay.io/fedora/fedora-kinoite:43

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
COPY ./firstboot/toggle_gui.sh /usr/local/bin/toggle_gui.sh
COPY ./native_benchmark.sh /usr/local/bin/native_benchmark.sh
COPY ./native_helper.sh /usr/local/bin/native_helper.sh

# Run the consolidated build script
# Ensure bootloader tools are present for reliable rebasing/switching
RUN chmod +x /tmp/build.sh && \
    dnf5 install -y grub2-common grub2-efi-x64 shim-x64 efibootmgr && \
    /tmp/build.sh

# Final OS configuration
RUN touch /etc/benchmark-bootc-release && \
    chmod +x /usr/local/bin/first-boot-setup.sh && \
    chmod +x /usr/local/bin/toggle_gui.sh && \
    chmod +x /usr/local/bin/native_benchmark.sh && \
    chmod +x /usr/local/bin/native_helper.sh && \
    systemctl enable benchmark-firstboot.service

# Setup writable benchmark partition (which contains the data/ folder)
RUN mkdir -p /var/benchmarks && ln -s /var/benchmarks /benchmarks && \
    ln -sf /benchmarks/data /data

# Ensure PATH and PYTHONPATH are available for login shells
RUN echo "export PYTHONPATH=/usr/local/lib/python-deps:\$PYTHONPATH" >> /etc/profile.d/benchmark.sh && \
    echo "export JULIA_DEPOT_PATH=/usr/share/julia/depot" >> /etc/profile.d/benchmark.sh

