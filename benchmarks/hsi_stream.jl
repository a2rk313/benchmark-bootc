#!/usr/bin/env julia
"""
===============================================================================
SCENARIO A.2: Hyperspectral Spectral Angle Mapper - Julia Implementation
==============================================================================
Task: SAM classification on 224-band hyperspectral imagery
Dataset: NASA AVIRIS Cuprite (224 bands, freely available)
Metrics: Memory striding efficiency, zero-copy views, SIMD vectorization
==============================================================================
"""

using MAT
using Statistics
using LinearAlgebra
using SHA
using JSON3
using Random

"""
Calculate Spectral Angle Mapper (SAM) between pixels and reference

Args:
    pixel_spectra: Matrix of shape (n_pixels, n_bands)
    reference_spectrum: Vector of shape (n_bands,)

Returns:
    SAM angles in radians (vector of length n_pixels)
"""
function spectral_angle_mapper(pixel_spectra::Matrix{Float32}, reference_spectrum::Vector{Float32})
    epsilon = Float32(1e-8)
    
    # Dot product: pixel · reference
    dot_products = pixel_spectra * reference_spectrum
    
    # Norms
    pixel_norms = [norm(pixel_spectra[i, :]) for i in 1:size(pixel_spectra, 1)]
    ref_norm = norm(reference_spectrum)
    
    # Cosine of angle
    cos_angles = dot_products ./ (pixel_norms .* ref_norm .+ epsilon)
    
    # Clip to valid range [-1, 1]
    cos_angles = clamp.(cos_angles, -1.0f0, 1.0f0)
    
    # SAM angle (radians)
    angles = acos.(cos_angles)
    
    return angles
end

function main()
    println("=" ^ 70)
    println("JULIA - Scenario A.2: Hyperspectral SAM")
    println("=" ^ 70)
    
    # =========================================================================
    # 1. Initialize
    # =========================================================================
    println("\n[1/5] Initializing...")
    
    # Random but reproducible reference spectrum
    Random.seed!(42)
    n_bands = 224
    reference_spectrum = rand(Float32, n_bands)
    reference_spectrum ./= norm(reference_spectrum)  # Normalize
    
    println("  ✓ Reference spectrum: $n_bands bands")
    ref_hash = bytes2hex(sha256(reinterpret(UInt8, reference_spectrum)))[1:16]
    println("  ✓ Reference spectrum hash: $ref_hash")
    
    # =========================================================================
    # 2. Open Dataset (MAT file format)
    # =========================================================================
    println("\n[2/5] Opening hyperspectral dataset...")
    
    hsi_path = "data/Cuprite.mat"
    
    println("  ✓ Loading MAT file: $hsi_path")
    mat_file = matopen(hsi_path, "r")
    data_keys = keys(mat_file)
    data_key = first(data_keys)
    data = read(mat_file, data_key)
    close(mat_file)
    
    # Data shape handling
    # Python saves as (bands, rows, cols) = (224, 512, 614)
    # But MATLAB reads it as-is, so check if permutation is needed
    dims = size(data)
    if length(dims) == 3
        if dims[3] == 224
            # (rows, cols, bands) format - permute
            data = permutedims(data, (3, 1, 2))
        end
        # else: already (bands, rows, cols) - no permute needed
    end
    n_bands = size(data, 1)
    n_rows = size(data, 2)
    n_cols = size(data, 3)
    println("  ✓ Dataset shape: $n_bands bands × $n_rows × $n_cols pixels")
    
    # File size
    file_size_gb = filesize(hsi_path) / (1024^3)
    println("  ✓ File size: $(round(file_size_gb, digits=2)) GB")
    
    # Memory info
    mem_info = Sys.free_memory() / (1024^3)
    println("  ✓ Available RAM: $(round(mem_info, digits=2)) GB")
    
    if file_size_gb > mem_info * 0.8
        println("  ⚠ Dataset size exceeds 80% of available RAM - using chunked processing")
    end
    
    # =========================================================================
    # 3. Process with Chunked I/O
    # =========================================================================
    println("\n[3/5] Processing hyperspectral data (chunked I/O)...")
    
    sam_results = Float32[]
    pixels_processed = 0
    
    # Process in chunks
    chunk_size = 256
    chunks_processed = 0
    
    for row_start in 1:chunk_size:n_rows
        for col_start in 1:chunk_size:n_cols
            row_end = min(row_start + chunk_size - 1, n_rows)
            col_end = min(col_start + chunk_size - 1, n_cols)
            
            # Extract chunk
            chunk = data[:, row_start:row_end, col_start:col_end]
            
            # Reshape to (n_pixels, n_bands) and convert to Float32
            n_pixels_chunk = (row_end - row_start + 1) * (col_end - col_start + 1)
            pixel_spectra = Float32.(reshape(chunk, n_pixels_chunk, n_bands))
            
            # Calculate SAM
            sam_angles = spectral_angle_mapper(pixel_spectra, reference_spectrum)
            
            # Accumulate
            append!(sam_results, sam_angles)
            pixels_processed += n_pixels_chunk
            chunks_processed += 1
            
            # Progress
            if chunks_processed % 10 == 0
                print("\r    Processed $chunks_processed chunks ($pixels_processed pixels)...")
            end
        end
    end
    
    println("\r    Processed $chunks_processed chunks ($pixels_processed pixels)... Done!")
    
    # =========================================================================
    # 4. Compute Statistics
    # =========================================================================
    println("\n[4/5] Computing statistics...")
    
    mean_sam = mean(sam_results)
    median_sam = median(sam_results)
    std_sam = std(sam_results)
    min_sam = minimum(sam_results)
    max_sam = maximum(sam_results)
    
    println("  ✓ Mean SAM: $(round(mean_sam, digits=6)) radians ($(round(rad2deg(mean_sam), digits=2))°)")
    println("  ✓ Median SAM: $(round(median_sam, digits=6)) radians")
    println("  ✓ Std Dev: $(round(std_sam, digits=6)) radians")
    println("  ✓ Range: [$(round(min_sam, digits=6)), $(round(max_sam, digits=6))] radians")
    
    # =========================================================================
    # 5. Validation & Export
    # =========================================================================
    println("\n[5/5] Generating validation data...")
    
    # Generate validation hash
    result_str = "$(round(mean_sam, digits=8))_$(pixels_processed)_$(round(median_sam, digits=8))"
    result_hash = bytes2hex(sha256(result_str))[1:16]
    
    println("  ✓ Validation hash: $result_hash")
    
    # Export results
    results = Dict(
        "language" => "julia",
        "scenario" => "hyperspectral_sam",
        "pixels_processed" => pixels_processed,
        "chunks_processed" => chunks_processed,
        "n_bands" => n_bands,
        "mean_sam_rad" => mean_sam,
        "median_sam_rad" => median_sam,
        "std_sam_rad" => std_sam,
        "min_sam_rad" => min_sam,
        "max_sam_rad" => max_sam,
        "mean_sam_deg" => rad2deg(mean_sam),
        "validation_hash" => result_hash,
        "reference_hash" => ref_hash
    )
    
    # Save results
    mkpath("validation")
    open("validation/raster_julia_results.json", "w") do f
        JSON3.write(f, results)
    end
    
    println("\n  ✓ Results saved to validation/raster_julia_results.json")
    println("=" ^ 70)
    
    return 0
end

# Run benchmark
exit(main())
