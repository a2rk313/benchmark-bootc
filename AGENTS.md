# Thesis Benchmarking Framework - Agent Documentation

## Overview

This project consists of two repositories with a split-repository paradigm:

| Repository | Purpose | Update Frequency |
|------------|---------|------------------|
| `benchmark-bootc` | Immutable OS with language runtimes | Rarely (infrastructure) |
| `benchmark-thesis` | Benchmark scripts and data | Frequently (code changes) |

---

## Repository: benchmark-bootc

### Purpose
Creates a custom bootable OS (bootc) based on Fedora Silverblue for bare-metal benchmarking.

### Key Files

| File/Directory | Description |
|----------------|-------------|
| `Containerfile` | Defines the bootc OS build |
| `build_files/build.sh` | Installs Julia, Python, R, and GIS libraries |
| `firstboot/` | Systemd service to clone benchmark-thesis on first boot |
| `native_benchmark.sh` | Orchestrates native benchmarks |
| `Justfile` | VM image build commands |

### Build Process

```bash
# Local build
just build

# Build VM image (QCOW2)
just build-qcow2
```

### OS Components (Installed via build.sh)

- **Julia 1.12.x** → `/opt/julia`
- **Python 3.x** via uv → system-wide
- **R 4.5.x** with spatial packages
- **GIS Libraries**: GDAL, PROJ, GEOS, HDF5, FFTW, OpenBLAS
- **Benchmarking**: hyperfine, time

### First-Boot Behavior

1. Systemd service `benchmark-firstboot.service` triggers after network is online
2. Clones `https://github.com/a2rk313/benchmark-thesis.git` to `/benchmarks`
3. Downloads datasets to `/benchmarks/data`
4. Symlinks orchestrators to `/usr/local/bin`

---

## Repository: benchmark-thesis

### Purpose
Contains all benchmark implementations, tools, and validation scripts.

### Key Directories

| Directory | Description |
|-----------|-------------|
| `benchmarks/` | 9 benchmark implementations in Python, Julia, R |
| `tools/` | Data download, visualization, comparison scripts |
| `validation/` | Cross-language validation and statistical analysis |
| `containers/` | Alternative container-based benchmarking |
| `data/` | Benchmark datasets (Cuprite HSI, GPS points, etc.) |

### Benchmark Suite

1. **Matrix Operations** - BLAS/LAPACK performance
2. **I/O Operations** - CSV, GeoTIFF, Shapefile handling
3. **Hyperspectral Analysis** - AVIRIS Cuprite SAM
4. **Vector Operations** - Point-in-polygon tests
5. **Interpolation** - Inverse Distance Weighting (IDW)
6. **Time-Series NDVI** - MODIS-like processing
7. **Raster Algebra** - Band math, NDVI calculation
8. **Zonal Statistics** - Zone-based aggregations
9. **Coordinate Reprojection** - CRS transformations

### Running Benchmarks

```bash
# Container-based (uses GHCR images)
./run_benchmarks.sh

# Native on bootc OS
native_benchmark.sh

# Or after first-boot setup
cd /benchmarks && ./run_benchmarks.sh --native-only
```

---

## Key Concepts

### Split-Repository Design

Immutable OS (benchmark-bootc) is separate from dynamic code (benchmark-thesis):
- OS rebuild: 20-30 minutes (only when deps change)
- Code update: Instant (git pull in /benchmarks)

### Bare-Metal vs Container Benchmarking

| Mode | Overhead | Use Case |
|------|----------|----------|
| **Native (bootc)** | Zero | Thesis benchmarks, academic rigor |
| **Container** | ~5-15% | Development, CI/CD |

### Silverblue/OSTree Quirks

1. `/root` is a symlink to `/var/roothome` - build.sh handles this
2. `/usr` is read-only at runtime
3. Data writes go to `/var` partition
4. Build cache mounts speed up CI builds

### Statistical Methodology

- **Minimum time** (min of 30 runs) per Chen & Revels (2016)
- **Warmup runs** to stabilize JIT
- **Flaky detection** with coefficient of variation thresholds
- **Effect sizes** (Cohen's d) for language comparisons

---

## Common Tasks

### Adding a New Benchmark

1. Add implementation to `benchmark-thesis/benchmarks/`
2. Update `benchmark-thesis/run_benchmarks.sh`
3. Test with `./run_benchmarks.sh --dry-run`

### Updating OS Dependencies

1. Modify `benchmark-bootc/build_files/build.sh`
2. Commit and push to trigger CI rebuild
3. Wait for GHCR image update (~15-20 min)

### Fixing CI Build Errors

Check build logs at: https://github.com/a2rk313/benchmark-bootc/actions

Common issues:
- Missing `python3-devel` for C extensions
- `/root` symlink issues (use `mkdir -p /var/roothome`)
- uv installation failures (install directly from tar.gz)

---

## Version Information

| Component | Version | Manager |
|-----------|---------|---------|
| Julia | 1.12.x | Direct binary |
| Python | 3.13.x | uv |
| R | 4.5.x | dnf5 |
| GDAL | 3.9.x | dnf5 |
| Fedora | 43 | rpm-ostree |

---

## References

- Chen & Revels (2016): Robust Benchmarking in Noisy Environments
- Tedesco et al. (2025): Multi-scale performance benchmarking
- bootc specification: https://github.com/containers/bootc
