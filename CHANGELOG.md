# Changelog

All notable changes to the `benchmark-bootc` project will be documented in this file.

## [Unreleased] - 2026-04-21

### Added
- **Repository Validation**: `first-boot-setup.sh` now validates the repository structure after cloning.
- **Memory Safety**: Added a memory check in the builder stage before memory-intensive Julia precompilation.
- **Robust Pathing**: Implemented dynamic `PYTHONPATH` detection in `native_benchmark.sh` to handle Python version changes.
- **Data Safety**: Added file existence checks to `hsi_stream.jl` and `zonal_stats.R` to prevent runtime crashes.
- **GUI & Headless Dual-Mode**: Switched base image to `fedora-kinoite:43` (KDE Plasma) to support GUI benchmarking.
- **Toggle Script**: Added `toggle_gui.sh --headless` and `toggle_gui.sh --gui` to easily switch between Desktop and Server modes on the same image.
- **Desktop Tax Analysis**: `native_benchmark.sh` now automatically detects and logs whether it is running in a Graphical or Multi-user environment.

### Changed
- **Architectural Refactor**: Reinstated the robust **multi-stage build** in `Containerfile`. This isolates the heavy compilation (Stage 1) from the final lean OS (Stage 2), ensuring build-time dependencies like `Cython` and `setuptools` do not pollute the final image while resolving source-build errors for `fiona`.
- **Unified Image Strategy**: Standardized on `fedora-kinoite:43` as the single base image, providing a GUI-capable environment that can be converted to a minimal headless state via the `toggle_gui.sh` script.
- **Optimized Builder**: Integrated all Julia, Python, and R installations directly into the `Containerfile` builder stage for better layer caching and reproducibility.
- **Improved First-Boot Guard**: Restored `ConditionPathExists` in `benchmark-firstboot.service` to ensure the 8GB data download only occurs once.

### Fixed
- **Fiona Build Error**: Added `Cython`, `setuptools`, and `wheel` to the builder stage to fix compilation errors for geospatial Python packages on Python 3.14.
- **Runtime Pathing**: Fixed "command not found" errors for `julia`, `python3`, and `uv` by explicitly symlinking binaries to `/usr/bin` during the OS build.
- **Julia Binary Stability**: Fixed a critical bug where Julia artifacts were being deleted during image optimization, causing runtime crashes in spatial packages.
- **Bootloader Recovery**: Integrated `grub2` and `efibootmgr` tools directly into the image to resolve "bootloader update failed" errors during `bootc switch/upgrade` operations.

### Documentation
- Updated `README.md` and `docs/APPROACH_BENCHMARKING.md` to include instructions for updating existing deployments using `rpm-ostree upgrade [index]`.
- Added Cloud Benchmarking guidance for Oracle Cloud (Always Free) ARM instances.
