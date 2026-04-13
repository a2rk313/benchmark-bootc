#!/usr/bin/env julia
"""
===============================================================================
SCENARIO D: Time-Series NDVI Analysis - Julia Implementation
===============================================================================
Task: Calculate NDVI statistics across 12-month time series
Dataset: Synthetic Landsat-like data (500x500 pixels × 12 dates × 2 bands)
Metrics: Temporal aggregation, SIMD vectorization, array operations
===============================================================================
"""

using Statistics
using Random
using LinearAlgebra
using JSON3
using SHA

function generate_synthetic_landsat(width=500, height=500, n_dates=12; seed=42)
    """Generate synthetic Landsat-like time series"""
    Random.seed!(seed)
    
    # Create spatial patterns
    x = range(0, 4π, length=width)
    y = range(0, 4π, length=height)
    X = repeat(x', height, 1)
    Y = repeat(y, 1, width)
    
    # Base vegetation pattern
    base_vegetation = (sin.(X) .* cos.(Y) .+ 1) ./ 2
    
    # Generate time series
    red_bands = zeros(Float32, n_dates, height, width)
    nir_bands = zeros(Float32, n_dates, height, width)
    
    for t in 1:n_dates
        # Seasonal variation
        season_factor = sin(2π * (t-1) / 12)
        vegetation_level = 0.5 + 0.3 * season_factor
        
        # Red band
        red_bands[t, :, :] = (
            0.1 .+ 0.2 .* (1 .- base_vegetation .* vegetation_level) .+
            0.05 .* randn(Float32, height, width)
        )
        
        # NIR band
        nir_bands[t, :, :] = (
            0.3 .+ 0.5 .* base_vegetation .* vegetation_level .+
            0.05 .* randn(Float32, height, width)
        )
    end
    
    # Clip to valid range
    clamp!(red_bands, 0, 1)
    clamp!(nir_bands, 0, 1)
    
    return red_bands, nir_bands
end

function calculate_ndvi(red, nir)
    """Calculate NDVI = (NIR - Red) / (NIR + Red)"""
    epsilon = Float32(1e-8)
    ndvi = (nir .- red) ./ (nir .+ red .+ epsilon)
    return clamp.(ndvi, -1, 1)
end

function main()
    println("=" ^ 70)
    println("JULIA - Scenario D: Time-Series NDVI Analysis")
    println("=" ^ 70)
    
    # 1. Generate data
    println("\n[1/5] Generating synthetic Landsat time series...")
    width, height = 500, 500
    n_dates = 12
    
    start_time = time()
    red_bands, nir_bands = generate_synthetic_landsat(width, height, n_dates)
    gen_time = time() - start_time
    
    data_size_mb = (sizeof(red_bands) + sizeof(nir_bands)) / (1024^2)
    println("  ✓ Generated $n_dates dates of $(width)×$(height) imagery")
    println("  ✓ Data size: $(round(data_size_mb, digits=1)) MB")
    
    # 2. Calculate NDVI
    println("\n[2/5] Calculating NDVI for each date...")
    start_time = time()
    ndvi_stack = similar(red_bands)
    
    for t in 1:n_dates
        ndvi_stack[t, :, :] = calculate_ndvi(red_bands[t, :, :], nir_bands[t, :, :])
    end
    
    calc_time = time() - start_time
    println("  ✓ NDVI calculated for all $n_dates dates")
    println("  ✓ Calculation time: $(round(calc_time, digits=2)) seconds")
    
    # 3. Temporal statistics
    println("\n[3/5] Computing temporal statistics...")
    start_time = time()
    
    mean_ndvi = mean(ndvi_stack, dims=1)[1, :, :]
    std_ndvi = std(ndvi_stack, dims=1)[1, :, :]
    max_ndvi = maximum(ndvi_stack, dims=1)[1, :, :]
    min_ndvi = minimum(ndvi_stack, dims=1)[1, :, :]
    
    # Trend detection
    time_index = Float32.(0:n_dates-1)
    ndvi_trend = zeros(Float32, height, width)
    
    for i in 1:height, j in 1:width
        pixel_series = ndvi_stack[:, i, j]
        # Simple linear regression slope
        ndvi_trend[i, j] = cov(time_index, pixel_series) / var(time_index)
    end
    
    stats_time = time() - start_time
    println("  ✓ Temporal statistics computed")
    println("  ✓ Mean NDVI: $(round(mean(mean_ndvi), digits=3))")
    
    # 4. Phenology
    println("\n[4/5] Extracting phenology metrics...")
    start_time = time()
    
    peak_month = [argmax(ndvi_stack[:, i, j]) for i in 1:height, j in 1:width]
    
    threshold = Float32(0.3)
    growing_season = sum(ndvi_stack .> threshold, dims=1)[1, :, :]
    amplitude = max_ndvi .- min_ndvi
    
    pheno_time = time() - start_time
    println("  ✓ Average peak month: $(round(mean(peak_month), digits=1))")
    println("  ✓ Average growing season: $(round(mean(growing_season), digits=1)) months")
    
    # 5. Results
    println("\n[5/5] Computing final metrics...")
    total_time = calc_time + stats_time + pheno_time
    pixels_processed = width * height * n_dates
    throughput = pixels_processed / total_time
    
    println("  ✓ Total processing time: $(round(total_time, digits=2)) seconds")
    println("  ✓ Throughput: $(round(Int, throughput)) pixel-dates/second")
    
    # Validation
    result_str = "$(round(mean(mean_ndvi), digits=6))_$(round(mean(ndvi_trend), digits=6))_$(round(mean(amplitude), digits=6))"
    result_hash = bytes2hex(sha256(result_str))[1:16]
    println("  ✓ Validation hash: $result_hash")
    
    # Export
    results = Dict(
        "language" => "julia",
        "scenario" => "timeseries_ndvi",
        "image_size" => "$(width)x$(height)",
        "n_dates" => n_dates,
        "total_pixels_processed" => pixels_processed,
        "execution_time_s" => total_time,
        "throughput_pixels_per_sec" => throughput,
        "mean_ndvi" => mean(mean_ndvi),
        "mean_trend" => mean(ndvi_trend),
        "mean_amplitude" => mean(amplitude),
        "avg_growing_season" => mean(growing_season),
        "validation_hash" => result_hash
    )
    
    mkpath("validation")
    open("validation/timeseries_julia_results.json", "w") do f
        JSON3.write(f, results)
    end
    
    println("\n  ✓ Results saved")
    println("=" ^ 70)
    return 0
end

exit(main())
