#!/usr/bin/env Rscript
################################################################################
# SCENARIO D: Time-Series NDVI Analysis - R Implementation
################################################################################

suppressPackageStartupMessages({
  library(jsonlite)
  library(digest)
})

generate_synthetic_landsat <- function(width=500, height=500, n_dates=12, seed=42) {
  set.seed(seed)
  
  # Spatial patterns
  x <- seq(0, 4*pi, length.out=width)
  y <- seq(0, 4*pi, length.out=height)
  X <- outer(rep(1, height), x)
  Y <- outer(y, rep(1, width))
  
  base_vegetation <- (sin(X) * cos(Y) + 1) / 2
  
  # Time series
  red_bands <- array(0, dim=c(n_dates, height, width))
  nir_bands <- array(0, dim=c(n_dates, height, width))
  
  for (t in 1:n_dates) {
    season_factor <- sin(2*pi*(t-1)/12)
    vegetation_level <- 0.5 + 0.3*season_factor
    
    red_bands[t,,] <- pmax(0, pmin(1,
      0.1 + 0.2*(1 - base_vegetation*vegetation_level) + 
      0.05*matrix(rnorm(height*width), height, width)
    ))
    
    nir_bands[t,,] <- pmax(0, pmin(1,
      0.3 + 0.5*base_vegetation*vegetation_level +
      0.05*matrix(rnorm(height*width), height, width)
    ))
  }
  
  list(red=red_bands, nir=nir_bands)
}

calculate_ndvi <- function(red, nir) {
  epsilon <- 1e-8
  ndvi <- (nir - red) / (nir + red + epsilon)
  pmax(-1, pmin(1, ndvi))
}

main <- function() {
  cat(strrep("=", 70), "\n")
  cat("R - Scenario D: Time-Series NDVI Analysis\n")
  cat(strrep("=", 70), "\n")
  
  # 1. Generate
  cat("\n[1/5] Generating synthetic Landsat time series...\n")
  width <- height <- 500
  n_dates <- 12
  
  start_time <- Sys.time()
  data <- generate_synthetic_landsat(width, height, n_dates)
  gen_time <- as.numeric(difftime(Sys.time(), start_time, units="secs"))
  
  cat(sprintf("  ✓ Generated %d dates of %dx%d imagery\n", n_dates, width, height))
  
  # 2. Calculate NDVI
  cat("\n[2/5] Calculating NDVI for each date...\n")
  start_time <- Sys.time()
  
  ndvi_stack <- array(0, dim=c(n_dates, height, width))
  for (t in 1:n_dates) {
    ndvi_stack[t,,] <- calculate_ndvi(data$red[t,,], data$nir[t,,])
  }
  
  calc_time <- as.numeric(difftime(Sys.time(), start_time, units="secs"))
  cat(sprintf("  ✓ Calculation time: %.2f seconds\n", calc_time))
  
  # 3. Temporal stats
  cat("\n[3/5] Computing temporal statistics...\n")
  start_time <- Sys.time()
  
  mean_ndvi <- apply(ndvi_stack, c(2,3), mean)
  std_ndvi <- apply(ndvi_stack, c(2,3), sd)
  max_ndvi <- apply(ndvi_stack, c(2,3), max)
  min_ndvi <- apply(ndvi_stack, c(2,3), min)
  
  # Trend
  time_index <- 0:(n_dates-1)
  ndvi_trend <- apply(ndvi_stack, c(2,3), function(x) {
    cov(time_index, x) / var(time_index)
  })
  
  stats_time <- as.numeric(difftime(Sys.time(), start_time, units="secs"))
  cat(sprintf("  ✓ Mean NDVI: %.3f\n", mean(mean_ndvi)))
  
  # 4. Phenology
  cat("\n[4/5] Extracting phenology metrics...\n")
  start_time <- Sys.time()
  
  peak_month <- apply(ndvi_stack, c(2,3), which.max)
  growing_season <- apply(ndvi_stack > 0.3, c(2,3), sum)
  amplitude <- max_ndvi - min_ndvi
  
  pheno_time <- as.numeric(difftime(Sys.time(), start_time, units="secs"))
  
  # 5. Results
  cat("\n[5/5] Computing final metrics...\n")
  total_time <- calc_time + stats_time + pheno_time
  pixels_processed <- width * height * n_dates
  throughput <- pixels_processed / total_time
  
  cat(sprintf("  ✓ Total time: %.2f seconds\n", total_time))
  cat(sprintf("  ✓ Throughput: %s pixels/second\n", format(round(throughput), big.mark=",")))
  
  # Validation
  result_str <- sprintf("%.6f_%.6f_%.6f", mean(mean_ndvi), mean(ndvi_trend), mean(amplitude))
  result_hash <- substr(digest(result_str, algo="sha256"), 1, 16)
  cat(sprintf("  ✓ Validation hash: %s\n", result_hash))
  
  # Export
  results <- list(
    language = "r",
    scenario = "timeseries_ndvi",
    image_size = sprintf("%dx%d", width, height),
    n_dates = n_dates,
    total_pixels_processed = pixels_processed,
    execution_time_s = total_time,
    throughput_pixels_per_sec = throughput,
    mean_ndvi = mean(mean_ndvi),
    mean_trend = mean(ndvi_trend),
    mean_amplitude = mean(amplitude),
    avg_growing_season = mean(growing_season),
    validation_hash = result_hash
  )
  
  dir.create("validation", showWarnings=FALSE)
  write_json(results, "validation/timeseries_r_results.json", pretty=TRUE, auto_unbox=TRUE)
  
  cat("\n  ✓ Results saved\n")
  cat(strrep("=", 70), "\n")
  return(0)
}

quit(status=main())
