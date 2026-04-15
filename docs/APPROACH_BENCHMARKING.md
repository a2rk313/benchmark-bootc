# Comprehensive Architectural Documentation: bootc Environment for GIS Benchmarking

## 1. Abstract & Academic Rationale

This document outlines the system architecture and containerization methodologies used to construct the benchmark-bootc operating system. The primary objective of this environment is to facilitate scientifically rigorous, reproducible performance benchmarking of Geographic Information Systems (GIS) and remote sensing workloads across Python, R, and Julia.

To satisfy the "minimum-time" statistical validity methodology outlined by Chen & Revels (2016), it is imperative to eliminate systemic interference, such as hypervisor "noisy neighbor" effects and containerization overhead (e.g., Docker/Podman networking and storage drivers). By utilizing the Bootable Containers (bootc) standard built on top of Fedora Silverblue, this project creates a custom, immutable Linux distribution that boots directly onto bare-metal hardware. This ensures that recorded execution times reflect the raw performance of the underlying language engines and C++ geospatial libraries (GDAL/PROJ), completely free from virtualization taxes.

---

## 2. System Architecture: The Split-Repository Paradigm

Immutable operating systems inherently resist runtime modifications. Baking rapidly changing benchmark scripts directly into an 8GB OS image would require a 20-to-30-minute container rebuild for every minor code tweak. To solve this, the project employs a Split-Repository Design, separating the heavy dependency appliance from the agile runtime logic.

### 2.1. The Appliance Layer (benchmark-bootc)

This repository serves as the infrastructure-as-code (IaC) foundation. It contains the Containerfile and orchestration scripts responsible for compiling the C++ toolchains, language interpreters, and matrix algebra libraries. This image is built infrequently and acts as the static foundation.

### 2.2. The Logic Layer (benchmark-thesis)

This repository houses the dynamic .py, .R, and .jl benchmarking scripts, dataset loaders, and JSON aggregators. It is completely decoupled from the OS build process.

### 2.3. The Bridge: First-Boot Systemd Initialization

To bridge the immutable OS and the dynamic logic, a custom systemd service (`benchmark-firstboot.service`) is embedded in the OS image.

- **Trigger**: The service is configured with `After=network-online.target` and `Wants=network-online.target` to ensure execution only occurs once the bare-metal server has successfully acquired an IP address and internet access.
- **Execution**: A oneshot bash script dynamically clones the benchmark-thesis repository directly into the `/benchmarks` directory.
- **Path Injection**: The orchestrator scripts (`run_benchmarks.sh`) are symlinked directly into `/usr/local/bin`, seamlessly integrating the remote logic into the host operating system's `$PATH`.

---

## 3. Fedora Silverblue & OSTree Internals

Standard Dockerfiles assume a highly mutable environment where the root (/) filesystem is fully writable. Fedora Silverblue utilizes rpm-ostree, which mounts /usr as a read-only filesystem. Building a bootc image requires navigating several strict structural paradigms.

### 3.1. Mitigating the /root Symlink Trap

In Fedora Silverblue, `/root` is not a physical directory; it is a symlink mapped to `/var/roothome`. During the buildah container construction phase, the `/var` directory is strictly managed and often empty. Consequently, `/root` resolves as a broken symlink.

When package managers (like Rust's uv or juliaup) attempt to write installation receipts to `~/.local` or cache files to `~/.cache`, the build process immediately terminates with an OS Error 17 (File exists).

**Architectural Fix**: The build script forces the creation of the physical target directory (`mkdir -p /var/roothome`) before executing any network downloads. This satisfies the symlink for the duration of the container build, allowing caches to be written and subsequently purged.

### 3.2. Data Mutability via Partition Routing

Because the root filesystem is read-only at runtime, any benchmark script attempting to write a results.json file or download a dataset to `/benchmarks` or `/data` will fail.

**Architectural Fix**: During the Containerfile build, physical directories are created in the writable partition (`mkdir -p /var/data`). Symlinks are then established at the root level (`ln -s /var/data /data`). This provides the benchmark scripts with expected root-level access while safely routing the I/O operations to the mutable /var partition.

---

## 4. Compilation & Image Optimization Techniques

Compiling three distinct data science environments alongside heavy C++ geospatial frameworks natively results in massive disk bloat. Several techniques were employed to reduce the image size from an initial 13 GB down to a manageable 6-8 GB footprint.

### 4.1. The Strict DNF Dependency Diet

By default, installing the gdal-devel and R-core-devel packages via dnf5 triggers the installation of over 600 "weak dependencies." This includes the entirety of texlive (for rendering R PDF manuals) and java-25-openjdk (for R-Java bridges).

**Optimization**: The package manager was constrained using the `--setopt=install_weak_deps=False` flag. This surgically prevented the download and unpacking of roughly 4 GB of unnecessary documentation fonts, GUI frameworks (qt6), and JVMs that are entirely irrelevant to headless server benchmarking.

### 4.2. Aggressive Build-Cache Purging

Standard container layers preserve all file state changes. If a 500 MB .tar.gz source file is downloaded, compiled, and deleted in a subsequent RUN step, the 500 MB still exists in the underlying image layer.

**Optimization**: All installations (DNF, Python, Julia, R) are chained with their respective cleanup commands (`rm -rf /tmp/*`, `dnf clean all`) within a single execution script (`build.sh`), ensuring source tarballs and compilation artifacts are never committed to an OCI layer.

---

## 5. Language Ecosystem & Toolchain Tooling

To ensure equitable benchmarking, all language packages were compiled optimally for the host architecture, deliberately avoiding user-space version managers (which add $PATH shimming overhead).

### 5.1. Python Toolchain

Python packages were installed globally (`--prefix=/usr`) utilizing uv, an ultra-fast Rust-based package installer. uv was configured with `--no-cache` to prevent the storage of intermediate .whl (wheel) files. Furthermore, environmental variables (`PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`) were baked into the OS to prevent I/O bottlenecks and .pyc cache writing during execution timing.

### 5.2. Julia Ahead-of-Time (AOT) Precompilation

Julia utilizes Just-In-Time (JIT) compilation. If packages are compiled during the benchmark run, the execution time will reflect the compilation overhead rather than the algorithmic efficiency.

**Optimization**: The container build script detects the underlying architecture (x86_64 vs. aarch64) and pulls the corresponding binaries. The `JULIA_DEPOT_PATH` is redirected to the global `/usr/share/julia/depot`. During the image build, `Pkg.precompile()` is executed. This forces the AOT compilation of all spatial libraries (ArchGDAL, GeoDataFrames), baking the .ji and .so binary caches directly into the immutable disk image.

### 5.3. R and the GCC 15 cstdint Compiler Fix

R spatial packages (specifically sf and terra) are compiled natively from source utilizing all available CPU threads (`Ncpus=parallel::detectCores()`).

Because the base OS (Fedora 41/43) utilizes the bleeding-edge GCC 15 compiler, older C++ libraries (such as the s2 geometry engine) fail to compile due to missing standard library includes (`#include <cstdint>`) that were historically implicitly included in older GCC versions.

**Optimization**: To prevent compilation failure, global compilation flags were injected directly into R's system configuration:

```bash
echo "CXX14FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site
echo "CXX17FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site
echo "CXX20FLAGS += -include cstdint" >> /usr/lib64/R/etc/Makevars.site
```

This forces the C++ preprocessor to globally inject standard integer types (e.g., uint32_t), allowing legacy geospatial dependencies to compile securely under modern security and compiler standards.

---

## 6. Continuous Integration and Deterministic OS Assembly

A foundational requirement for scientific benchmarking is environmental determinism—the guarantee that the operating system can be identically reconstructed by peer reviewers without relying on the original author's local machine state. To enforce this strict reproducibility, the benchmark-bootc operating system is entirely abstracted from local hardware and orchestrated through an automated Continuous Integration (CI) pipeline using GitHub Actions.

### 6.1. Ephemeral "Clean Room" Compilation

Relying on a local machine to compile an immutable operating system introduces severe methodological risks, including local cache contamination, architecture mismatches, and undocumented environmental variables (often summarized as the "it works on my machine" anti-pattern).

By offloading the compilation to an ephemeral GitHub Actions Virtual Machine runner (ubuntu-latest), the project guarantees a pristine, zero-state "clean room" build environment for every iteration. The pipeline triggers automatically upon commits to the repository, ensuring the published container image is a strict, mathematically reproducible output of the version-controlled Containerfile.

### 6.2. Daemonless Containerization via Buildah

Standard CI pipelines often rely on Docker for container construction. However, Docker requires a persistent background daemon running as root, introducing security and networking overhead. Instead, this architecture utilizes Buildah, Red Hat's daemonless, rootless engine for constructing Open Container Initiative (OCI) compliant images.

### 6.3. Artifact Publication and Hardware Translation

Upon the successful assembly of the OCI layers, the GitHub Actions pipeline authenticates against the GitHub Container Registry (GHCR) and pushes the finalized multi-gigabyte image (`ghcr.io/username/benchmark-bootc:latest`).

While hosted as a standard OCI container, bare-metal servers cannot boot directly from a web registry. The final link in the supply chain involves transmuting this container into a raw hardware disk image. Utilizing the Red Hat bootc-image-builder tool, the container is pulled and converted in-place into target-specific formats:

- **QCOW2**: For deployment to KVM-based Virtual Machines or free-tier ARM cloud platforms (e.g., Oracle Cloud Ampere A1)
- **AMI**: For deployment to AWS .metal Spot Instances
- **ISO**: For flashing to physical USB media to boot directly onto consumer desktop hardware

This pipeline—from Git commit, to Buildah compilation, to GHCR distribution, to physical disk generation—establishes a fully automated, auditable, and scientifically transparent infrastructure supply chain.

---

## 7. Repository Structure

```
benchmark-bootc/
├── Containerfile              # bootc OS build definition
├── build_files/
│   └── build.sh               # Package installation script
├── firstboot/
│   ├── first-boot-setup.sh    # Repo clone script
│   └── benchmark-firstboot.service  # Systemd service
├── native_benchmark.sh         # Benchmark orchestrator
├── Justfile                   # VM build commands
└── .github/workflows/
    └── build.yml              # CI/CD pipeline
```

```
benchmark-thesis/
├── benchmarks/                # Python, Julia, R implementations
│   ├── matrix_ops.{py,jl,R}
│   ├── hsi_stream.{py,jl,R}
│   ├── vector_pip.{py,jl,R}
│   └── ...
├── tools/                     # Data download, visualization
├── validation/                # Cross-language validation
├── data/                      # Benchmark datasets
├── containers/                # Alternative container builds
├── Project.toml               # Julia dependencies
└── .mise.toml                 # Version management
```

---

## 8. Usage

### Deploy the OS

1. Pull the image: `podman pull ghcr.io/a2rk313/benchmark-bootc:latest`
2. Convert to bootable media using `bootc-image-builder`
3. Boot the bare-metal server

### First Boot

The `benchmark-firstboot.service` automatically:
1. Clones `benchmark-thesis` to `/benchmarks`
2. Downloads datasets to `/data`
3. Symlinks orchestrators to `/usr/local/bin`

### Run Benchmarks

```bash
# Quick benchmark
native_benchmark.sh

# Full suite
cd /benchmarks && ./run_benchmarks.sh --native-only
```

---

## 9. Conclusion

The benchmark-bootc operating system represents a highly specialized convergence of cloud-native infrastructure, continuous integration, and bare-metal performance engineering. By navigating the complexities of immutable OSTree filesystems, strictly governing dependency chains, forcing ahead-of-time binary compilation, and automating the supply chain via GitHub Actions, this environment guarantees maximum hardware utilization. The resulting architecture isolates the true computational capabilities of the Python, R, and Julia runtimes, providing a pristine, zero-overhead foundation for academic spatial benchmarking.
