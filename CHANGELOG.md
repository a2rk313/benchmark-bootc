# Changelog

All notable changes to the `benchmark-bootc` project will be documented in this file.

## [Unreleased] - 2026-04-21

### Added
- **Repository Validation**: `first-boot-setup.sh` now validates the repository structure after cloning.
- **Memory Safety**: Added a memory check in `build.sh` before memory-intensive Julia precompilation.
- **Robust Pathing**: Implemented dynamic `PYTHONPATH` detection in `native_benchmark.sh` to handle Python version changes.
- **Data Safety**: Added file existence checks to `hsi_stream.jl` and `zonal_stats.R` to prevent runtime crashes.

### Changed
- **UV Pinning**: Pinned the `uv` package manager to version `0.6.4` for reproducible builds.
- **Julia Depot Persistence**: Moved the Julia depot to `/var/lib/julia/depot` to ensure precompiled packages survive bootc system updates.
- **SSL Verification**: Explicitly enabled SSL verification for first-boot repository cloning.

### Fixed
- **Fiona Build Error**: Added `python3-setuptools` and `python3-wheel` to fix dependency issues during image construction.
- **Algorithmic Parity**: Standardized `matrix_ops.py` and axis transposition in `raster_algebra.py`.
- **Bootloader Recovery**: Integrated `grub2` and `efibootmgr` tools directly into the image.

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
