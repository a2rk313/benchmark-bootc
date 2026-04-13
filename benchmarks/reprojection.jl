#!/usr/bin/env julia
"""
SCENARIO G: Coordinate Reprojection - Julia Implementation
Tests: EPSG:4326 <-> UTM/Web Mercator reprojection performance

Note: Uses pure Julia implementation of coordinate transformations for 
compatibility. For production use, consider PROJ bindings.
"""

using Statistics
using Random
using SHA
using JSON3

const OUTPUT_DIR = "validation"
const RESULTS_DIR = "results"

include(joinpath(@__DIR__, "common_hash.jl"))

deg2rad(deg::T) where T<:Number = deg * pi / 180.0
rad2deg(rad::T) where T<:Number = rad * 180.0 / pi

function wgs84_to_web_mercator(lat::AbstractVector{Float64}, lon::AbstractVector{Float64})
    n = length(lat)
    x = Vector{Float64}(undef, n)
    y = Vector{Float64}(undef, n)
    
    @inbounds for i in 1:n
        lat_r = deg2rad(lat[i])
        lon_r = deg2rad(lon[i])
        
        x[i] = 6378137.0 * lon_r
        y[i] = 6378137.0 * log(tan(pi/4 + lat_r/2))
    end
    
    return (x=x, y=y)
end

function wgs84_to_utm(lat::AbstractVector{Float64}, lon::AbstractVector{Float64}, zones::AbstractVector{Int})
    n = length(lat)
    x = Vector{Float64}(undef, n)
    y = Vector{Float64}(undef, n)
    
    a = 6378137.0
    f = 1.0 / 298.257223563
    k0 = 0.9996
    e = sqrt(2*f - f^2)
    e2 = e^2
    e_prime2 = e2 / (1.0 - e2)
    
    @inbounds for i in 1:n
        lat_r = deg2rad(lat[i])
        lon_r = deg2rad(lon[i])
        zone = zones[i]
        
        lambda0 = deg2rad((zone - 1) * 6 - 180 + 3)
        
        sin_lat = sin(lat_r)
        cos_lat = cos(lat_r)
        tan_lat = tan(lat_r)
        
        N = a / sqrt(1.0 - e2 * sin_lat^2)
        T = tan_lat^2
        C = e_prime2 * cos_lat^2
        A = cos_lat * (lon_r - lambda0)
        
        M = a * ((1.0 - e2/4.0 - 3.0*e2^2/64.0) * lat_r - 
                  (3.0*e2/8.0 + 3.0*e2^2/32.0) * sin(2.0*lat_r) +
                  (15.0*e2^2/256.0) * sin(4.0*lat_r))
        
        x_utm = k0 * N * (A + (1.0 - T + C) * A^3/6.0 + 
                          (5.0 - 18.0*T + T^2 + 72.0*C - 58.0*e_prime2) * A^5/120.0)
        y_utm = k0 * (M + N * tan_lat * (A^2/2.0 + 
                          (5.0 - T + 9.0*C + 4.0*C^2) * A^4/24.0 + 
                          (61.0 - 58.0*T + T^2 + 600.0*C - 330.0*e_prime2) * A^6/720.0))
        
        x[i] = x_utm + 500000.0
        y[i] = lat[i] < 0.0 ? y_utm + 10000000.0 : y_utm
    end
    
    return (x=x, y=y)
end

function generate_test_points(n_points::Int)
    Random.seed!(42)
    lat = rand(-90.0:1e-6:90.0, n_points)
    lon = rand(-180.0:1e-6:180.0, n_points)
    return (lat=lat, lon=lon)
end

function run_benchmark(func, runs::Int=10, warmup::Int=2)
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

function run_reprojection_benchmark()
    println("=" ^ 70)
    println("JULIA - Scenario G: Coordinate Reprojection")
    println("=" ^ 70)
    
    sizes = [1000, 5000, 10000]
    results = Dict()
    all_hashes = String[]
    
    for size in sizes
        println("\n[Testing with $size points]")
        println("-" ^ 40)
        
        points = generate_test_points(size)
        
        println("  Web Mercator (EPSG:4326 -> 3857)...")
        
        merc_task() = wgs84_to_web_mercator(points.lat, points.lon)
        
        times, merc_result = run_benchmark(merc_task, 5, 2)
        merc_hash = generate_hash([mean(merc_result.x), mean(merc_result.y)])
        push!(all_hashes, merc_hash)
        
        println("    Min: $(minimum(times))s (primary)")
        println("    Mean: $(mean(times))s ± $(std(times))s")
        println("    Rate: $(round(Int, size / minimum(times))) points/sec")
        println("    Hash: $merc_hash")
        
        results["mercator_$size"] = Dict(
            "n_points" => size,
            "min_time_s" => minimum(times),
            "mean_time_s" => mean(times),
            "std_time_s" => std(times),
            "points_per_second" => round(Int, size / minimum(times)),
            "hash" => merc_hash
        )
        
        println("  UTM (zone-optimized)...")
        
        zones = Vector{Int}(floor.(Int, (points.lon .+ 180.0) ./ 6.0) .+ 1)
        
        utm_task() = wgs84_to_utm(points.lat, points.lon, zones)
        
        times, _ = run_benchmark(utm_task, 3, 1)
        
        println("    Min: $(minimum(times))s (primary)")
        println("    Mean: $(mean(times))s ± $(std(times))s")
        println("    Rate: $(round(Int, size / minimum(times))) points/sec")
        
        results["utm_$size"] = Dict(
            "n_points" => size,
            "min_time_s" => minimum(times),
            "mean_time_s" => mean(times),
            "std_time_s" => std(times),
            "points_per_second" => round(Int, size / minimum(times))
        )
    end
    
    println("\n" * "=" ^ 70)
    println("SAVING RESULTS...")
    println("=" ^ 70)
    
    mkpath(OUTPUT_DIR)
    mkpath(RESULTS_DIR)
    
    output_data = Dict(
        "language" => "julia",
        "scenario" => "coordinate_reprojection",
        "results" => results,
        "all_hashes" => all_hashes,
        "combined_hash" => generate_hash(all_hashes)
    )
    
    open("$OUTPUT_DIR/reprojection_julia_results.json", "w") do f
        JSON3.pretty(f, output_data)
    end
    
    println("Results saved")
    println("Combined validation hash: $(output_data["combined_hash"])")
    
    println("\n" * "=" ^ 70)
    println("Note: Minimum times are primary metrics (Chen & Revels 2016)")
    println("=" ^ 70)
    
    return output_data
end

run_reprojection_benchmark()
