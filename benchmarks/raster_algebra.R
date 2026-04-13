#!/usr/bin/env Rscript
# =============================================================================
# SCENARIO E: Raster Algebra & Band Math - R Implementation
# Tests: Band arithmetic, NDVI calculation, spectral indices
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

load_cuprite_bands <- function() {
  # Use project root for data
  data_dir <- if (file.exists("data")) "data" else file.path(dirname(script_dir), "data")
  mat_path <- file.path(data_dir, "Cuprite.mat")
  
  tryCatch({
    mat_data <- R.matlab::readMat(mat_path)
    data <- mat_data[[1]]
    
    # Preserve matrix dimensions using aperm
    green <- aperm(data[, , 31], c(2, 1))
    red <- aperm(data[, , 51], c(2, 1))
    nir <- aperm(data[, , 71], c(2, 1))
    swir <- aperm(data[, , 91], c(2, 1))
    
    list(
      green = green,
      red = red,
      nir = nir,
      swir = swir,
      shape = dim(data)
    )
  }, error = function(e) {
    cat("Warning: Could not load Cuprite data:", conditionMessage(e), "\n")
    cat("Generating synthetic data instead...\n")
    set.seed(42)
    shape <- c(512, 614)
    list(
      green = matrix(runif(prod(shape)) * 1000, nrow = shape[1], ncol = shape[2]),
      red = matrix(runif(prod(shape)) * 800, nrow = shape[1], ncol = shape[2]),
      nir = matrix(runif(prod(shape)) * 2000, nrow = shape[1], ncol = shape[2]),
      swir = matrix(runif(prod(shape)) * 1500, nrow = shape[1], ncol = shape[2]),
      shape = c(4, shape)
    )
  })
}

benchmark_ndvi <- function(nir, red) {
  numerator <- nir - red
  denominator <- nir + red
  ndvi <- ifelse(denominator != 0, numerator / denominator, 0)
  return(ndvi)
}

benchmark_band_arithmetic <- function(green, red, nir, swir) {
  results <- list()
  
  results$sum <- green + red + nir + swir
  results$difference <- nir - red
  results$ratio <- nir / pmax(red, .Machine$double.eps)
  
  blue <- green * 0.8
  results$evi <- 2.5 * (nir - red) / (nir + 6*red - 7.5*blue + 1)
  
  L <- 0.5
  results$savi <- ((nir - red) / (nir + red + L)) * (1 + L)
  
  results$ndwi <- (green - nir) / (green + nir)
  results$nbr <- (nir - swir) / (nir + swir)
  
  return(results)
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

run_raster_algebra_benchmark <- function() {
  cat(strrep("=", 70), "\n")
  cat("R - Scenario E: Raster Algebra & Band Math\n")
  cat(strrep("=", 70), "\n")
  
  cat("\n[1/4] Loading hyperspectral data...\n")
  bands <- load_cuprite_bands()
  cat(sprintf("  ✓ Loaded %d bands, shape: %d x %d (%d pixels)\n",
              bands$shape[1], bands$shape[2], bands$shape[3], 
              bands$shape[2] * bands$shape[3]))
  
  results <- list()
  all_hashes <- character(0)
  
  # NDVI benchmark
  cat("\n[2/4] Testing NDVI calculation...\n")
  
  ndvi_task <- function() {
    benchmark_ndvi(bands$nir, bands$red)
  }
  
  bench_result <- run_benchmark(ndvi_task, 10, 2)
  times <- bench_result$times
  ndvi_result <- bench_result$result
  ndvi_hash <- generate_hash(ndvi_result)
  all_hashes <- c(all_hashes, ndvi_hash)
  
  cat(sprintf("  ✓ Min: %.4fs (primary)\n", min(times)))
  cat(sprintf("  ✓ Mean: %.4fs ± %.4fs\n", mean(times), sd(times)))
  cat(sprintf("  ✓ Hash: %s\n", ndvi_hash))
  
  results$ndvi <- list(
    min_time_s = min(times),
    mean_time_s = mean(times),
    std_time_s = sd(times),
    hash = ndvi_hash
  )
  
  # Band arithmetic benchmark
  cat("\n[3/4] Testing band arithmetic...\n")
  
  band_math_task <- function() {
    benchmark_band_arithmetic(bands$green, bands$red, bands$nir, bands$swir)
  }
  
  bench_result <- run_benchmark(band_math_task, 10, 2)
  times <- bench_result$times
  indices_result <- bench_result$result
  indices_hash <- generate_hash(unlist(indices_result))
  all_hashes <- c(all_hashes, indices_hash)
  
  cat(sprintf("  ✓ Min: %.4fs (primary)\n", min(times)))
  cat(sprintf("  ✓ Mean: %.4fs ± %.4fs\n", mean(times), sd(times)))
  cat(sprintf("  ✓ Hash: %s\n", indices_hash))
  
  results$band_arithmetic <- list(
    min_time_s = min(times),
    mean_time_s = mean(times),
    std_time_s = sd(times),
    hash = indices_hash
  )
  
  # Convolution benchmark (using terra focal)
  cat("\n[4/4] Testing 3x3 convolution...\n")
  
  # Convert to SpatRaster for terra operations
  dim_nir <- dim(bands$nir)
  nir_rast <- terra::rast(nrows = dim_nir[1], ncols = dim_nir[2], vals = as.numeric(bands$nir))
  
  conv_task <- function() {
    terra::focal(nir_rast, w = matrix(1/9, 3, 3), fun = "mean")
  }
  
   bench_result <- run_benchmark(conv_task, 10, 2)
  times <- bench_result$times
  conv_result <- bench_result$result
  conv_hash <- generate_hash(as.matrix(conv_result))
  all_hashes <- c(all_hashes, conv_hash)
  
  cat(sprintf("  ✓ Min: %.4fs (primary)\n", min(times)))
  cat(sprintf("  ✓ Mean: %.4fs ± %.4fs\n", mean(times), sd(times)))
  cat(sprintf("  ✓ Hash: %s\n", conv_hash))
  
  results$convolution_3x3 <- list(
    min_time_s = min(times),
    mean_time_s = mean(times),
    std_time_s = sd(times),
    hash = conv_hash
  )
  
  # Save results
  cat("\n", strrep("=", 70), "\n")
  cat("SAVING RESULTS...\n")
  cat(strrep("=", 70), "\n")
  
  dir.create(OUTPUT_DIR, showWarnings = FALSE, recursive = TRUE)
  dir.create(RESULTS_DIR, showWarnings = FALSE, recursive = TRUE)
  
  output_data <- list(
    language = "r",
    scenario = "raster_algebra",
    data_shape = bands$shape,
    results = results,
    all_hashes = all_hashes,
    combined_hash = generate_hash(all_hashes)
  )
  
  write_json(
    output_data,
    paste0(OUTPUT_DIR, "/raster_algebra_r_results.json"),
    pretty = TRUE,
    auto_unbox = TRUE
  )
  
  cat("✓ Results saved\n")
  cat(sprintf("✓ Combined validation hash: %s\n", output_data$combined_hash))
  
  cat("\n", strrep("=", 70), "\n")
  cat("Note: Minimum times are primary metrics (Chen & Revels 2016)\n")
  cat("      Mean/median provided for context only\n")
  cat(strrep("=", 70), "\n")
  
  return(output_data)
}

run_raster_algebra_benchmark()
