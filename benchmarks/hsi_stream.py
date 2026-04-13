#!/usr/bin/env python3
"""
===============================================================================
SCENARIO A.2: Hyperspectral Spectral Angle Mapper - Python Implementation
==============================================================================
Task: SAM classification on 224-band hyperspectral imagery
Dataset: NASA AVIRIS Cuprite (224 bands, freely available)
Metrics: Memory striding efficiency, cache utilization, FLOPS
==============================================================================
"""

import numpy as np
import scipy.io as sio
import sys
import json
import hashlib
from pathlib import Path
import psutil
import os


def spectral_angle_mapper(pixel_spectra, reference_spectrum):
    """
    Calculate Spectral Angle Mapper (SAM) between pixels and reference

    Args:
        pixel_spectra: Array of shape (n_pixels, n_bands)
        reference_spectrum: Array of shape (n_bands,)

    Returns:
        SAM angles in radians (array of shape n_pixels)
    """
    # Normalize to avoid numerical issues
    epsilon = 1e-8

    # Dot product: pixel · reference
    dot_product = np.dot(pixel_spectra, reference_spectrum)

    # Norms
    pixel_norms = np.linalg.norm(pixel_spectra, axis=1)
    ref_norm = np.linalg.norm(reference_spectrum)

    # Cosine of angle
    cos_angle = dot_product / (pixel_norms * ref_norm + epsilon)

    # Clip to valid range [-1, 1] to avoid numerical errors in arccos
    cos_angle = np.clip(cos_angle, -1.0, 1.0)

    # SAM angle (radians)
    angles = np.arccos(cos_angle)

    return angles


def main():
    print("=" * 70)
    print("PYTHON - Scenario A.2: Hyperspectral SAM")
    print("=" * 70)

    # =========================================================================
    # 1. Initialize
    # =========================================================================
    print("\n[1/5] Initializing...")

    # Random but reproducible reference spectrum
    np.random.seed(42)
    n_bands = 224
    reference_spectrum = np.random.rand(n_bands).astype(np.float32)
    reference_spectrum /= np.linalg.norm(reference_spectrum)  # Normalize

    print(f"  ✓ Reference spectrum: {n_bands} bands")
    print(
        f"  ✓ Reference spectrum hash: {hashlib.sha256(reference_spectrum.tobytes()).hexdigest()[:16]}"
    )

    # =========================================================================
    # 2. Open Dataset (MAT file format)
    # =========================================================================
    print("\n[2/5] Opening hyperspectral dataset...")

    hsi_path = "data/Cuprite.mat"

    print(f"  ✓ Loading MAT file: {hsi_path}")
    mat = sio.loadmat(hsi_path)
    data_key = [k for k in mat.keys() if not k.startswith("__")][0]
    raw_data = mat[data_key]

    # Cuprite.mat has shape (512, 614, 224)
    # AVIRIS Cuprite has 224 bands, so the correct layout is (bands, rows, cols)
    # Shape (512, 614, 224) -> we want (bands=224, rows=614, cols=224)
    # Transpose from (0,1,2) to (2,1,0): (512, 614, 224) -> (224, 614, 224)
    if raw_data.shape[2] == 224:
        # (bands_wrong, rows, cols) with bands=512 -> swap to get (cols, rows, bands_wrong)
        # Then take [:224,:,:] to get (224, rows, cols)
        data = raw_data.transpose(2, 1, 0)[:224, :, :]
        print(f"  ✓ Transposed data to (bands, rows, cols)")
    else:
        data = raw_data

    n_bands, n_rows, n_cols = data.shape
    print(f"  ✓ Dataset shape: {n_bands} bands × {n_rows} × {n_cols} pixels")

    file_size_gb = os.path.getsize(hsi_path) / (1024**3)
    print(f"  ✓ File size: {file_size_gb:.2f} GB")

    available_ram = psutil.virtual_memory().available / (1024**3)
    print(f"  ✓ Available RAM: {available_ram:.2f} GB")

    if file_size_gb > available_ram * 0.8:
        print(
            f"  ⚠ Dataset size exceeds 80% of available RAM - using chunked processing"
        )

    # =========================================================================
    # 3. Process in Chunks (Out-of-Core)
    # =========================================================================
    print("\n[3/5] Processing hyperspectral data (chunked I/O)...")

    chunk_size = 256

    sam_results = []
    pixels_processed = 0
    chunks_processed = 0

    for row in range(0, n_rows, chunk_size):
        for col in range(0, n_cols, chunk_size):
            row_end = min(row + chunk_size, n_rows)
            col_end = min(col + chunk_size, n_cols)

            # Extract chunk: shape (n_bands, chunk_rows, chunk_cols)
            chunk_data = data[:, row:row_end, col:col_end]
            chunk_pixels = chunk_data.shape[1] * chunk_data.shape[2]

            # Reshape to (n_pixels, n_bands): (bands, rows, cols) -> (rows*cols, bands)
            pixel_spectra = chunk_data.transpose(1, 2, 0).reshape(-1, n_bands)

            sam_angles = spectral_angle_mapper(pixel_spectra, reference_spectrum)

            sam_results.extend(sam_angles.tolist())
            pixels_processed += len(sam_angles)
            chunks_processed += 1

            if chunks_processed % 10 == 0:
                print(
                    f"    Processed {chunks_processed} chunks ({pixels_processed:,} pixels)...",
                    end="\r",
                )

    print(
        f"    Processed {chunks_processed} chunks ({pixels_processed:,} pixels)... Done!"
    )

    # =========================================================================
    # 4. Compute Statistics
    # =========================================================================
    print("\n[4/5] Computing statistics...")

    sam_array = np.array(sam_results)

    mean_sam = float(np.mean(sam_array))
    median_sam = float(np.median(sam_array))
    std_sam = float(np.std(sam_array))
    min_sam = float(np.min(sam_array))
    max_sam = float(np.max(sam_array))

    print(f"  ✓ Mean SAM: {mean_sam:.6f} radians ({np.degrees(mean_sam):.2f}°)")
    print(f"  ✓ Median SAM: {median_sam:.6f} radians")
    print(f"  ✓ Std Dev: {std_sam:.6f} radians")
    print(f"  ✓ Range: [{min_sam:.6f}, {max_sam:.6f}] radians")

    # =========================================================================
    # 5. Validation & Export
    # =========================================================================
    print("\n[5/5] Generating validation data...")

    # Generate validation hash
    result_str = f"{mean_sam:.8f}_{pixels_processed}_{median_sam:.8f}"
    result_hash = hashlib.sha256(result_str.encode()).hexdigest()[:16]

    print(f"  ✓ Validation hash: {result_hash}")

    # Export results
    results = {
        "language": "python",
        "scenario": "hyperspectral_sam",
        "pixels_processed": pixels_processed,
        "chunks_processed": chunks_processed,
        "n_bands": n_bands,
        "mean_sam_rad": mean_sam,
        "median_sam_rad": median_sam,
        "std_sam_rad": std_sam,
        "min_sam_rad": min_sam,
        "max_sam_rad": max_sam,
        "mean_sam_deg": float(np.degrees(mean_sam)),
        "validation_hash": result_hash,
        "reference_hash": hashlib.sha256(reference_spectrum.tobytes()).hexdigest()[:16],
    }

    # Save results
    output_dir = Path("validation")
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "raster_python_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n  ✓ Results saved to validation/raster_python_results.json")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
