#!/usr/bin/env Rscript
#===============================================================================
# I/O Operations Benchmark - R Implementation
#===============================================================================
# Tests file I/O performance for CSV and binary formats
# Tasks: CSV Write/Read, Binary Write/Read
#===============================================================================

library(jsonlite)

benchmark_csv_write <- function(n_rows = 1000000) {
  # Task 1: Write CSV File
  
  # Pre-generate data (not timed)
  df <- data.frame(
    lat = runif(n_rows, min = -90, max = 90),
    lon = runif(n_rows, min = -180, max = 180),
    device_id = sample(1:10000, n_rows, replace = TRUE)
  )
  
  output_path <- "data/io_test_r.csv"
  
  # Timed operation
  start_time <- Sys.time()
  write.csv(df, output_path, row.names = FALSE)
  elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
  
  file_size <- file.info(output_path)$size
  
  return(list(elapsed = elapsed, file_size = file_size))
}

benchmark_csv_read <- function() {
  # Task 2: Read CSV File
  
  input_path <- "data/io_test_r.csv"
  
  # Timed operation
  start_time <- Sys.time()
  df <- read.csv(input_path)
  elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
  
  return(list(elapsed = elapsed, n_rows = nrow(df)))
}

benchmark_binary_write <- function(n_values = 1000000) {
  # Task 3: Write Binary File
  
  # Pre-generate data (not timed)
  arr <- rnorm(n_values)
  
  output_path <- "data/io_test_r.bin"
  
  # Timed operation
  start_time <- Sys.time()
  con <- file(output_path, "wb")
  writeBin(arr, con, size = 8)  # 8 bytes = float64
  close(con)
  elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
  
  file_size <- file.info(output_path)$size
  
  return(list(elapsed = elapsed, file_size = file_size))
}

benchmark_binary_read <- function() {
  # Task 4: Read Binary File
  
  input_path <- "data/io_test_r.bin"
  
  # Timed operation
  start_time <- Sys.time()
  con <- file(input_path, "rb")
  arr <- readBin(con, double(), n = file.info(input_path)$size / 8)
  close(con)
  elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
  
  return(list(elapsed = elapsed, n_values = length(arr)))
}

main <- function() {
  cat(strrep("=", 70), "\n")
  cat("R - I/O Operations Benchmark\n")
  cat(strrep("=", 70), "\n")
  
  # Configuration
  n_csv_rows <- 1000000
  n_binary_values <- 1000000
  n_runs <- 10
  
  # Create data directory
  dir.create("data", showWarnings = FALSE, recursive = TRUE)
  
  results <- list()
  
  # Task 1: CSV Write
  cat(sprintf("\n[1/4] CSV Write (%s rows)...\n", format(n_csv_rows, big.mark = ",")))
  times <- numeric(n_runs)
  file_size <- 0
  for (i in 1:n_runs) {
    result <- benchmark_csv_write(n_csv_rows)
    times[i] <- result$elapsed
    file_size <- result$file_size
  }
  results$csv_write <- list(
    mean = mean(times),
    std = sd(times),
    min = min(times),
    max = max(times),
    file_size_mb = file_size / (1024^2)
  )
  cat(sprintf("  ✓ Min: %.4fs (primary)\n", results$csv_write$min))
  cat(sprintf("  ✓ Mean: %.4fs ± %.4fs\n", results$csv_write$mean, results$csv_write$std))
  cat(sprintf("  ✓ File size: %.2f MB\n", results$csv_write$file_size_mb))
  
  # Task 2: CSV Read
  cat(sprintf("\n[2/4] CSV Read (%s rows)...\n", format(n_csv_rows, big.mark = ",")))
  times <- numeric(n_runs)
  n_rows <- 0
  for (i in 1:n_runs) {
    result <- benchmark_csv_read()
    times[i] <- result$elapsed
    n_rows <- result$n_rows
  }
  results$csv_read <- list(
    mean = mean(times),
    std = sd(times),
    min = min(times),
    max = max(times),
    rows_read = n_rows
  )
  cat(sprintf("  ✓ Min: %.4fs (primary)\n", results$csv_read$min))
  cat(sprintf("  ✓ Mean: %.4fs ± %.4fs\n", results$csv_read$mean, results$csv_read$std))
  
  # Task 3: Binary Write
  cat(sprintf("\n[3/4] Binary Write (%s float64 values)...\n", format(n_binary_values, big.mark = ",")))
  times <- numeric(n_runs)
  file_size <- 0
  for (i in 1:n_runs) {
    result <- benchmark_binary_write(n_binary_values)
    times[i] <- result$elapsed
    file_size <- result$file_size
  }
  results$binary_write <- list(
    mean = mean(times),
    std = sd(times),
    min = min(times),
    max = max(times),
    file_size_mb = file_size / (1024^2)
  )
  cat(sprintf("  ✓ Min: %.4fs (primary)\n", results$binary_write$min))
  cat(sprintf("  ✓ Mean: %.4fs ± %.4fs\n", results$binary_write$mean, results$binary_write$std))
  cat(sprintf("  ✓ File size: %.2f MB\n", results$binary_write$file_size_mb))
  
  # Task 4: Binary Read
  cat(sprintf("\n[4/4] Binary Read (%s float64 values)...\n", format(n_binary_values, big.mark = ",")))
  times <- numeric(n_runs)
  n_values <- 0
  for (i in 1:n_runs) {
    result <- benchmark_binary_read()
    times[i] <- result$elapsed
    n_values <- result$n_values
  }
  results$binary_read <- list(
    mean = mean(times),
    std = sd(times),
    min = min(times),
    max = max(times),
    values_read = n_values
  )
  cat(sprintf("  ✓ Min: %.4fs (primary)\n", results$binary_read$min))
  cat(sprintf("  ✓ Mean: %.4fs ± %.4fs\n", results$binary_read$mean, results$binary_read$std))
  
  # Save results
  cat("\n", strrep("=", 70), "\n")
  cat("SAVING RESULTS...\n")
  cat(strrep("=", 70), "\n")
  
  output <- list(
    language = "R",
    r_version = paste(R.version$major, R.version$minor, sep = "."),
    n_csv_rows = n_csv_rows,
    n_binary_values = n_binary_values,
    n_runs = n_runs,
    methodology = "Minimum time as primary estimator (Chen & Revels 2016)",
    results = results
  )
  
  dir.create("results", showWarnings = FALSE, recursive = TRUE)
  write_json(output, "results/io_ops_r.json", auto_unbox = TRUE, pretty = TRUE)
  
  cat("✓ Results saved to: results/io_ops_r.json\n")
  
  # Cleanup
  cat("\nCleaning up test files...\n")
  file.remove("data/io_test_r.csv", showWarnings = FALSE)
  file.remove("data/io_test_r.bin", showWarnings = FALSE)
  cat("✓ Cleanup complete\n")
  
  cat("\nNote: Minimum times are primary metrics (Chen & Revels 2016)\n")
  cat("      Mean/median provided for context only\n")
}

main()
