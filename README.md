# benchmark-bootc

Custom bootc image for thesis benchmarking: Julia vs Python vs R for GIS/Remote Sensing workflows.

## What's Included

- **R 4.5.x** - Statistical computing
- **Julia 1.11.x** - High-performance computing
- **Python 3.14** - General programming
- **GIS Packages**: GDAL, proj, geos, rasterio, geopandas, terra, sf
- **Benchmark Suite**: All 9 benchmarks × 3 languages

## Quick Start

### Build Locally

```bash
# Build container image
just build

# Build and run VM
just run-vm

# Build ISO
just build-iso
```

### Build via GitHub Actions

Push to main → Actions builds automatically → Image at `ghcr.io/<user>/benchmark-bootc:latest`

### Rebase Your System

```bash
# From a bootc system (Bluefin, Fedora Atomic, etc.)
sudo bootc switch ghcr.io/<user>/benchmark-bootc:latest
sudo bootc apply
reboot
```

## Run Benchmarks

```bash
# Run all benchmarks
./run_benchmarks.sh

# Run specific language
python3 benchmarks/matrix_ops.py
julia benchmarks/matrix_ops.jl
Rscript benchmarks/matrix_ops.R

# Native benchmark (no containers)
./native_benchmark.sh
```

## Base Image

- **Base**: `ghcr.io/ublue-os/silverblue-main:latest`
- **OS**: Fedora 43

## Repository Structure

```
benchmark-bootc/
├── Containerfile              # Image definition
├── build_files/
│   └── build.sh              # Package installation script
├── benchmarks/               # Benchmark implementations
│   ├── matrix_ops.py/jl/R
│   ├── io_ops.py/jl/R
│   └── ...
├── tools/                   # Analysis tools
│   ├── thesis_viz.py
│   └── ...
├── validation/              # Validation scripts
└── Justfile                 # Build commands
```

## For Thesis

This image provides reproducible bare-metal benchmarking environment:

1. **Version pinned**: R 4.5.x, Julia 1.11.x, Python 3.14
2. **All packages included**: No external dependencies
3. **GitHub Actions CI**: Automated builds
4. **Image digest pinning**: Exact reproducibility

## Community

- [Universal Blue Forums](https://universal-blue.discourse.group/)
- [Universal Blue Discord](https://discord.gg/WEu6BdFEtp)
- [bootc discussions](https://github.com/bootc-dev/bootc/discussions)
