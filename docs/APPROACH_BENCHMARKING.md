# Comprehensive Architectural Documentation: bootc Environment for GIS Benchmarking

## 1. Abstract and Academic Rationale

This document provides a comprehensive technical specification of the system architecture and containerization methodologies used to construct the **benchmark-bootc** operating system. The primary objective of this environment is to facilitate **scientifically rigorous, reproducible performance benchmarking** of Geographic Information Systems (GIS) and remote sensing (RS) workloads across three programming languages: Python, R, and Julia.

To satisfy the "minimum-time" statistical validity methodology outlined by **Chen & Revels (2016)**, it is imperative to eliminate systemic interference — such as hypervisor "noisy neighbor" effects, containerization overhead, and OS scheduler noise — from benchmark measurements. By utilizing the **Bootable Containers (bootc)** standard, this project creates a custom, immutable Linux distribution that boots directly onto bare-metal hardware. This ensures that recorded execution times reflect the raw performance of the underlying language engines and C++ geospatial libraries, completely free from virtualization overhead.

### 1.1 Why bootc?

**bootc (Bootable Containers)** is a technology that packages a complete Linux operating system as an [OCI container image](https://opencontainers.org/) and boots it directly on bare metal or virtual machines. It provides:

| Feature | Benefit for Benchmarking |
|---------|-------------------------|
| **Immutability** | Filesystem cannot drift; exact package versions guaranteed |
| **Atomic updates** | Roll back to any previous image if something breaks |
| **Content-addressable** | Every deployment verified by SHA-256 hash |
| **CI/CD native** | Standard container build pipelines (GitHub Actions) |
| **Bare-metal** | No hypervisor overhead (unlike VMs or containers) |

---

## 2. System Architecture: The Strict Decoupling Design

To balance scientific stability with research agility, this project employs a **Strict Decoupling Architecture**. The system is divided into two distinct layers:

### 2.1. The Appliance Layer (`benchmark-bootc`)

This repository serves as the **Hardware-as-Code (HaC)** foundation. It is responsible for:

- Defining the OS kernel and immutable filesystem
- Installing the high-performance C++ geospatial stack (GDAL, PROJ, GEOS)
- Providing optimized language runtimes (Julia 1.12.6, Python 3.14.x, R 4.5.x)
- Enforcing BLAS synchronization and CPU affinity tools (`numactl`)
- Standardizing the benchmarking environment through unified environment variables

The appliance is built as a **multi-stage bootc image**, ensuring a "clean-room" environment for the runtimes.

### 2.2. The Logic Layer (`benchmark-thesis`)

This repository contains the **Research Logic**. It is decoupled from the OS image and is cloned at runtime by the user. It contains:

- Identical algorithmic implementations in Julia, Python, and R
- Orchestration scripts (`setup-benchmarks.sh`, `native_benchmark.sh`)
- Dataset management and validation suites
- Statistical visualization tools

### 2.3. The Interface: Manual Initialization

Users boot the immutable appliance and then initialize the logic layer:

```bash
# 1. Clone the logic repository
git clone https://github.com/a2rk313/benchmark-thesis.git ~/benchmark-thesis

# 2. Run setup (validates environment, downloads data)
cd ~/benchmark-thesis && sudo ./setup-benchmarks.sh

# 3. Execute benchmarks
./native_benchmark.sh
```

### 2.4. Why Decouple?

| Concern | Without Decoupling | With Decoupling |
|---------|-------------------|-----------------|
| Fix a benchmark bug | Rebuild 8GB OS image (~30 min) | `git pull` (instant) |
| Add a new benchmark | Rebuild entire image | Write new script, commit |
| Update a dataset | Rebuild image | Download new data |
| Tune OS dependencies | Rebuild image | Rebuild image (only when needed) |
| Reproduce results | Unclear which OS version | Exact image digest pinned |

---

## 3. Fedora bootc and OSTree Internals

The appliance is built on Fedora Kinoite, utilizing the bootc standard for OCI-native image updates.

### 3.1. Immutable Filesystem Management

In bootc systems, the filesystem is organized as follows:

| Mount Point | Access | Purpose |
|-------------|--------|---------|
| `/usr` | Read-only | System packages, binaries, libraries |
| `/var` | Read-write | User data, logs, runtime state |
| `/home` | Persistent | User files (survives OS updates) |
| `/etc` | Read-only (with overlays) | System configuration |

**Impact on our project**:
- All system packages are baked into the image (no runtime `dnf install`)
- User data must be stored in `/var` or `/home` (not `/usr` or `/root`)
- The Julia depot at `/usr/share/julia/depot` is read-only (compiled packages are immutable)
- A writable depot at `/var/lib/julia` is created at boot for user-specific packages

### 3.2. OSTree Deployments

OSTree (similar to Git for operating systems) allows multiple OS versions to coexist:

```
$ sudo rpm-ostree status
State: idle
Deployments:
● ostree-unverified-registry:ghcr.io/a2rk313/benchmark-bootc:latest
                   Digest: sha256:5e7969299e4fc949c43c8001d5712eedb6f1fb89079375c39a93fa1895bed9c4
                  Version: latest.20260428 (2026-04-28T08:35:16Z)
                   Pinned: yes

  ostree-unverified-registry:ghcr.io/a2rk313/benchmark-bootc:latest
                   Digest: sha256:abc123...  ← Previous version (available for rollback)
```

Users can rollback to any previous deployment from the GRUB boot menu.

### 3.3. Julia Depot Optimization

Julia's JIT (Just-In-Time) nature requires precompiled binary caches to prevent timing contamination. The appliance synchronizes the `JULIA_DEPOT_PATH` across build and runtime stages:

**Build stage** (Containerfile Stage 1):
```dockerfile
ENV JULIA_DEPOT_PATH="/usr/share/julia/depot"
RUN julia -e 'using Pkg; Pkg.add(["ArchGDAL", "GeoDataFrames", ...])'
RUN julia -e 'using ArchGDAL, GeoDataFrames; println("Loaded")'
RUN julia -e 'using Pkg; Pkg.precompile(strict=true)'
```

**Runtime stage** (Containerfile Stage 2):
```dockerfile
COPY --from=builder /usr/share/julia/depot /usr/share/julia/depot
RUN echo 'JULIA_DEPOT_PATH=/var/lib/julia:/usr/share/julia/depot' >> /etc/environment
```

This ensures that AOT (Ahead-of-Time) precompiled GIS packages are valid and available with zero first-run overhead.

---

## 4. Multi-Stage Build Architecture

### 4.1. Stage 1: The Builder (Heavy Compilation)

```dockerfile
FROM registry.fedoraproject.org/fedora:43 AS builder
```

This stage:
1. Installs compilers, development headers, and build tools
2. Downloads and installs Julia 1.12.6
3. Precompiles Julia packages with a specific LLVM CPU target
4. Builds R packages from source
5. All artifacts are stored in `/usr/share/julia/depot`

**Key technique**: LLVM fat binary compilation
```dockerfile
ENV JULIA_CPU_TARGET="generic;sandybridge,-xsaveopt,clone_all;haswell,-rdrnd,base(1)"
```

This instructs Julia to compile each package for multiple CPU architectures:
- `generic`: Baseline x86-64 (works on any processor)
- `sandybridge`: AVX instructions (2011+ Intel)
- `haswell`: AVX2 instructions (2013+ Intel)

The resulting "fat binaries" run efficiently on a wide range of CPUs without recompilation.

### 4.2. Stage 2: The Final OS (Lean Deployment)

```dockerfile
FROM quay.io/fedora/fedora-kinoite:43
```

This stage:
1. Starts from a clean Fedora Kinoite base
2. Installs only runtime packages (no compilers, no build tools)
3. Copies the precompiled Julia depot from the builder stage
4. Sets up environment variables and system configuration
5. Verifies all packages load correctly

**Result**: A lean, production-ready OS image with all computational infrastructure pre-installed.

---

## 5. Benchmark Fairness and Variance Control

A core requirement for the thesis is a "level playing field" for all three language ecosystems.

### 5.1. BLAS Synchronization

**What is BLAS?** BLAS (Basic Linear Algebra Subprograms) is a standardized specification for low-level linear algebra routines. It is the computational foundation of all numerical computing — matrix multiplication, dot products, vector operations, etc.

All three runtimes are forced to use the **same OpenBLAS backend** via FlexiBLAS:

```bash
flexiblas default OPENBLAS
```

Thread counts are locked to 8 across all ecosystems:
- `JULIA_NUM_THREADS=8`
- `OPENBLAS_NUM_THREADS=8`
- `FLEXIBLAS_NUM_THREADS=8`
- `GOTO_NUM_THREADS=8`
- `OMP_NUM_THREADS=8`

This ensures that when Python calls `numpy.dot()`, Julia calls `A * B`, or R calls `crossprod()`, they all execute the **same underlying OpenBLAS code**.

### 5.2. CPU Affinity (Variance Killer)

To eliminate Linux scheduler noise, the benchmark orchestrator uses `numactl`:

```bash
numactl --cpunodebind=0 --membind=0 --physcpubind=0-7 <benchmark_command>
```

This locks the benchmark process to specific physical cores, preventing:
- **Thread migration**: Moving a thread between cores invalidates CPU cache
- **NUMA penalties**: Accessing memory from a "remote" NUMA node is slower
- **Frequency scaling**: Different cores may have different clock speeds

### 5.3. Filesystem Cache Clearing

Between benchmark runs, the filesystem cache is cleared:

```bash
sync; echo 3 > /proc/sys/vm/drop_caches
```

This ensures that I/O benchmarks measure actual disk performance, not cached data from previous runs.

---

## 6. Environment Variable Configuration

The OS sets environment variables at two levels to ensure availability across all execution contexts:

### 6.1. Global (`/etc/environment`)

Read by PAM for ALL sessions (login shells, scripts, systemd services):
```
JULIA_DEPOT_PATH=/var/lib/julia:/usr/share/julia/depot
JULIA_PKG_OFFLINE=true
```

### 6.2. Interactive (`/etc/profile.d/benchmark.sh`)

Loaded on interactive login:
```bash
export JULIA_DEPOT_PATH="/var/lib/julia:/usr/share/julia/depot"
export JULIA_PKG_OFFLINE="true"
export JULIA_NUM_THREADS=8
export OPENBLAS_NUM_THREADS=8
export FLEXIBLAS_NUM_THREADS=8
export GOTO_NUM_THREADS=8
export OMP_NUM_THREADS=8
export FLEXIBLAS=OPENBLAS-OPENMP
```

**Why two levels?** Interactive shells source `profile.d`, but scripts and non-interactive processes read `/etc/environment`. Setting both ensures `JULIA_DEPOT_PATH` is available regardless of how Julia is invoked.

---

## 7. Repository Structure

```
benchmark-bootc/
├── Containerfile              # Multi-stage OS definition
├── .github/
│   └── workflows/
│       ├── build.yml          # Container image build and publish
│       └── build-disk.yml     # Disk image build (ISO, QCOW2)
├── disk_config/
│   ├── disk.toml              # BIB config for QCOW2
│   └── iso.toml               # BIB config for ISO
├── build_files/
│   └── build.sh               # Legacy build script
├── docs/
│   └── APPROACH_BENCHMARKING.md  # This file
├── Justfile                   # Build automation commands
├── AGENTS.md                  # Internal AI assistant docs
├── CHANGELOG.md               # Version history
└── README.md                  # Main documentation
```

---

## 8. CI/CD Pipeline

### 8.1. Container Image Build (`build.yml`)

**Trigger**: Push to `main` branch

**What it does**:
1. Builds the multi-stage container image using the `Containerfile`
2. Pushes to GitHub Container Registry (GHCR) at `ghcr.io/a2rk313/benchmark-bootc:latest`
3. Tags with date-based version (e.g., `latest.20260428`)

### 8.2. Disk Image Build (`build-disk.yml`)

**Trigger**: Manual dispatch or tag push (`thesis-*`)

**What it does**:
1. Pulls the container image from GHCR
2. Runs Bootc Image Builder (BIB) to create:
   - **QCOW2**: Virtual machine image (for KVM/QEMU)
   - **anaconda-iso**: Bootable installer ISO (for physical machines)
3. Splits ISO files into <1.9GB chunks (GitHub Release 2GB file limit)
4. Generates SHA256 checksums
5. Uploads to GitHub Release (on tag push) or Job Artifacts (on manual dispatch)

### 8.3. Build Commands

```bash
# Build container image locally
just build

# Build QCOW2 VM image locally
just build-qcow2
```

---

## 9. Conclusion

By separating the **Appliance** from the **Logic**, this architecture provides a high-fidelity scientific instrument that is both stable and agile. Research logic can be updated instantly via Git, while the underlying computational foundation remains immutable, reproducible, and highly tuned for bare-metal geoinformatics performance.

The use of bootc ensures that:
1. **Every deployment is identical** (content-addressable images)
2. **Updates are atomic and reversible** (OSTree deployments)
3. **No hypervisor overhead** (bare-metal execution)
4. **Clean-room environment** (no development tool interference)

This enables scientifically rigorous benchmarking that satisfies the requirements for publication in peer-reviewed geoinformatics journals.
