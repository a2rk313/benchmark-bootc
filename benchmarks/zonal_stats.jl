#!/usr/bin/env julia
"""
SCENARIO F: Zonal Statistics - Julia Implementation
Tests: Polygon-based raster statistics (mean, std, sum over zones)
"""

using Statistics
using Random
using SHA
using JSON3

const OUTPUT_DIR = "validation"
const RESULTS_DIR = "results"

include(joinpath(@__DIR__, "common_hash.jl"))

function create_latitude_zones(rows, cols, n_zones)
    mask = zeros(Int32, rows, cols)
    zone_height = rows ÷ n_zones
    
    for z in 1:n_zones
        row_start = (z - 1) * zone_height + 1
        row_end = z == n_zones ? rows : z * zone_height
        mask[row_start:row_end, :] .= z
    end
    
    return mask
end

function zonal_mean(raster, mask, zone_id)
    zone_mask = mask .== zone_id
    zone_values = raster[zone_mask]
    return length(zone_values) > 0 ? mean(zone_values) : 0.0
end

function zonal_statistics(raster, mask)
    unique_zones = unique(mask)
    unique_zones = unique_zones[unique_zones .> 0]
    
    means = Float64[]
    stds = Float64[]
    sums = Float64[]
    counts = Int[]
    
    for zone_id in unique_zones
        zone_mask = mask .== zone_id
        zone_values = raster[zone_mask]
        if length(zone_values) > 0
            push!(means, mean(zone_values))
            push!(stds, std(zone_values))
            push!(sums, sum(zone_values))
            push!(counts, length(zone_values))
        else
            push!(means, 0.0)
            push!(stds, 0.0)
            push!(sums, 0.0)
            push!(counts, 0)
        end
    end
    
    return (zones=unique_zones, means=means, stds=stds, sums=sums, counts=counts)
end

function run_benchmark(func, runs=10, warmup=2)
    for _ in 1:warmup
        func()
    end
    
    times = Float64[]
    result = nothing
    for _ in 1:runs
        t_start = time_ns()
        result = func()
        t_end = time_ns()
        push!(times, (t_end - t_start) / 1e9)
    end
    
    return times, result
end

function run_zonal_stats_benchmark()
    println("=" ^ 70)
    println("JULIA - Scenario F: Zonal Statistics")
    println("=" ^ 70)
    
    println("\n[1/4] Loading data...")
    
    rows, cols = 180, 360
    n_zones = 10
    
    Random.seed!(42)
    raster = rand(Float32, rows, cols) .* 3000f0
    
    println("  ✓ Created raster: $rows x $cols cells ($(rows * cols) cells)")
    
    results = Dict()
    all_hashes = []
    
    println("\n[2/4] Creating raster mask grid...")
    
    function mask_task()
        return create_latitude_zones(rows, cols, n_zones)
    end
    
    times, mask_result = run_benchmark(mask_task, 5, 1)
    mask_hash = generate_hash(mask_result)
    push!(all_hashes, mask_hash)
    
    println("  ✓ Mask created: $n_zones zones")
    println("  ✓ Min: $(minimum(times))s (primary)")
    println("  ✓ Mean: $(mean(times))s ± $(std(times))s")
    
    results["mask_creation"] = Dict(
        "min_time_s" => minimum(times),
        "mean_time_s" => mean(times),
        "std_time_s" => std(times),
        "n_zones" => n_zones,
        "hash" => mask_hash
    )
    
    println("\n[3/4] Testing zonal mean calculation...")
    
    function zonal_task()
        return zonal_statistics(raster, mask_result)
    end
    
    times, stats_result = run_benchmark(zonal_task, 10, 2)
    stats_hash = generate_hash(stats_result.means)
    push!(all_hashes, stats_hash)
    
    println("  ✓ Min: $(minimum(times))s (primary)")
    println("  ✓ Mean: $(mean(times))s ± $(std(times))s")
    println("  ✓ Hash: $stats_hash")
    
    results["zonal_mean"] = Dict(
        "min_time_s" => minimum(times),
        "mean_time_s" => mean(times),
        "std_time_s" => std(times),
        "n_zones" => length(stats_result.zones),
        "hash" => stats_hash
    )
    
    println("\n[4/4] Testing full zonal statistics...")
    
    function full_stats_task()
        return zonal_statistics(raster, mask_result)
    end
    
    times, _ = run_benchmark(full_stats_task, 10, 2)
    
    println("  ✓ Min: $(minimum(times))s (primary)")
    println("  ✓ Mean: $(mean(times))s ± $(std(times))s")
    
    results["zonal_stats"] = Dict(
        "min_time_s" => minimum(times),
        "mean_time_s" => mean(times),
        "std_time_s" => std(times),
        "hash" => stats_hash
    )
    
    println("\n" * "=" ^ 70)
    println("SAVING RESULTS...")
    println("=" ^ 70)
    
    mkpath(OUTPUT_DIR)
    mkpath(RESULTS_DIR)
    
    output_data = Dict(
        "language" => "julia",
        "scenario" => "zonal_statistics",
        "results" => results,
        "all_hashes" => all_hashes,
        "combined_hash" => generate_hash(all_hashes)
    )
    
    open("$OUTPUT_DIR/zonal_stats_julia_results.json", "w") do f
        JSON3.pretty(f, output_data)
    end
    
    println("✓ Results saved")
    println("✓ Combined validation hash: $(output_data["combined_hash"])")
    
    println("\n" * "=" ^ 70)
    println("Note: Minimum times are primary metrics (Chen & Revels 2016)")
    println("=" ^ 70)
    
    return output_data
end

run_zonal_stats_benchmark()
