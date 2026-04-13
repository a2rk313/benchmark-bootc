#!/usr/bin/env Rscript
#===============================================================================
# Matrix Operations Benchmark - R Implementation
#===============================================================================
# Reproduces Tedesco et al. (2025) matrix operation benchmarks
# Tasks: Creation/Transpose/Reshape, Power, Sorting, Cross-product, Determinant
#===============================================================================

library(jsonlite)

benchmark_matrix_creation_transpose_reshape <- function(n = 2500) {
  # Task 1.1: Matrix Creation + Transpose + Reshape
  
  start_time <- Sys.time()
  
  # Create
  A <- matrix(rnorm(n * n), nrow = n, ncol = n)
  
  # Transpose
  A <- t(A)
  
  # Reshape
  new_rows <- as.integer(n * 2 / 5)
  new_cols <- as.integer(n * n / new_rows)
  dim(A) <- c(new_rows, new_cols)
  
  # Transpose again
  A <- t(A)
  
  elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
  return(elapsed)
}

benchmark_matrix_power <- function(n = 2500) {
  # Task 1.2: Element-wise Matrix Exponentiation
  
  # Pre-generate data (not timed)
  A <- matrix(rnorm(n * n), nrow = n, ncol = n)
  A <- abs(A) / 2.0
  
  # Timed operation
  start_time <- Sys.time()
  A_pow <- A ^ 10
  elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
  
  return(elapsed)
}

benchmark_sorting <- function(n = 1000000) {
  # Task 1.3: Sorting Random Values
  
  # Pre-generate data (not timed)
  arr <- rnorm(n)
  
  # Timed operation (quicksort)
  start_time <- Sys.time()
  arr_sorted <- sort(arr, method = "quick")
  elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
  
  return(elapsed)
}

benchmark_crossproduct <- function(n = 2500) {
  # Task 1.4: Matrix Cross-Product (A'A)
  
  # Pre-generate data (not timed)
  A <- matrix(rnorm(n * n), nrow = n, ncol = n)
  
  # Timed operation
  start_time <- Sys.time()
  B <- crossprod(A)  # Equivalent to t(A) %*% A but faster
  elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
  
  return(elapsed)
}

benchmark_determinant <- function(n = 2500) {
  # Task 1.5: Matrix Determinant
  
  # Pre-generate data (not timed)
  A <- matrix(rnorm(n * n), nrow = n, ncol = n)
  
  # Timed operation
  start_time <- Sys.time()
  det_val <- det(A)
  elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
  
  return(elapsed)
}

main <- function() {
  cat(strrep("=", 70), "\n")
  cat("R - Matrix Operations Benchmark\n")
  cat(strrep("=", 70), "\n")
  
  # Configuration
  n_matrix <- 2500  # Matrix size
  n_sort <- 1000000  # Sorting size
  n_runs <- 30  # CLT threshold for stable bootstrap CIs  # Number of runs for statistical power
  n_warmup <- 5  # Warmup runs (excluded from measurement)
  
  results <- list()
  
  # Warmup phase (Chen & Revels 2016: exclude startup overhead)
  cat(sprintf("\n  Warming up (%d runs)...\n", n_warmup))
  for (i in 1:n_warmup) {
    benchmark_matrix_creation_transpose_reshape(n_matrix)
  }
  cat("  ✓ Warmup complete\n")
  
  # Task 1: Creation/Transpose/Reshape
  cat(sprintf("\n[1/5] Matrix Creation + Transpose + Reshape (%d×%d)...\n", n_matrix, n_matrix))
  times <- replicate(n_runs, benchmark_matrix_creation_transpose_reshape(n_matrix))
  results$matrix_creation <- list(
    mean = mean(times),
    std = sd(times),
    min = min(times),
    max = max(times),
    median = median(times),
    times = as.list(times)
  )
  cat(sprintf("  ✓ Min: %.4fs (primary)\n", results$matrix_creation$min))
  cat(sprintf("  ✓ Mean: %.4fs ± %.4fs\n", results$matrix_creation$mean, results$matrix_creation$std))
  
  # Task 2: Matrix Power
  cat(sprintf("\n[2/5] Matrix Exponentiation ^10 (%d×%d)...\n", n_matrix, n_matrix))
  for (i in 1:n_warmup) benchmark_matrix_power(n_matrix)
  times <- replicate(n_runs, benchmark_matrix_power(n_matrix))
  results$matrix_power <- list(
    mean = mean(times),
    std = sd(times),
    min = min(times),
    max = max(times),
    median = median(times),
    times = as.list(times)
  )
  cat(sprintf("  ✓ Min: %.4fs (primary)\n", results$matrix_power$min))
  
  # Task 3: Sorting
  cat(sprintf("\n[3/5] Sorting %s Random Values...\n", format(n_sort, big.mark = ",")))
  for (i in 1:n_warmup) benchmark_sorting(n_sort)
  times <- replicate(n_runs, benchmark_sorting(n_sort))
  results$sorting <- list(
    mean = mean(times),
    std = sd(times),
    min = min(times),
    max = max(times),
    median = median(times),
    times = as.list(times)
  )
  
  # Task 4: Cross-product
  cat(sprintf("\n[4/5] Cross-Product A'A (%d×%d)...\n", n_matrix, n_matrix))
  for (i in 1:n_warmup) benchmark_crossproduct(n_matrix)
  times <- replicate(n_runs, benchmark_crossproduct(n_matrix))
  results$crossproduct <- list(
    mean = mean(times),
    std = sd(times),
    min = min(times),
    max = max(times),
    median = median(times),
    times = as.list(times)
  )
  
  # Task 5: Determinant
  cat(sprintf("\n[5/5] Matrix Determinant (%d×%d)...\n", n_matrix, n_matrix))
  for (i in 1:n_warmup) benchmark_determinant(n_matrix)
  times <- replicate(n_runs, benchmark_determinant(n_matrix))
  results$determinant <- list(
    mean = mean(times),
    std = sd(times),
    min = min(times),
    max = max(times),
    median = median(times),
    times = as.list(times)
  )
  cat(sprintf("  ✓ Min: %.4fs (primary)\n", results$determinant$min))
  cat(sprintf("  ✓ Mean: %.4fs ± %.4fs\n", results$determinant$mean, results$determinant$std))
  
  # Save results
  cat("\n", strrep("=", 70), "\n")
  cat("SAVING RESULTS...\n")
  cat(strrep("=", 70), "\n")
  
  # Get BLAS library info
  blas_info <- tryCatch({
    sessionInfo()$BLAS
  }, error = function(e) {
    "Unknown"
  })
  
  output <- list(
    language = "R",
    r_version = paste(R.version$major, R.version$minor, sep = "."),
    blas_library = blas_info,
    matrix_size = n_matrix,
    sorting_size = n_sort,
    n_runs = n_runs,
    n_warmup = n_warmup,
    methodology = "Minimum time as primary estimator (Chen & Revels 2016)",
    enhanced_stats = TRUE,
    results = results
  )
  
  dir.create("results", showWarnings = FALSE, recursive = TRUE)
  dir.create("validation", showWarnings = FALSE, recursive = TRUE)
  write_json(output, "results/matrix_ops_r.json", auto_unbox = TRUE, pretty = TRUE)
  
  # Save times for Python statistical analysis
  times_output <- list(
    benchmark = "matrix_ops",
    language = "r",
    r_version = paste(R.version$major, R.version$minor, sep = "."),
    runs = lapply(names(results), function(name) {
      r <- results[[name]]
      list(
        name = name,
        times = r$times,
        min_time = r$min,
        mean_time = r$mean,
        std_time = r$std,
        cv = r$std / r$mean,
        median = r$median
      )
    })
  )
  write_json(times_output, "validation/matrix_ops_r_times.json", auto_unbox = TRUE, pretty = TRUE)
  
  cat("✓ Results saved to: results/matrix_ops_r.json\n")
  cat("✓ Times saved to: validation/matrix_ops_r_times.json\n")
  cat("\nNote: Minimum times are primary metrics (Chen & Revels 2016)\n")
  cat("      Mean/median provided for context only\n")
  cat("\nBLAS Library:", blas_info, "\n")
  cat("  (Performance depends heavily on BLAS - OpenBLAS recommended)\n")
}

main()
