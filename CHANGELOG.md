# Changelog

All notable changes to the `benchmark-bootc` project will be documented in this file.

## [Unreleased] - 2026-04-22

### Added
- **Strict Decoupling Design**: Completely separated the **OS Appliance** (`benchmark-bootc`) from the **Research Logic** (`benchmark-thesis`). This ensures that changes to benchmark scripts never require an 8GB OS image rebuild.
- **Manual Setup Workflow**: Introduced `setup-benchmarks.sh` as an interactive utility for users to initialize the benchmarking environment upon booting the appliance.
- **CPU Affinity Locking**: Integrated `numactl --physcpubind` into the native orchestrator to eliminate Linux scheduler noise.

### Changed
- **Appliance-Only Containerfile**: Refactored the OS definition to strictly provide runtimes and libraries. All custom orchestration scripts have been migrated to the logic repository.
- **Julia Depot Parity**: Synchronized `JULIA_DEPOT_PATH` across both build and runtime stages for perfect binary cache validity.
- **Explicit BLAS Pinning**: Replaced dynamic FlexiBLAS detection with an explicit `OPENBLAS` backend lock for absolute fairness.

### Documentation
- Updated `README.md` and `docs/APPROACH_BENCHMARKING.md` to reflect the new decoupled architecture and manual initialization workflow.

## [Unreleased] - 2026-04-21

### Added
- **Manual Setup Utility**: Replaced the automated first-boot service with a user-friendly `setup-benchmarks.sh` script for full visibility and control over the environment initialization.
- **Repository Structure Validation**: `setup-benchmarks.sh` now validates the repository and data structure interactively.
- **Memory Safety**: Added a memory check in the builder stage before memory-intensive Julia precompilation.
- **Data Safety**: Added file existence checks to `hsi_stream.jl` and `zonal_stats.R` to prevent runtime crashes.
- **GUI & Headless Dual-Mode**: Switched base image to `fedora-kinoite:43` (KDE Plasma) to support GUI benchmarking.
- **Toggle Script**: Added `toggle_gui.sh --headless` and `toggle_gui.sh --gui` to easily switch between Desktop and Server modes on the same image.

### Changed
- **Architectural Simplification**: Completely refactored the Python environment to use pre-compiled **native Fedora RPM packages** instead of source-building via `uv`. This eliminates compilation errors and ensures maximum runtime stability.
- **Removed Automation**: Deleted the `benchmark-firstboot.service` to prevent background "magic" failures and provide a more standard appliance experience.
- **Architectural Refactor**: Reinstated the robust **multi-stage build** in `Containerfile`. This isolates the heavy compilation (Stage 1) from the final lean OS (Stage 2).
- **Julia Depot Persistence**: Moved the Julia depot to `/var/lib/julia/depot` to ensure precompiled packages survive bootc system updates.

### Fixed
- **Fiona Build Error**: Added `Cython`, `setuptools`, and `wheel` to the builder stage to fix compilation errors for geospatial Python packages on Python 3.14.
- **Runtime Pathing**: Fixed "command not found" errors for `julia`, `python3`, and `uv` by explicitly symlinking binaries to `/usr/bin` during the OS build.
- **Julia Binary Stability**: Fixed a critical bug where Julia artifacts were being deleted during image optimization.
- **Bootloader Recovery**: Integrated `grub2` and `efibootmgr` tools directly into the image to resolve "bootloader update failed" errors.
