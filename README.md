# benchmark-bootc

Custom bootable OS (bootc) for thesis benchmarking. This repository provides the **Infrastructure (OS Appliance)**, while the benchmarking logic and datasets reside in the [benchmark-thesis](https://github.com/a2rk313/benchmark-thesis.git) repository.

## Architecture

This project uses a **Strict Decoupling Design** for maximum agility:

| Layer | Repository | Responsibility |
| :--- | :--- | :--- |
| **Appliance** | `benchmark-bootc` | OS, Julia/R/Python runtimes, Geospatial C++ libs, BLAS synchronization. |
| **Logic** | `benchmark-thesis` | Orchestration scripts, benchmark algorithms, validation, and datasets. |

### Why Strict Decoupling?

- **Fast Iteration**: Modify benchmark scripts and pull changes instantly without rebuilding the 8GB OS image.
- **Pure Environment**: The OS is a "clean-room" appliance with zero background noise from development tools.
- **Scientific Rigor**: Runtimes are locked and tuned in the appliance layer; logic is updated in the research layer.

## Quick Start

### 1. Deploy or Update the OS

```bash
# Option A: Rebase from another bootc system
sudo bootc switch ghcr.io/a2rk313/benchmark-bootc:latest
sudo bootc apply
reboot

# Option B: Update an existing deployment
sudo rpm-ostree upgrade
sudo reboot
```

### 2. Initialize Benchmarking Environment

After booting into the OS, clone the logic repository and run the setup utility:

```bash
# Clone the logic repository to the writable partition
git clone https://github.com/a2rk313/benchmark-thesis.git /benchmarks

# Run the setup script (interactive)
cd /benchmarks
sudo ./setup-benchmarks.sh
```

### 3. Run Benchmarks

```bash
# Use the optimized native runner from inside the benchmarks repo
./native_benchmark.sh
```

## What's Included in the OS Appliance

- **Julia 1.12.6** → Precompiled AOT spatial packages (ArchGDAL, GeoDataFrames)
- **Python 3.14.x** → Native Fedora RPMs (NumPy 2.x, SciPy, GeoPandas)
- **R 4.5.x** → Native RPMs + optimized geospatial packages
- **BLAS Synchronization**: Force-pinned OpenBLAS backend via FlexiBLAS
- **System Tuning**: `numactl` and `cpupower` for CPU affinity and governor control

## Repository Structure

```
benchmark-bootc/
├── Containerfile              # Appliance definition (Multi-stage)
├── build_files/               # Legacy build logic (referenced by Containerfile)
├── disk_config/               # BIB configurations for ISO/QCOW2
├── docs/                      # Architectural documentation
└── CHANGELOG.md               # Version history
```

## For Thesis

This framework ensures **scientifically rigorous** benchmarking:

| Requirement | Implementation |
|-------------|----------------|
| Bare-metal execution | bootc → direct hardware |
| Variance Control | CPU Affinity (numactl) + Performance Governor |
| Statistical validity | min(t) of 30 runs (Chen & Revels 2016) |
| Reproducibility | Immutable OS + Unified BLAS environment |

## Documentation

- [APPROACH_BENCHMARKING.md](docs/APPROACH_BENCHMARKING.md) - Full architectural documentation
- [AGENTS.md](AGENTS.md) - Internal agent documentation
