# Benchmark Bootc — Thesis Benchmarking OS Appliance

[![Build Status](https://img.shields.io/github/actions/workflow/status/a2rk313/benchmark-bootc/build-disk.yml)](https://github.com/a2rk313/benchmark-bootc/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Executive Summary

**benchmark-bootc** is a custom-built, immutable Linux operating system designed for **scientifically rigorous, reproducible bare-metal benchmarking** of Geographic Information Systems (GIS) and Remote Sensing (RS) workloads. Built using the [bootc](https://containers.github.io/bootc/) (Bootable Container) standard on Fedora Silverblue, this appliance provides a clean, optimized, and deterministic computational environment — free from the noise of background services, hypervisor overhead, and development tool interference.

This repository defines the **infrastructure layer** (the operating system, language runtimes, and system libraries). The research logic (benchmark implementations, orchestration scripts, and datasets) lives in the companion repository: [benchmark-thesis](https://github.com/a2rk313/benchmark-thesis).

---

## Table of Contents

1. [Research Context and Motivation](#1-research-context-and-motivation)
2. [Architecture: The Strict Decoupling Design](#2-architecture-the-strict-decoupling-design)
3. [Core Technologies Explained](#3-core-technologies-explained)
4. [The Bootc Operating System](#4-the-bootc-operating-system)
5. [Software Stack and Language Runtimes](#5-software-stack-and-language-runtimes)
6. [Benchmark Fairness and Variance Control](#6-benchmark-fairness-and-variance-control)
7. [Statistical Methodology](#7-statistical-methodology)
8. [Quick Start](#8-quick-start)
9. [Repository Structure](#9-repository-structure)
10. [CI/CD Pipeline and Disk Image Builds](#10-cicd-pipeline-and-disk-image-builds)
11. [Troubleshooting](#11-troubleshooting)
12. [For Thesis Committee](#12-for-thesis-committee)
13. [References](#13-references)

---

## 1. Research Context and Motivation

### 1.1 The Problem

Modern geospatial and remote sensing workflows are computationally intensive. Processing hyperspectral satellite imagery (with hundreds of spectral bands), performing spatial joins on millions of geographic points, or computing zonal statistics over large raster grids requires substantial computational resources. The choice of programming language and its underlying libraries can dramatically impact performance — but quantifying these differences requires a **controlled experimental environment**.

### 1.2 Why This Matters

In academic and industrial geoinformatics, practitioners choose between three dominant ecosystems:
- **Python** — the most popular, with mature libraries (GeoPandas, Rasterio, NumPy)
- **R** — strong in spatial statistics and geospatial analysis (sf, terra)
- **Julia** — a newer language promising Python-like syntax with C-like performance

However, comparisons are often confounded by:
1. **Hardware differences** — benchmarks run on different machines
2. **Library version mismatches** — different BLAS implementations, different library versions
3. **Container/hypervisor overhead** — Docker or VMs add 5–15% latency
4. **OS noise** — background services, CPU frequency scaling, scheduler decisions

### 1.3 Our Solution

**benchmark-bootc** addresses all four confounders by:
1. Running on **bare metal** (no hypervisor)
2. Using a **single, immutable OS image** with locked versions
3. Synchronizing **BLAS backends** across all languages (OpenBLAS via FlexiBLAS)
4. Eliminating **OS noise** through CPU affinity pinning and performance governor

---

## 2. Architecture: The Strict Decoupling Design

### 2.1 Overview

This project employs a **Strict Decoupling Architecture** that separates the operating system infrastructure from the research logic:

```
┌─────────────────────────────────────────────────────────────────┐
│                    BENCHMARK BOOTC                               │
│  (This Repository — Infrastructure / OS Appliance)              │
│                                                                 │
│  • Custom bootable OS (bootc image)                            │
│  • Language runtimes: Julia 1.12.6, Python 3.14.x, R 4.5.x     │
│  • Geospatial C++ libraries: GDAL, PROJ, GEOS                  │
│  • BLAS synchronization (OpenBLAS)                              │
│  • System tuning tools: numactl, cpupower                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                    Immutable OS Image
                    (updated rarely)
                              │
┌─────────────────────────────────────────────────────────────────┐
│                  BENCHMARK-THESIS                                │
│  (Companion Repository — Research Logic)                        │
│                                                                 │
│  • 9 benchmark implementations (Python, Julia, R)              │
│  • Orchestration scripts (run_benchmarks.sh, setup-benchmarks.sh)│
│  • Dataset management and validation suites                     │
│  • Statistical analysis and visualization tools                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Why Decouple?

| Concern | Without Decoupling | With Decoupling |
|---------|-------------------|-----------------|
| Fix a benchmark bug | Rebuild 8GB OS image (~30 min) | `git pull` (instant) |
| Add a new benchmark | Rebuild entire image | Write new script, commit |
| Update a dataset | Rebuild image | Download new data |
| Tune OS dependencies | Rebuild image | Rebuild image (only when needed) |
| Reproduce results | Unclear which OS version | Exact image digest pinned |

**The key insight**: OS infrastructure changes infrequently (library updates, kernel patches), while research logic changes constantly (bug fixes, new benchmarks, parameter tuning). Decoupling ensures that frequent code changes don't require expensive image rebuilds.

### 2.3 Layer Responsibilities

| Layer | Repository | Responsibility | Update Frequency |
|-------|-----------|----------------|------------------|
| **Appliance** | `benchmark-bootc` | OS, runtimes, C++ libraries, system tuning | Rarely (when dependencies change) |
| **Logic** | `benchmark-thesis` | Benchmark code, orchestration, analysis, datasets | Frequently (daily research workflow) |

---

## 3. Core Technologies Explained

### 3.1 bootc (Bootable Containers)

**Definition**: bootc is a technology that packages a complete Linux operating system as a [OCI container image](https://opencontainers.org/) and boots it directly on bare metal or virtual machines.

**How it works**:
1. Developers define an OS in a `Containerfile` (similar to a Dockerfile)
2. The image is built as a standard container and pushed to a registry
3. Target machines pull the image and boot directly from it
4. The system is **immutable** — the root filesystem cannot be modified at runtime
5. Updates are atomic: pull a new image, reboot into it

**Why we use it**:
- **Reproducibility**: Every deployment uses the exact same image (verified by content-addressable hash)
- **Immutability**: The OS cannot drift — no accidental package installations
- **Atomic updates**: Roll back to any previous image if something breaks
- **Container-native CI/CD**: Standard GitHub Actions can build and test the OS

### 3.2 OSTree (Atomic Filesystem)

**Definition**: OSTree is a version-controlled filesystem system (similar to Git, but for operating system files) used by Fedora Silverblue, Kinoite, and other immutable Linux distributions.

**Key concepts**:
- `/usr` is **read-only** — system files are part of an immutable tree
- `/var` is **writable** — user data, logs, and runtime state live here
- `/home` is **persistent** — user files survive OS updates
- **Deployments**: Multiple OS versions can coexist; you select which to boot at startup

**Impact on our project**:
- All system packages are baked into the image (no runtime `dnf install`)
- User data must be stored in `/var` or `/home` (not `/usr` or `/root`)
- The Julia depot at `/usr/share/julia/depot` is read-only (compiled packages are immutable)
- A writable depot at `/var/lib/julia` is created at boot for user-specific packages

### 3.3 Fedora Kinoite

**Definition**: Fedora Kinoite is the KDE Plasma variant of Fedora Silverblue. It provides a full desktop environment while maintaining the immutable OSTree filesystem.

**Why we use Kinoite**:
- **GUI support**: Allows benchmarking of desktop GIS applications if needed
- **Headless mode**: Can run in server-only mode (no desktop environment)
- **Full compatibility**: Shares the same bootc infrastructure as Silverblue
- **Large package ecosystem**: Access to Fedora's extensive package repository

### 3.4 BIB (Bootc Image Builder)

**Definition**: Bootc Image Builder (BIB) is a tool that converts a bootc container image into bootable disk formats (ISO installer, QCOW2 virtual machine image, Amazon Machine Image, etc.).

**What it does**:
1. Takes a bootc container image from a registry
2. Creates a bootable disk image (ISO for physical installation, QCOW2 for VMs)
3. Configures partitioning, bootloader, and filesystem
4. Produces a ready-to-deploy artifact

**In our workflow**:
- GitHub Actions runs BIB automatically on every push
- Outputs: ISO (for physical machines) and QCOW2 (for virtualization)
- ISO files are split into <2GB chunks for GitHub Release distribution

---

## 4. The Bootc Operating System

### 4.1 System Specifications

| Component | Version | Manager | Purpose |
|-----------|---------|---------|---------|
| **OS** | Fedora 43 (Kinoite) | bootc/OSTree | Base operating system |
| **Kernel** | Linux 6.x | rpm-ostree | System kernel |
| **Julia** | 1.12.6 | Direct binary (tarball) | High-performance computing language |
| **Python** | 3.14.x | System RPMs | General-purpose scripting |
| **R** | 4.5.x | dnf5 | Statistical computing |
| **GDAL** | 3.9.x | dnf5 | Geospatial data translation |
| **PROJ** | Latest | dnf5 | Coordinate transformations |
| **GEOS** | Latest | dnf5 | Computational geometry |
| **OpenBLAS** | Latest | dnf5/FlexiBLAS | Linear algebra backend |
| **FFTW** | Latest | dnf5 | Fast Fourier Transforms |
| **HDF5** | Latest | dnf5 | Hierarchical data format |

### 4.2 The Multi-Stage Containerfile

The OS is defined in a `Containerfile` with two build stages:

#### Stage 1: The Builder (Heavy Compilation)

```dockerfile
FROM registry.fedoraproject.org/fedora:43 AS builder
```

This stage:
1. Installs compilers, development headers, and build tools
2. Downloads and installs Julia 1.12.6
3. **Precompiles Julia packages** with a specific LLVM CPU target (`generic;sandybridge;haswell`) — producing "fat binaries" that run efficiently on a wide range of CPUs
4. Builds R packages from source
5. All artifacts are stored in `/usr/share/julia/depot`

**Key technique**: `JULIA_CPU_TARGET="generic;sandybridge,-xsaveopt,clone_all;haswell,-rdrnd,base(1)"` instructs Julia to compile each package for multiple CPU architectures, ensuring the binaries work efficiently on both old and new processors.

#### Stage 2: The Final OS (Lean Deployment)

```dockerfile
FROM quay.io/fedora/fedora-kinoite:43
```

This stage:
1. Starts from a clean Fedora Kinoite base
2. Installs only **runtime** packages (no compilers, no build tools)
3. Copies the precompiled Julia depot from the builder stage
4. Sets up environment variables and system configuration
5. Verifies all packages load correctly

**Result**: A lean, production-ready OS image with all computational infrastructure pre-installed.

### 4.3 Filesystem Layout

```
/usr/share/julia/depot/     ← Precompiled Julia packages (read-only)
/usr/lib/julia/             ← Julia runtime binaries (read-only)
/usr/lib64/R/library/       ← R packages (read-only)
/usr/bin/python3            ← Python runtime (system RPM)
/var/lib/julia/             ← Writable Julia depot (created at boot)
/home/a2rk/                 ← User home directory (persistent)
```

### 4.4 Environment Configuration

The OS sets environment variables at two levels:

**Global (`/etc/environment`)** — Read by PAM for ALL sessions (login shells, scripts, systemd services):
```
JULIA_DEPOT_PATH=/var/lib/julia:/usr/share/julia/depot
JULIA_PKG_OFFLINE=true
```

**Interactive (`/etc/profile.d/benchmark.sh`)** — Loaded on interactive login:
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

## 5. Software Stack and Language Runtimes

### 5.1 Julia 1.12.6

**What is Julia?** Julia is a high-level, high-performance programming language designed for numerical and scientific computing. It combines Python-like syntax with C-like performance through Just-In-Time (JIT) compilation using the LLVM compiler infrastructure.

**Why Julia for GIS?**
- **Performance**: Near-C speed for numerical operations
- **Multiple dispatch**: Elegant code for complex mathematical operations
- **Parallel computing**: Built-in threading and distributed computing
- **Growing GIS ecosystem**: ArchGDAL, GeoDataFrames, LibGEOS

**Julia packages pre-installed**:
| Package | Version | Purpose |
|---------|---------|---------|
| `BenchmarkTools.jl` | Latest | Precision benchmarking toolkit |
| `CSV.jl` | Latest | High-speed CSV parsing |
| `DataFrames.jl` | Latest | Tabular data manipulation |
| `SHA.jl` | Latest | Cryptographic hash functions |
| `MAT.jl` | Latest | MATLAB file format I/O |
| `JSON3.jl` | Latest | JSON parsing and generation |
| `NearestNeighbors.jl` | Latest | K-d tree spatial searches |
| `LibGEOS.jl` | Latest | Computational geometry (GEOS bindings) |
| `Shapefile.jl` | Latest | ESRI Shapefile I/O |
| `ArchGDAL.jl` | Latest | Geospatial data I/O (GDAL bindings) |
| `GeoDataFrames.jl` | Latest | Geospatial tabular data |

### 5.2 Python 3.14.x

**What is Python?** Python is the most widely used programming language for scientific computing and data science, known for its readable syntax and extensive library ecosystem.

**Python packages installed** (via Fedora RPMs):
| Package | Purpose |
|---------|---------|
| `numpy` | Numerical computing and array operations |
| `scipy` | Scientific algorithms (optimization, integration, statistics) |
| `pandas` | Tabular data manipulation |
| `matplotlib` | 2D plotting and visualization |
| `seaborn` | Statistical visualization |
| `scikit-learn` | Machine learning algorithms |
| `shapely` | Computational geometry |
| `pyproj` | Coordinate transformations |
| `fiona` | Vector data I/O |
| `rasterio` | Raster data I/O |
| `geopandas` | Geospatial tabular data |
| `xarray` | Multi-dimensional labeled arrays |
| `h5py` | HDF5 file format I/O |
| `psutil` | System and process monitoring |
| `tqdm` | Progress bars |

### 5.3 R 4.5.x

**What is R?** R is a programming language and environment specifically designed for statistical computing and graphics, widely used in academia and industry for data analysis.

**R packages pre-installed**:
| Package | Purpose |
|---------|---------|
| `terra` | Spatial data analysis (raster and vector) |
| `sf` | Simple Features (vector data) |
| `data.table` | High-performance data manipulation |
| `R.matlab` | MATLAB file format I/O |
| `FNN` | Fast Nearest Neighbor search |
| `jsonlite` | JSON parsing and generation |
| `digest` | Hash functions |

---

## 6. Benchmark Fairness and Variance Control

### 6.1 The Fairness Problem

When comparing language performance, it's critical that differences in execution time reflect **language efficiency**, not confounding variables like:
- Different BLAS (Basic Linear Algebra Subprograms) implementations
- Different thread counts
- Different CPU affinity settings
- Different memory allocation strategies

### 6.2 BLAS Synchronization via FlexiBLAS

**What is BLAS?** BLAS (Basic Linear Algebra Subprograms) is a standardized set of low-level routines for performing common linear algebra operations (matrix multiplication, dot products, etc.). High-level languages like Python (NumPy), Julia, and R all delegate these operations to a BLAS library.

**What is FlexiBLAS?** FlexiBLAS is a BLAS abstraction layer that allows switching between different BLAS implementations (OpenBLAS, Intel MKL, BLIS) at runtime without recompiling dependent software.

**Our configuration**:
```bash
# Force all languages to use OpenBLAS
flexiblas default OPENBLAS
export FLEXIBLAS=OPENBLAS-OPENMP
```

This ensures that when Python calls `numpy.dot()`, Julia calls `A * B`, or R calls `crossprod()`, they all use the **same underlying OpenBLAS code**.

### 6.3 Thread Count Lockdown

All languages are restricted to **8 threads**:
```bash
export JULIA_NUM_THREADS=8     # Julia's parallel threading
export OPENBLAS_NUM_THREADS=8  # OpenBLAS thread pool
export FLEXIBLAS_NUM_THREADS=8 # FlexiBLAS thread pool
export GOTO_NUM_THREADS=8      # GotoBLAS thread pool
export OMP_NUM_THREADS=8       # OpenMP thread pool
```

**Why 8?** The reference hardware (Intel Core i5-8350U) has 4 physical cores with Hyper-Threading (8 logical cores). Using 8 threads maximizes parallelism without oversubscribing the CPU.

### 6.4 CPU Affinity via numactl

**What is CPU Affinity?** CPU affinity binds a process to specific CPU cores, preventing the Linux scheduler from migrating it between cores. This eliminates cache invalidation and NUMA (Non-Uniform Memory Access) penalties caused by thread migration.

**What is NUMA?** NUMA is a memory architecture where some memory regions are "closer" to certain CPU cores than others. Accessing "local" memory is faster than accessing "remote" memory. Binding a process to a single NUMA node ensures consistent memory access latency.

**Our implementation** (in `run_benchmarks.sh`):
```bash
numactl --cpunodebind=0 --membind=0 --physcpubind=0-7 <benchmark_command>
```

This pins the benchmark to:
- NUMA node 0 (all memory from the same node)
- Physical cores 0-7 (all available cores)

### 6.5 Filesystem Cache Clearing

Between benchmark runs, the filesystem cache is cleared:
```bash
sync; echo 3 > /proc/sys/vm/drop_caches
```

This ensures that I/O benchmarks measure actual disk performance, not cached data from previous runs.

---

## 7. Statistical Methodology

### 7.1 Chen & Revels (2016) Framework

**Definition**: Chen & Revels (2016) established that benchmark timing measurements in modern operating systems are **non-independent and identically distributed (non-i.i.d.)** due to background interrupts, context switching, cache effects, and garbage collection pauses.

**The mathematical model**:
```
T_measured = T_true + Σ(delay_i)

where:
  T_measured = observed execution time
  T_true = true algorithmic execution time
  delay_i = individual delay factors (OS scheduling, cache misses, GC, etc.)
  delay_i ≥ 0 (delays never speed up execution)
```

**The key insight**: Since all delay factors are non-negative, the **minimum** observed time has the smallest aggregate delay contribution, making it the most accurate estimate of `T_true`.

### 7.2 Our Implementation

| Parameter | Value | Justification |
|-----------|-------|---------------|
| **Warmup runs** | 5 | Allow JIT compilation (Julia) and cache stabilization |
| **Benchmark runs** | 30 | Central Limit Theorem threshold for stable bootstrap CIs |
| **Primary metric** | Minimum execution time | Chen & Revels (2016) recommendation |
| **Context metrics** | Mean, median, std dev | Reported for completeness only |
| **Confidence intervals** | 95% Bootstrap | Non-parametric, no i.i.d. assumption |

### 7.3 Flaky Benchmark Detection

We use the **Coefficient of Variation (CV)** to detect unstable benchmarks:
```
CV = std_dev / mean
```

Benchmarks with `CV > 0.10` (10%) are flagged as "flaky" and may require additional investigation.

---

## 8. Quick Start

### 8.1 Deploy the OS

**Option A: Rebase from another bootc system**
```bash
sudo bootc switch ghcr.io/a2rk313/benchmark-bootc:latest
sudo reboot
```

**Option B: Update an existing deployment**
```bash
sudo bootc upgrade
sudo reboot
```

**Option C: Install from ISO**
1. Download the ISO from [GitHub Releases](https://github.com/a2rk313/benchmark-bootc/releases)
2. Create a bootable USB (e.g., with `dd` or Fedora Media Writer)
3. Boot from USB and follow the installer

### 8.2 Initialize the Benchmark Environment

After booting into the OS:

```bash
# Clone the research logic repository
git clone https://github.com/a2rk313/benchmark-thesis.git ~/benchmark-thesis

# Run the setup script
cd ~/benchmark-thesis
sudo ./setup-benchmarks.sh
```

### 8.3 Run Benchmarks

```bash
# Run all native benchmarks (Python, Julia, R)
./native_benchmark.sh

# Or use the full orchestrator
./run_benchmarks.sh --native-only
```

### 8.4 Verify the Setup

```bash
# Check Julia
julia -e 'using Pkg; Pkg.status()'

# Check Python
python3 -c 'import numpy, scipy, geopandas; print("OK")'

# Check R
Rscript -e 'library(sf); library(terra); cat("OK\n")'
```

---

## 9. Repository Structure

```
benchmark-bootc/
├── Containerfile              # Multi-stage OS definition (builds the image)
├── .github/
│   └── workflows/
│       ├── build.yml          # Builds and publishes the container image to GHCR
│       └── build-disk.yml     # Builds disk images (ISO, QCOW2) via BIB
├── disk_config/
│   ├── disk.toml              # BIB config for QCOW2 image (partitioning, filesystem)
│   └── iso.toml               # BIB config for ISO installer image
├── build_files/
│   └── build.sh               # Legacy build script (referenced by Containerfile)
├── docs/
│   └── APPROACH_BENCHMARKING.md  # Architectural documentation
├── Justfile                   # Build automation commands (just build, just build-qcow2)
├── AGENTS.md                  # Internal documentation for AI assistants
├── CHANGELOG.md               # Version history
├── README.md                  # This file
├── LICENSE                    # MIT License
└── .gitignore                 # Git ignore patterns
```

---

## 10. CI/CD Pipeline and Disk Image Builds

### 10.1 Container Image Build (build.yml)

**Trigger**: Push to `main` branch

**What it does**:
1. Builds the multi-stage container image using the `Containerfile`
2. Pushes the image to GitHub Container Registry (GHCR) at `ghcr.io/a2rk313/benchmark-bootc:latest`
3. The image is tagged with a date-based version (e.g., `latest.20260428`)

### 10.2 Disk Image Build (build-disk.yml)

**Trigger**: Manual dispatch or tag push (`thesis-*`)

**What it does**:
1. Pulls the container image from GHCR
2. Runs Bootc Image Builder (BIB) to create:
   - **QCOW2**: Virtual machine image (for KVM/QEMU)
   - **anaconda-iso**: Bootable installer ISO (for physical machines)
3. Splits ISO files into <1.9GB chunks (GitHub Release 2GB file limit)
4. Generates SHA256 checksums
5. Uploads to GitHub Release (on tag push) or Job Artifacts (on manual dispatch)

### 10.3 Build Commands

```bash
# Build container image locally
just build

# Build QCOW2 VM image locally
just build-qcow2
```

### 10.4 Release Process

1. **Test**: Run `just build` and verify the image works
2. **Tag**: Create a release tag (`git tag thesis-v1 && git push origin thesis-v1`)
3. **CI**: GitHub Actions builds disk images and uploads to GitHub Release
4. **Download**: Users download the release assets (ISO parts or QCOW2)

---

## 11. Troubleshooting

### 11.1 Julia Cannot Find Packages

**Symptom**: `ERROR: ArgumentError: Package MAT not found`

**Cause**: `JULIA_DEPOT_PATH` not set for non-login shells

**Fix**:
```bash
# Check current depot paths
julia -e 'println(DEPOT_PATH)'

# Expected output: ["/var/lib/julia", "/usr/share/julia/depot"]

# If empty or wrong, set manually:
export JULIA_DEPOT_PATH="/var/lib/julia:/usr/share/julia/depot"
```

### 11.2 Boot Fails After Upgrade

**Symptom**: System won't boot after `bootc upgrade`

**Fix**: At the GRUB menu, select the previous deployment (older image)

### 11.3 Permission Denied on Julia Depot

**Symptom**: `Permission denied` when loading Julia packages

**Fix**:
```bash
sudo chmod -R a+rX /usr/share/julia/depot
```

### 11.4 Disk Image Too Large for GitHub Release

GitHub Releases have a 2GB per-file limit. ISO files are split automatically:

```bash
# Reassemble the ISO
cat thesis-amd64-anaconda-iso.iso.part-* > thesis.iso

# Verify integrity
sha256sum -c SHA256SUMS
```

---

## 12. For Thesis Committee

### 12.1 Methodological Rigor

This framework ensures scientifically rigorous benchmarking through:

| Requirement | Implementation |
|-------------|----------------|
| **Bare-metal execution** | bootc boots directly on hardware, no hypervisor |
| **Variance control** | CPU affinity (numactl) + performance governor + cache clearing |
| **Statistical validity** | Minimum of 30 runs (Chen & Revels 2016) |
| **BLAS fairness** | All languages use same OpenBLAS via FlexiBLAS |
| **Reproducibility** | Immutable OS + locked package versions + content-addressable images |
| **Transparency** | Open-source code, public datasets, documented methodology |

### 12.2 Citation

```bibtex
@software{benchmark-bootc,
  author = {a2rk313},
  title = {Benchmark Bootc: Immutable OS for GIS Benchmarking},
  year = {2026},
  url = {https://github.com/a2rk313/benchmark-bootc},
  license = {MIT}
}
```

### 12.3 Thesis Integration

This OS appliance is the foundation for the thesis work described in the companion repository. The methodology follows:
- Chen & Revels (2016): Robust benchmarking in noisy environments
- Tedesco et al. (2025): Multi-scale performance benchmarking in spatio-temporal statistics

---

## 13. References

### Primary References

1. **Chen, J., & Revels, J. (2016).** *Robust benchmarking in noisy environments.* arXiv preprint arXiv:1608.04295. https://arxiv.org/abs/1608.04295

2. **Tedesco, L., Rodeschini, J., & Otto, P. (2025).** *Computational Benchmark Study in Spatio-Temporal Statistics With a Hands-On Guide to Optimise R.* Environmetrics. DOI: 10.1002/env.70017

### Technical References

3. **bootc specification.** https://containers.github.io/bootc/

4. **Fedora Silverblue.** https://fedoraproject.org/silverblue/

5. **OSTree.** https://ostreedev.github.io/ostree/

6. **Bootc Image Builder.** https://github.com/osbuild/bootc-image-builder

7. **FlexiBLAS.** https://github.com/mpimd-csc/flexiblas

8. **OpenBLAS.** https://www.openblas.net/

---

*This project is part of a Master's thesis on computational benchmarking of programming languages for GIS and Remote Sensing workflows.*
