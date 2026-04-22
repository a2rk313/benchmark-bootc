# benchmark-bootc

Custom bootable OS (bootc) for thesis benchmarking: Julia vs Python vs R for GIS/Remote Sensing workflows.

## Architecture

This project uses a **Split-Repository Design** for maximum flexibility:

| Repository | Purpose | Size |
|------------|---------|------|
| `benchmark-bootc` | Immutable OS with language runtimes | ~6-8 GB |
| `benchmark-thesis` | Benchmark scripts and datasets | Downloaded at first boot |

### Why Split Design?

- **Immutable OS**: Rebuilt only when dependencies change (20-30 min build)
- **Dynamic Code**: Updated instantly via git pull
- **Scientific Rigor**: Zero container/virtualization overhead for accurate timing

## What's Included in the OS

- **Julia 1.11.x** → Precompiled AOT spatial packages
- **Python 3.x** via uv → NumPy, SciPy, GeoPandas, Rasterio
- **R 4.5.x** → terra, sf, data.table
- **GIS Libraries**: GDAL, PROJ, GEOS, HDF5, FFTW, OpenBLAS
- **Benchmarking Tools**: hyperfine, time

## Quick Start

### 1. Deploy or Update the OS

```bash
# Option A: Rebase from another bootc system
sudo bootc switch ghcr.io/a2rk313/benchmark-bootc:latest
sudo bootc apply
reboot

# Option B: Update an existing deployment
sudo rpm-ostree upgrade
# Or specifically by deployment index if multiple are present
# sudo rpm-ostree upgrade [index]
sudo reboot

# Option C: Build VM locally
just build-qcow2
```

### 2. First Boot (Automatic)

The system automatically:
1. Clones `benchmark-thesis` to `/benchmarks`
2. Downloads datasets to `/benchmarks/data`
3. Installs benchmarks into your $PATH

### 3. Run Benchmarks

```bash
# Quick benchmark (matrix operations)
native_benchmark.sh

# Full suite
cd /benchmarks && ./run_benchmarks.sh --native-only
```

## Repository Structure

```
benchmark-bootc/
├── Containerfile              # bootc OS definition
├── build_files/
│   └── build.sh              # Package installation (Julia, Python, R, GIS)
├── firstboot/
│   ├── first-boot-setup.sh   # Clones benchmark-thesis
│   └── benchmark-firstboot.service  # Systemd unit
├── native_benchmark.sh        # Benchmark orchestrator
├── Justfile                  # VM build commands
├── docs/
│   └── APPROACH_BENCHMARKING.md  # Full architecture docs
└── AGENTS.md                # Agent/internals documentation
```

## For Thesis

This OS ensures **scientifically rigorous** benchmarking:

| Requirement | Implementation |
|-------------|----------------|
| Bare-metal execution | bootc → direct hardware |
| No container overhead | Native execution |
| Statistical validity | min(t) of 30 runs (Chen & Revels 2016) |
| Reproducibility | Immutable OS + pinned versions |
| AOT compilation | Julia packages precompiled |

### Image Size Optimization

| Technique | Savings |
|-----------|--------|
| Weak deps disabled | ~4 GB |
| Aggressive cache purge | ~1 GB |
| No benchmarks in image | ~2 GB |

**Result**: 6-8 GB image (vs original 13 GB)

## Community

- [Universal Blue Forums](https://universal-blue.discourse.group/)
- [Universal Blue Discord](https://discord.gg/WEu6BdFEtp)
- [bootc discussions](https://github.com/bootc-dev/bootc/discussions)

## Documentation

- [APPROACH_BENCHMARKING.md](docs/APPROACH_BENCHMARKING.md) - Full architectural documentation
- [AGENTS.md](AGENTS.md) - Internal agent documentation
