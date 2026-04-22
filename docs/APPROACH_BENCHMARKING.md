# Comprehensive Architectural Documentation: bootc Environment for GIS Benchmarking

## 1. Abstract & Academic Rationale

This document outlines the system architecture and containerization methodologies used to construct the benchmark-bootc operating system. The primary objective of this environment is to facilitate scientifically rigorous, reproducible performance benchmarking of Geographic Information Systems (GIS) and remote sensing workloads across Python, R, and Julia.

To satisfy the "minimum-time" statistical validity methodology outlined by Chen & Revels (2016), it is imperative to eliminate systemic interference, such as hypervisor "noisy neighbor" effects and containerization overhead. By utilizing the Bootable Containers (bootc) standard, this project creates a custom, immutable Linux distribution that boots directly onto bare-metal hardware. This ensures that recorded execution times reflect the raw performance of the underlying language engines and C++ geospatial libraries, completely free from virtualization taxes.

---

## 2. System Architecture: The Strict Decoupling Design

To balance scientific stability with research agility, this project employs a **Strict Decoupling Architecture**. The system is divided into two distinct layers:

### 2.1. The Appliance Layer (benchmark-bootc)

This repository serves as the **Hardware-as-Code (HaC)** foundation. It is responsible for:
- Defining the OS kernel and immutable filesystem.
- Installing the high-performance C++ geospatial stack (GDAL, PROJ, GEOS).
- Providing optimized language runtimes (Julia 1.12.6, Python 3.14.x, R 4.5.x).
- Enforcing BLAS synchronization and CPU affinity tools (`numactl`).
- Standardizing the benchmarking environment through unified environment variables.

The appliance is built as a multi-stage bootc image, ensuring a "clean-room" environment for the runtimes.

### 2.2. The Logic Layer (benchmark-thesis)

This repository contains the **Research Logic**. It is decoupled from the OS image and is cloned at runtime by the user. It contains:
- Identical algorithmic implementations in Julia, Python, and R.
- Orchestration scripts (`setup-benchmarks.sh`, `native_benchmark.sh`).
- Dataset management and validation suites.
- Statistical visualization tools.

### 2.3. The Interface: Manual Initialization

Users boot the immutable appliance and then initialize the logic layer:
1. **Clone**: `git clone https://github.com/a2rk313/benchmark-thesis.git /benchmarks`
2. **Setup**: `cd /benchmarks && sudo ./setup-benchmarks.sh`
3. **Execute**: `./native_benchmark.sh`

---

## 3. Fedora bootc & OSTree Internals

The appliance is built on Fedora Kinoite, utilizing the bootc standard for OCI-native image updates.

### 3.1. Immutable Filesystem Management

In bootc systems, `/usr` is mounted as a read-only filesystem. To ensure research data survives updates and reboots, the appliance uses a dedicated writable partition:
- `/var/benchmarks` is created during the build.
- `/benchmarks` is symlinked to this writable location.
- `/data` is symlinked to `/benchmarks/data` for path consistency.

### 3.2. Julia Depot Optimization

Julia's JIT nature requires precompiled binary caches to prevent timing contamination. The appliance synchronizes the `JULIA_DEPOT_PATH` to `/usr/share/julia/depot` during both the build and runtime stages. This ensures that AOT (Ahead-of-Time) precompiled GIS packages are valid and available with zero first-run overhead.

---

## 4. Benchmark Fairness & Variance Control

A core requirement for the thesis is a "level playing field" for all three language ecosystems.

### 4.1. BLAS Synchronization

All three runtimes are forced to use the same OpenBLAS backend via FlexiBLAS:
```bash
flexiblas default OPENBLAS
```
Thread counts are locked to 8 across all ecosystems via:
- `JULIA_NUM_THREADS=8`
- `OPENBLAS_NUM_THREADS=8`
- `OMP_NUM_THREADS=8`

### 4.2. CPU Affinity (Variance Killer)

To eliminate Linux scheduler noise, the `native_benchmark.sh` orchestrator uses `numactl --physcpubind=0-7`. This locks the benchmark process to specific physical cores, preventing thread migration and ensuring maximum consistency across independent runs.

---

## 5. Repository Structure

```
benchmark-bootc/
├── Containerfile              # Appliance definition (Multi-stage)
├── build_files/               # Legacy build logic (referenced by Containerfile)
├── disk_config/               # BIB configurations for ISO/QCOW2
├── docs/                      # Architectural documentation
└── CHANGELOG.md               # Version history
```

```
benchmark-thesis/
├── benchmarks/                # Python, Julia, R implementations
├── tools/                     # Data download, visualization
├── setup-benchmarks.sh        # Environment initialization utility
├── native_benchmark.sh        # Optimized benchmark runner
├── toggle_gui.sh              # Desktop Tax toggle (GUI vs Headless)
└── ...
```

---

## 6. Conclusion

By separating the **Appliance** from the **Logic**, this architecture provides a high-fidelity scientific instrument that is both stable and agile. Research logic can be updated instantly via Git, while the underlying computational foundation remains immutable, reproducible, and highly tuned for bare-metal geoinformatics performance.
