#!/usr/bin/env julia
"""
===============================================================================
SCENARIO C: Spatial Interpolation - Julia Implementation
===============================================================================
Task: Inverse Distance Weighting (IDW) interpolation on scattered points
Dataset: 50,000 random points → 1000x1000 grid interpolation
Metrics: Computational throughput, numerical efficiency, parallelization
===============================================================================
"""

using NearestNeighbors
using Statistics
using Random
using LinearAlgebra
using JSON3
using SHA

function idw_interpolation(points::Matrix{Float64}, values::Vector{Float64}, 
                           grid_x::Matrix{Float64}, grid_y::Matrix{Float64};
                           power::Float64=2.0, neighbors::Int=12)
    """
    Inverse Distance Weighting interpolation
    """
    # Build KD-tree for fast nearest neighbor search
    tree = KDTree(points')
    
    # Flatten grid for vectorized processing
    grid_points = hcat(vec(grid_x), vec(grid_y))'
    
    # Query nearest neighbors
    idxs, dists = knn(tree, grid_points, neighbors, true)
    
    # Prepare output
    n_grid = size(grid_points, 2)
    interpolated = zeros(Float64, n_grid)
    
    # Interpolate for each grid point
    for i in 1:n_grid
        # Avoid division by zero
        distances = max.(dists[i], 1e-10)
        
        # Calculate weights (inverse distance)
        weights = 1.0 ./ (distances .^ power)
        
        # Normalize weights
        weights ./= sum(weights)
        
        # Interpolate value
        interpolated[i] = sum(weights .* values[idxs[i]])
    end
    
    # Reshape to grid
    return reshape(interpolated, size(grid_x))
end

function main()
    println("=" ^ 70)
    println("JULIA - Scenario C: Spatial Interpolation (IDW)")
    println("=" ^ 70)
    
    # =========================================================================
    # 1. Generate synthetic scattered points
    # =========================================================================
    println("\n[1/4] Generating scattered point data...")
    
    Random.seed!(42)
    n_points = 50000
    
    # Random points in [0, 1000] x [0, 1000]
    x = rand(n_points) .* 1000
    y = rand(n_points) .* 1000
    
    # Synthetic elevation field with spatial structure
    values = (
        100 .* sin.(x ./ 200) .* cos.(y ./ 200) .+  # Large-scale pattern
        50 .* sin.(x ./ 50) .+                       # Medium-scale
        20 .* randn(n_points)                        # Noise
    )
    
    points = hcat(x, y)
    
    println("  ✓ Generated $(n_points) scattered points")
    println("  ✓ Value range: [$(minimum(values)), $(maximum(values))]")
    
    # =========================================================================
    # 2. Create interpolation grid
    # =========================================================================
    println("\n[2/4] Creating interpolation grid...")
    
    grid_resolution = 1000  # 1000x1000 grid
    grid_x_vec = range(0, 1000, length=grid_resolution)
    grid_y_vec = range(0, 1000, length=grid_resolution)
    
    grid_x = repeat(grid_x_vec', grid_resolution, 1)
    grid_y = repeat(grid_y_vec, 1, grid_resolution)
    
    println("  ✓ Grid size: $grid_resolution × $grid_resolution")
    println("  ✓ Total interpolation points: $(grid_resolution^2)")
    
    # =========================================================================
    # 3. Perform IDW interpolation
    # =========================================================================
    println("\n[3/4] Performing IDW interpolation...")
    
    start_time = time()
    interpolated = idw_interpolation(points, values, grid_x, grid_y, power=2.0, neighbors=12)
    elapsed_time = time() - start_time
    
    println("  ✓ Interpolation complete in $(round(elapsed_time, digits=2)) seconds")
    println("  ✓ Interpolated value range: [$(minimum(interpolated)), $(maximum(interpolated))]")
    
    # =========================================================================
    # 4. Compute statistics and validate
    # =========================================================================
    println("\n[4/4] Computing metrics...")
    
    # Calculate interpolation quality metrics
    mean_value = mean(interpolated)
    std_value = std(interpolated)
    median_value = median(interpolated)
    
    # Calculate processing rate
    points_per_second = (grid_resolution ^ 2) / elapsed_time
    
    println("  ✓ Mean interpolated value: $(round(mean_value, digits=2))")
    println("  ✓ Std dev: $(round(std_value, digits=2))")
    println("  ✓ Processing rate: $(round(Int, points_per_second)) grid points/second")
    
    # Generate validation hash
    result_str = "$(round(mean_value, digits=6))_$(round(std_value, digits=6))_$(round(median_value, digits=6))"
    result_hash = bytes2hex(sha256(result_str))[1:16]
    
    println("  ✓ Validation hash: $result_hash")
    
    # Export results
    results = Dict(
        "language" => "julia",
        "scenario" => "interpolation_idw",
        "n_points" => n_points,
        "grid_size" => grid_resolution,
        "total_interpolated" => grid_resolution ^ 2,
        "execution_time_s" => elapsed_time,
        "points_per_second" => points_per_second,
        "mean_value" => mean_value,
        "std_value" => std_value,
        "median_value" => median_value,
        "validation_hash" => result_hash
    )
    
    # Save results
    mkpath("validation")
    open("validation/interpolation_julia_results.json", "w") do f
        JSON3.write(f, results)
    end
    
    println("\n  ✓ Results saved to validation/interpolation_julia_results.json")
    println("=" ^ 70)
    
    return 0
end

# Run benchmark
exit(main())
