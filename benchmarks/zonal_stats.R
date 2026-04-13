#!/usr/bin/env Rscript
# =============================================================================
# SCENARIO F: Zonal Statistics - R Implementation
# Tests: Polygon-based raster statistics (mean, std, sum over zones)
# =============================================================================

suppressPackageStartupMessages({
  library(terra)
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

run_zonal_stats_benchmark <- function() {
  cat(strrep("=", 70), "\n")
  cat("R - Scenario F: Zonal Statistics\n")
  cat(strrep("=", 70), "\n")
  
  # Load data
  cat("\n[1/4] Loading data...\n")
  polys <- tryCatch({
    st_read("data/natural_earth_countries.gpkg")
  }, error = function(e) {
    cat("Warning: Could not load polygons, using simplified data\n")
    NULL
  })
  
  # Create synthetic raster
  set.seed(42)
  rows <- 180
  cols <- 360
  raster <- rast(nrows = rows, ncols = cols, 
                 xmin = -180, xmax = 180, ymin = -90, ymax = 90,
                 crs = "EPSG:4326")
  values(raster) <- runif(ncell(raster)) * 3000
  
  cat(sprintf("  ✓ Created raster: %d x %d cells\n", rows, cols))
  
  results <- list()
  all_hashes <- character(0)
  
  # Test zonal mean using terra
  cat("\n[2/4] Testing zonal statistics (terra)...\n")
  
  zonal_task <- function() {
    terra::zonal(raster, as.polygons(raster), fun = "mean", na.rm = TRUE)
  }
  
  bench_result <- run_benchmark(zonal_task, 10, 2)
  times <- bench_result$times
  
  # Create simple zones (e.g., latitudinal bands)
  zones <- rast(nrows = rows, ncols = cols, 
                xmin = -180, xmax = 180, ymin = -90, ymax = 90,
                crs = "EPSG:4326")
  zone_height <- rows / 10
  zone_ids <- rep(1:10, each = cols * zone_height)
  zone_ids <- matrix(zone_ids[1:(rows*cols)], nrow = rows, ncol = cols, byrow = TRUE)
  values(zones) <- as.vector(zone_ids)
  
  zonal_mean_task <- function() {
    terra::zonal(raster, zones, fun = "mean", na.rm = TRUE)
  }
  
  bench_result <- run_benchmark(zonal_mean_task, 10, 2)
  times <- bench_result$times
  zonal_result <- bench_result$result
  
  zonal_hash <- generate_hash(as.numeric(zonal_result$mean))
  all_hashes <- c(all_hashes, zonal_hash)
  
  cat(sprintf("  ✓ Min: %.4fs (primary)\n", min(times)))
  cat(sprintf("  ✓ Mean: %.4fs ± %.4fs\n", mean(times), sd(times)))
  cat(sprintf("  ✓ Hash: %s\n", zonal_hash))
  
  results$zonal_mean <- list(
    min_time_s = min(times),
    mean_time_s = mean(times),
    std_time_s = sd(times),
    n_zones = 10,
    hash = zonal_hash
  )
  
  # Save results
  cat("\n", strrep("=", 70), "\n")
  cat("SAVING RESULTS...\n")
  cat(strrep("=", 70), "\n")
  
  dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)
  dir.create(RESULTS_DIR, showWarnings = FALSE, recursive = TRUE)
  
  output_data <- list(
    language = "r",
    scenario = "zonal_statistics",
    results = results,
    all_hashes = all_hashes,
    combined_hash = generate_hash(all_hashes)
  )
  
  write_json(output_data, paste0(OUTPUT_DIR, "/zonal_stats_r_results.json"), 
             pretty = TRUE, auto_unbox = TRUE)
  
  cat("✓ Results saved\n")
  cat(sprintf("✓ Combined validation hash: %s\n", output_data$combined_hash))
  
  cat("\n", strrep("=", 70), "\n")
  cat("Note: Minimum times are primary metrics (Chen & Revels 2016)\n")
  cat(strrep("=", 70), "\n")
  
  return(output_data)
}

run_zonal_stats_benchmark()
