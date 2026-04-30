# AGENTS.md — Thesis Benchmarking Framework Documentation

## Overview

This project consists of two repositories with a split-repository paradigm:

| Repository | Purpose | URL | Update Frequency |
|------------|---------|-----|------------------|
| `benchmark-bootc` | Immutable OS with language runtimes | https://github.com/a2rk313/benchmark-bootc | Rarely (infrastructure changes) |
| `benchmark-thesis` | Benchmark implementations and data | https://github.com/a2rk313/benchmark-thesis | Frequently (code changes) |

---

## Repository: benchmark-bootc

### Purpose

Creates a custom bootable OS (bootc) based on Fedora Kinoite for bare-metal benchmarking. This is the **infrastructure layer** — it provides the computational environment in which benchmarks run.

### Key Files

| File/Directory | Description |
|----------------|-------------|
| `Containerfile` | Multi-stage OS definition (Stage 1: Builder, Stage 2: Final OS) |
| `.github/workflows/build.yml` | Container image build and publish to GHCR |
| `.github/workflows/build-disk.yml` | Disk image build (ISO, QCOW2) via Bootc Image Builder |
| `disk_config/disk.toml` | BIB configuration for QCOW2 image |
| `disk_config/iso.toml` | BIB configuration for ISO installer |
| `Justfile` | Build automation commands (`just build`, `just build-qcow2`) |
| `CHANGELOG.md` | Version history |

### Build Process

```bash
# Build container image locally
just build

# Build QCOW2 VM image (for KVM/QEMU)
just build-qcow2
```

### OS Components (Installed via Containerfile)

| Component | Version | Manager | Location |
|-----------|---------|---------|----------|
| Julia | 1.12.6 | Direct binary (tarball) | `/usr/lib/julia` |
| Python | 3.14.x | System RPMs | `/usr/bin/python3` |
| R | 4.5.x | dnf5 | `/usr/bin/Rscript` |
| GDAL | 3.9.x | dnf5 | System libraries |
| PROJ | Latest | dnf5 | System libraries |
| GEOS | Latest | dnf5 | System libraries |
| HDF5 | Latest | dnf5 | System libraries |
| FFTW | Latest | dnf5 | System libraries |
| OpenBLAS | Latest | dnf5/FlexiBLAS | System libraries |
| hyperfine | Latest | dnf5 | `/usr/bin/hyperfine` |
| numactl | Latest | dnf5 | `/usr/bin/numactl` |

### Julia Packages (Pre-installed)

| Package | Purpose |
|---------|---------|
| `BenchmarkTools.jl` | Precision benchmarking toolkit |
| `CSV.jl` | High-speed CSV parsing |
| `DataFrames.jl` | Tabular data manipulation |
| `SHA.jl` | Cryptographic hash functions |
| `MAT.jl` | MATLAB file format I/O |
| `JSON3.jl` | JSON parsing and generation |
| `NearestNeighbors.jl` | K-d tree spatial searches |
| `LibGEOS.jl` | Computational geometry (GEOS bindings) |
| `Shapefile.jl` | ESRI Shapefile I/O |
| `ArchGDAL.jl` | Geospatial data I/O (GDAL bindings) |
| `GeoDataFrames.jl` | Geospatial tabular data |

### Environment Configuration

**Global (`/etc/environment`)** — Read by PAM for all sessions:
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

### Initialization Behavior

1. User boots into the OS appliance (from ISO or QCOW2)
2. User clones `benchmark-thesis` repository to a local directory:
   ```bash
   git clone https://github.com/a2rk313/benchmark-thesis.git ~/benchmark-thesis
   ```
3. User runs the setup script:
   ```bash
   cd ~/benchmark-thesis
   sudo ./setup-benchmarks.sh
   ```
4. User runs benchmarks:
   ```bash
   ./native_benchmark.sh
   ```

---

## Repository: benchmark-thesis

### Purpose

Contains all benchmark implementations, orchestration scripts, tools, and validation suites. This is the **research logic layer** — it is updated frequently as benchmarks are refined and new scenarios are added.

### Key Directories

| Directory | Description |
|-----------|-------------|
| `benchmarks/` | 9 benchmark implementations in Python, Julia, and R |
| `tools/` | Data download, visualization, comparison scripts |
| `validation/` | Cross-language validation and statistical analysis |
| `containers/` | Container definitions (Python, Julia, R) |
| `data/` | Benchmark datasets (Cuprite HSI, GPS points, etc.) |
| `results/` | Benchmark output (JSON files, figures) |
| `docs/` | Documentation files |

### Benchmark Suite

| ID | Scenario | Pattern | Languages |
|----|----------|---------|-----------|
| B1 | Matrix Operations | Dense linear algebra (BLAS/LAPACK) | Python, Julia, R |
| B2 | I/O Operations | File read/write, serialization | Python, Julia, R |
| B3 | Hyperspectral SAM | Vectorized cosine similarity | Python, Julia, R |
| B4 | Vector Point-in-Polygon | Spatial join, geometry containment | Python, Julia, R |
| B5 | IDW Interpolation | K-nearest neighbor search | Python, Julia, R |
| B6 | Time-Series NDVI | Array reduction, temporal statistics | Python, Julia, R |
| B7 | Raster Algebra | Element-wise array operations | Python, Julia, R |
| B8 | Zonal Statistics | Raster-vector overlay | Python, Julia, R |
| B9 | Coordinate Reprojection | Coordinate transformations | Python, Julia, R |

### Running Benchmarks

```bash
# On bootc OS (native, zero overhead)
./native_benchmark.sh

# Full orchestrator (native + container modes)
./run_benchmarks.sh

# Native only
./run_benchmarks.sh --native-only

# Container only
./run_benchmarks.sh --container-only

# Download datasets
python3 tools/download_data.py --all

# Generate visualizations
python3 tools/thesis_viz.py --all

# Run validation
python3 validation/thesis_validation.py --all
```

---

## Key Concepts

### Split-Repository Design

Immutable OS (`benchmark-bootc`) is separate from dynamic code (`benchmark-thesis`):
- OS rebuild: 20-30 minutes (only when dependencies change)
- Code update: Instant (`git pull` in the `benchmark-thesis` repository)

### Bare-Metal vs Container Benchmarking

| Mode | Overhead | Use Case |
|------|----------|----------|
| **Native (bootc)** | Zero | Thesis benchmarks, academic rigor |
| **Container** | ~5-15% | Development, CI/CD |

### Silverblue/OSTree Quirks

1. `/usr` is read-only at runtime — no `dnf install`
2. Data writes go to `/var` partition
3. `/var/lib/julia` is created at boot time via `tmpfiles.d`
4. Build cache mounts speed up CI builds

### Statistical Methodology

Following Chen & Revels (2016):
- **Minimum time** (min of 30 runs) as primary metric
- **Warmup runs** (5 runs) to stabilize JIT and caches
- **Flaky detection** with coefficient of variation (CV > 10%)
- **Effect sizes** (Cohen's d) for language comparisons
- **Bootstrap confidence intervals** (95%, 1000 resamples)

---

## Version Information

| Component | Version | Manager |
|-----------|---------|---------|
| Julia | 1.12.6 | Direct binary |
| Python | 3.14.x | System RPMs |
| R | 4.5.x | dnf5 |
| GDAL | 3.9.x | dnf5 |
| Fedora | 43 (Kinoite) | bootc/OSTree |
| OpenBLAS | Latest | FlexiBLAS |
| NumPy | 2.x | System RPMs |
| SciPy | Latest | System RPMs |

---

## CI/CD Pipeline

### Container Image Build (`build.yml`)

**Trigger**: Push to `main`

**Output**: Container image pushed to GHCR at `ghcr.io/a2rk313/benchmark-bootc:latest`

### Disk Image Build (`build-disk.yml`)

**Trigger**: Manual dispatch or tag push (`thesis-*`)

**Output**:
- QCOW2 VM image (uploaded to Job Artifacts)
- ISO installer (split into <1.9GB chunks, uploaded to GitHub Release on tag)

### Release Process

1. Push code to `main` → CI builds container image
2. Create tag (`git tag thesis-v1 && git push origin thesis-v1`) → CI builds disk images
3. Download ISO parts from GitHub Release → Reassemble: `cat *.part-* > thesis.iso`

---

## Common Tasks

### Adding a New Benchmark

1. Add implementation to `benchmark-thesis/benchmarks/` (create `{name}.py`, `{name}.jl`, `{name}.R`)
2. Update `benchmark-thesis/run_benchmarks.sh` to include the new benchmark
3. Test with `./run_benchmarks.sh --dry-run`
4. Commit and push to `benchmark-thesis`

### Updating OS Dependencies

1. Modify `benchmark-bootc/Containerfile` (add packages to Stage 1 or Stage 2)
2. Commit and push to trigger CI rebuild
3. Wait for GHCR image update (~20-30 min)
4. Update bootc image: `sudo bootc upgrade && sudo reboot`

### Fixing CI Build Errors

Check build logs at: https://github.com/a2rk313/benchmark-bootc/actions

Common issues:
- Julia precompilation fails → Increase RAM or reduce `JULIA_NUM_THREADS`
- Missing `python3-devel` for C extensions → Add to `dnf5 install` in Containerfile
- `/root` symlink issues (bootc) → Use `/var/roothome` instead
- ISO build fails → Add `--rootfs=ext4` flag

---

## Glossary

| Term | Definition |
|------|-----------|
| **bootc** | Bootable Containers — technology to boot OCI container images as OS |
| **OSTree** | Version-controlled filesystem system (like Git for OS files) |
| **BIB** | Bootc Image Builder — converts bootc images to bootable disk formats |
| **BLAS** | Basic Linear Algebra Subprograms — low-level math routines |
| **LAPACK** | Linear Algebra Package — higher-level math routines built on BLAS |
| **JIT** | Just-In-Time compilation — compile code at runtime (Julia) |
| **AOT** | Ahead-Of-Time compilation — precompile code before runtime |
| **LLVM** | Compiler infrastructure used by Julia for code generation |
| **FlexiBLAS** | BLAS abstraction layer that allows switching BLAS backends at runtime |
| **OpenBLAS** | Open-source BLAS implementation |
| **GDAL** | Geospatial Data Abstraction Library — raster/vector data I/O |
| **PROJ** | Cartographic projections library — coordinate transformations |
| **GEOS** | Geometry Engine, Open Source — computational geometry |
| **numactl** | NUMA control utility — bind processes to CPU cores and memory nodes |
| **NUMA** | Non-Uniform Memory Access — memory architecture with varying access latencies |
| **CV** | Coefficient of Variation — std_dev / mean, measures stability |
| **CLT** | Central Limit Theorem — statistical principle for stable sampling |
| **SAM** | Spectral Angle Mapper — hyperspectral classification algorithm |
| **NDVI** | Normalized Difference Vegetation Index — vegetation health metric |
| **IDW** | Inverse Distance Weighting — spatial interpolation method |
| **CRS** | Coordinate Reference System — spatial coordinate framework |
| **QCOW2** | QEMU Copy-On-Write version 2 — virtual machine disk format |
| **GHCR** | GitHub Container Registry — container image hosting |

---

## References

- Chen, J., & Revels, J. (2016). *Robust benchmarking in noisy environments*. arXiv:1608.04295.
- Tedesco, L., Rodeschini, J., & Otto, P. (2025). *Computational Benchmark Study in Spatio-Temporal Statistics*. Environmetrics. DOI: 10.1002/env.70017.
- bootc specification: https://containers.github.io/bootc/
- OSTree: https://ostreedev.github.io/ostree/
- Bootc Image Builder: https://github.com/osbuild/bootc-image-builder
