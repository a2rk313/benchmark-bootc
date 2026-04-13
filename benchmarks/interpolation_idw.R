#!/usr/bin/env Rscript
################################################################################
# SCENARIO C: Spatial Interpolation – R (IDW with FNN, synthetic only)
################################################################################
# Task: Inverse Distance Weighting (IDW) interpolation on scattered points
# Dataset: 50,000 random points → 1000×1000 grid interpolation
# Metrics: Computational throughput, numerical efficiency
#
# IMPLEMENTATION:
#   - Uses FNN (kd‑tree) for fast nearest neighbour search
#   - Vectorized weight calculation (identical to Python/Julia)
#   - Purely synthetic data generation with fixed seed (42)
################################################################################

suppressPackageStartupMessages({
  library(FNN)          # fast kd‑tree nearest neighbour search
  library(jsonlite)
  library(digest)
})

#' Inverse Distance Weighting (IDW) interpolation
idw_interpolation <- function(points, values, grid_x, grid_y,
                              power = 2, neighbors = 12) {
  grid_pts <- cbind(as.vector(grid_x), as.vector(grid_y))
  nn <- get.knnx(points, grid_pts, k = neighbors)
  dists <- pmax(nn$nn.dist, 1e-10)
  idx   <- nn$nn.index
  weights <- 1 / (dists ^ power)
  weights <- weights / rowSums(weights)
  interpolated <- rowSums(weights * matrix(values[idx], ncol = neighbors))
  matrix(interpolated, nrow = nrow(grid_x), ncol = ncol(grid_x))
}

# ------------------------------------------------------------------------------
# Generate synthetic scattered points (fixed seed)
# ------------------------------------------------------------------------------
generate_synthetic_points <- function(n = 50000) {
  set.seed(42)
  x <- runif(n, 0, 1000)
  y <- runif(n, 0, 1000)
  value <- 100 * sin(x / 200) * cos(y / 200) +
           50 * sin(x / 50) +
           20 * rnorm(n)
  data.frame(x = x, y = y, value = value)
}

# ------------------------------------------------------------------------------
main <- function() {
  cat(strrep("=", 70), "\n")
  cat("R - Scenario C: Spatial Interpolation (IDW with FNN, synthetic)\n")
  cat(strrep("=", 70), "\n")

  # ----------------------------------------------------------------------------
  # 1. Generate synthetic point data
  # ----------------------------------------------------------------------------
  cat("\n[1/4] Generating SYNTHETIC point data...\n")
  points_df <- generate_synthetic_points()
  cat(sprintf("  ✓ %d points\n", nrow(points_df)))

  points <- as.matrix(points_df[, c("x", "y")])
  values <- points_df$value

  # ----------------------------------------------------------------------------
  # 2. Create interpolation grid
  # ----------------------------------------------------------------------------
  cat("\n[2/4] Creating interpolation grid...\n")
  grid_res <- 1000
  grid_x <- matrix(seq(0, 1000, length.out = grid_res),
                   nrow = grid_res, ncol = grid_res, byrow = TRUE)
  grid_y <- matrix(seq(0, 1000, length.out = grid_res),
                   nrow = grid_res, ncol = grid_res, byrow = FALSE)
  cat(sprintf("  ✓ Grid size: %d × %d\n", grid_res, grid_res))
  cat(sprintf("  ✓ Total interpolation points: %s\n",
              format(grid_res^2, big.mark = ",")))

  # ----------------------------------------------------------------------------
  # 3. Perform IDW interpolation
  # ----------------------------------------------------------------------------
  cat("\n[3/4] Performing IDW interpolation (kd‑tree, vectorized)...\n")
  start_time <- Sys.time()
  interpolated <- idw_interpolation(points, values, grid_x, grid_y,
                                    power = 2, neighbors = 12)
  elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
  cat(sprintf("  ✓ Interpolation complete in %.2f seconds\n", elapsed))
  cat(sprintf("  ✓ Interpolated value range: [%.2f, %.2f]\n",
              min(interpolated, na.rm = TRUE),
              max(interpolated, na.rm = TRUE)))

  # ----------------------------------------------------------------------------
  # 4. Statistics and validation
  # ----------------------------------------------------------------------------
  cat("\n[4/4] Computing metrics...\n")
  mean_val <- mean(interpolated, na.rm = TRUE)
  std_val  <- sd(interpolated, na.rm = TRUE)
  med_val  <- median(interpolated, na.rm = TRUE)
  pts_per_sec <- (grid_res^2) / elapsed
  cat(sprintf("  ✓ Mean: %.2f, Std: %.2f\n", mean_val, std_val))
  cat(sprintf("  ✓ Processing rate: %s grid points/second\n",
              format(round(pts_per_sec), big.mark = ",")))

  # Validation hash
  result_str <- sprintf("%.6f_%.6f_%.6f", mean_val, std_val, med_val)
  result_hash <- substr(digest(result_str, algo = "sha256"), 1, 16)
  cat(sprintf("  ✓ Validation hash: %s\n", result_hash))

  # ----------------------------------------------------------------------------
  # 5. Save results
  # ----------------------------------------------------------------------------
  results <- list(
    language = "r",
    scenario = "interpolation_idw",
    n_points = nrow(points_df),
    grid_size = grid_res,
    total_interpolated = grid_res^2,
    execution_time_s = elapsed,
    points_per_second = pts_per_sec,
    mean_value = mean_val,
    std_value = std_val,
    median_value = med_val,
    validation_hash = result_hash
  )

  dir.create("validation", showWarnings = FALSE)
  write_json(results, "validation/interpolation_r_results.json",
             pretty = TRUE, auto_unbox = TRUE)

  cat("\n  ✓ Results saved to validation/interpolation_r_results.json\n")
  cat(strrep("=", 70), "\n")
  return(0)
}

quit(status = main())
