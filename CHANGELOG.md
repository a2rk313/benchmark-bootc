# Changelog

All notable changes to the `benchmark-bootc` project will be documented in this file.

## [Unreleased] - 2026-04-21

### Added
- **Expanded Benchmark Runner**: `native_benchmark.sh` now supports 9 core thesis scenarios (Matrix Ops, Raster Algebra, Zonal Stats, Vector PiP, NDVI Time Series, Reprojection, Interpolation, HSI Stream, and I/O Ops).
- **Persistent Results Storage**: Benchmark results are now automatically saved to `/var/benchmarks/results/native/` to ensure they survive reboots and OS updates.
- **Deep Precompilation (Warmup)**: Added a "Warmup" phase to `build.sh` that triggers binary cache generation for heavy GIS packages (ArchGDAL, GeoDataFrames) during the image build.
- **Environment Persistence**: Added `/etc/profile.d/benchmark.sh` to ensure `PYTHONPATH` and `JULIA_DEPOT_PATH` are available in interactive login shells.

### Changed
- **Architectural Refactor**: Replaced manual multi-stage copying in `Containerfile` with a consolidated execution of the robust `build_files/build.sh` script.
- **Base Image Update**: Switched from `fedora-kinoite` to the standard `quay.io/fedora/fedora-bootc:43` for better server-side deployment stability.
- **Optimized build.sh**: Refactored the Julia installation to preserve `artifacts/` and `compiled/` directories, preventing the loss of critical C++ shared libraries.
- **Improved First-Boot Guard**: Restored `ConditionPathExists` in `benchmark-firstboot.service` to ensure the 8GB data download only occurs once.

### Fixed
- **Runtime Pathing**: Fixed "command not found" errors for `julia`, `python3`, and `uv` by explicitly symlinking binaries to `/usr/bin` during the OS build.
- **Buildah Exit Error**: Fixed a failure in the `Containerfile` caused by a redundant `rm /tmp/build.sh` command (as the script now cleans itself up).
- **Julia Binary Stability**: Fixed a critical bug where Julia artifacts were being deleted during image optimization, causing runtime crashes in spatial packages.

### Documentation
- Updated `README.md` and `docs/APPROACH_BENCHMARKING.md` to include instructions for updating existing deployments using `rpm-ostree upgrade [index]`.
- Added Cloud Benchmarking guidance for Oracle Cloud (Always Free) ARM instances.
