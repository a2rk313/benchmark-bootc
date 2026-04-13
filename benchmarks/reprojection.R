#!/usr/bin/env Rscript
# =============================================================================
# SCENARIO G: Coordinate Reprojection - R Implementation
# Tests: EPSG:4326 <-> UTM/Web Mercator reprojection performance
# 
# Note: Uses pure R implementation of coordinate transformations for 
# compatibility. For production use, consider sf/GDAL bindings.
# =============================================================================

suppressPackageStartupMessages({
  library(jsonlite)
  library(digest)
})

# Get script directory
get_script_dir <- function() {
  cmdArgs <- commandArgs(trailingOnly = FALSE)
  fileArg <- cmdArgs[grep("^--file=", cmdArgs)]
  if (length(fileArg) == 0) {
    return(".")
  }
  filePath <- sub("^--file=", "", fileArg)
  return(dirname(filePath))
}

script_dir <- get_script_dir()
OUTPUT_DIR <- "validation"
RESULTS_DIR <- "results"

source(file.path(script_dir, "common_hash.R"))

deg2rad <- function(deg) deg * pi / 180
rad2deg <- function(rad) rad * 180 / pi

wgs84_to_web_mercator <- function(lat, lon) {
  n <- length(lat)
  x <- numeric(n)
  y <- numeric(n)
  
  for (i in 1:n) {
    lat_r <- deg2rad(lat[i])
    lon_r <- deg2rad(lon[i])
    
    x[i] <- 6378137.0 * lon_r
    y[i] <- 6378137.0 * log(tan(pi/4 + lat_r/2))
  }
  
  return(list(x = x, y = y))
}

wgs84_to_utm <- function(lat, lon, zone) {
  n <- length(lat)
  x <- numeric(n)
  y <- numeric(n)
  
  a <- 6378137.0
  f <- 1/298.257223563
  k0 <- 0.9996
  e <- sqrt(2*f - f^2)
  
  lambda0 <- deg2rad((zone - 1) * 6 - 180 + 3)
  
  for (i in 1:n) {
    lat_r <- deg2rad(lat[i])
    lon_r <- deg2rad(lon[i])
    
    e2 <- e^2
    e_prime2 <- e2 / (1 - e2)
    
    N <- a / sqrt(1 - e2 * sin(lat_r)^2)
    T <- tan(lat_r)^2
    C <- e_prime2 * cos(lat_r)^2
    A <- cos(lat_r) * (lon_r - lambda0)
    
    M <- a * ((1 - e2/4 - 3*e2^2/64) * lat_r - 
              (3*e2/8 + 3*e2^2/32) * sin(2*lat_r) +
              (15*e2^2/256) * sin(4*lat_r))
    
    x_utm <- k0 * N * (A + (1-T+C)*A^3/6 + (5-18*T+T^2+72*C-58*e_prime2)*A^5/120)
    y_utm <- k0 * (M + N*tan(lat_r)*(A^2/2 + (5-T+9*C+4*C^2)*A^4/24 + 
                                     (61-58*T+T^2+600*C-330*e_prime2)*A^6/720))
    
    x[i] <- x_utm + 500000.0
    y[i] <- ifelse(lat[i] < 0, y_utm + 10000000.0, y_utm)
  }
  
  return(list(x = x, y = y))
}

generate_test_points <- function(n_points) {
  set.seed(42)
  data.frame(
    lat = runif(n_points, -90, 90),
    lon = runif(n_points, -180, 180)
  )
}

run_benchmark <- function(func, runs = 10, warmup = 2) {
  for (i in 1:warmup) {
    invisible(func())
  }
  
  times <- numeric(runs)
  result <- NULL
  for (i in 1:runs) {
    t_start <- proc.time()
    result <- func()
    t_end <- proc.time()
    times[i] <- (t_end - t_start)["elapsed"]
  }
  
  list(times = times, result = result)
}

run_reprojection_benchmark <- function() {
  cat(strrep("=", 70), "\n")
  cat("R - Scenario G: Coordinate Reprojection\n")
  cat(strrep("=", 70), "\n")
  
  sizes <- c(1000, 5000, 10000)
  results <- list()
  all_hashes <- character(0)
  
  for (size in sizes) {
    cat(sprintf("\n[Testing with %d points]\n", size))
    cat(strrep("-", 40), "\n")
    
    points <- generate_test_points(size)
    
    cat("  Web Mercator (EPSG:4326 -> 3857)...\n")
    
    merc_task <- function() {
      wgs84_to_web_mercator(points$lat, points$lon)
    }
    
    bench_result <- run_benchmark(merc_task, 5, 2)
    merc_result <- bench_result$result
    merc_hash <- generate_hash(c(mean(merc_result$x), mean(merc_result$y)))
    
    cat(sprintf("    Min: %.4fs (primary)\n", min(bench_result$times)))
    cat(sprintf("    Mean: %.4fs ± %.4fs\n", mean(bench_result$times), sd(bench_result$times)))
    cat(sprintf("    Rate: %s points/sec\n", format(size / min(bench_result$times), big.mark = ",")))
    cat(sprintf("    Hash: %s\n", merc_hash))
    
    results[[sprintf("mercator_%d", size)]] <- list(
      n_points = size,
      min_time_s = min(bench_result$times),
      mean_time_s = mean(bench_result$times),
      std_time_s = sd(bench_result$times),
      points_per_second = size / min(bench_result$times),
      hash = merc_hash
    )
    
    cat("  UTM (zone-optimized)...\n")
    
    zones <- floor((points$lon + 180) / 6) + 1
    
    utm_task <- function() {
      wgs84_to_utm(points$lat, points$lon, zones)
    }
    
    bench_result <- run_benchmark(utm_task, 3, 1)
    utm_result <- bench_result$result
    
    cat(sprintf("    Min: %.4fs (primary)\n", min(bench_result$times)))
    cat(sprintf("    Mean: %.4fs ± %.4fs\n", mean(bench_result$times), sd(bench_result$times)))
    cat(sprintf("    Rate: %s points/sec\n", format(size / min(bench_result$times), big.mark = ",")))
    
    results[[sprintf("utm_%d", size)]] <- list(
      n_points = size,
      min_time_s = min(bench_result$times),
      mean_time_s = mean(bench_result$times),
      std_time_s = sd(bench_result$times),
      points_per_second = size / min(bench_result$times)
    )
    
    all_hashes <- c(all_hashes, merc_hash)
  }
  
  cat("\n", strrep("=", 70), "\n")
  cat("SAVING RESULTS...\n")
  cat(strrep("=", 70), "\n")
  
  dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)
  dir.create(RESULTS_DIR, showWarnings = FALSE, recursive = TRUE)
  
  output_data <- list(
    language = "r",
    scenario = "coordinate_reprojection",
    results = results,
    all_hashes = all_hashes,
    combined_hash = generate_hash(all_hashes)
  )
  
  write_json(output_data, paste0(OUTPUT_DIR, "/reprojection_r_results.json"),
             pretty = TRUE, auto_unbox = TRUE)
  
  cat("Results saved\n")
  cat(sprintf("Combined validation hash: %s\n", output_data$combined_hash))
  
  cat("\n", strrep("=", 70), "\n")
  cat("Note: Minimum times are primary metrics (Chen & Revels 2016)\n")
  cat(strrep("=", 70), "\n")
  
  return(output_data)
}

run_reprojection_benchmark()
