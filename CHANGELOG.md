# Changelog

All notable changes to the `benchmark-bootc` project will be documented in this file.

## [Unreleased] - 2026-04-21

### Added
- **GUI & Headless Dual-Mode**: Switched base image to `fedora-kinoite:43` (KDE Plasma) to support GUI benchmarking.
- **Toggle Script**: Added `toggle_gui.sh --headless` and `toggle_gui.sh --gui` to easily switch between Desktop and Server modes on the same image.
- **Desktop Tax Analysis**: `native_benchmark.sh` now automatically detects and logs whether it is running in a Graphical or Multi-user environment.
- **Bootloader Recovery**: Integrated `grub2` and `efibootmgr` tools directly into the image to resolve "bootloader update failed" errors during `bootc switch/upgrade` operations.
- **Expanded Benchmark Runner**: `native_benchmark.sh` now supports 9 core thesis scenarios.

### Changed
- **Architectural Refactor**: Replaced manual multi-stage copying in `Containerfile` with a consolidated execution of the robust `build_files/build.sh` script.
- **Unified Image Strategy**: Standardized on `fedora-kinoite:43` as the single base image, providing a GUI-capable environment that can be converted to a minimal headless state via the `toggle_gui.sh` script.
- **Optimized build.sh**: Refactored the Julia installation to preserve `artifacts/` and `compiled/` directories, preventing the loss of critical C++ shared libraries.
- **Improved First-Boot Guard**: Restored `ConditionPathExists` in `benchmark-firstboot.service` to ensure the 8GB data download only occurs once.

### Fixed
- **Runtime Pathing**: Fixed "command not found" errors for `julia`, `python3`, and `uv` by explicitly symlinking binaries to `/usr/bin` during the OS build.
- **Buildah Exit Error**: Fixed a failure in the `Containerfile` caused by a redundant `rm /tmp/build.sh` command (as the script now cleans itself up).
- **Julia Binary Stability**: Fixed a critical bug where Julia artifacts were being deleted during image optimization, causing runtime crashes in spatial packages.

### Documentation
- Updated `README.md` and `docs/APPROACH_BENCHMARKING.md` to include instructions for updating existing deployments using `rpm-ostree upgrade [index]`.
- Added Cloud Benchmarking guidance for Oracle Cloud (Always Free) ARM instances.
