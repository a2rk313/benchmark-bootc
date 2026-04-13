#!/usr/bin/env Rscript
################################################################################
# SCENARIO A.2: Hyperspectral Spectral Angle Mapper - R Implementation
################################################################################
# Task: SAM classification on 224-band hyperspectral imagery
# Dataset: NASA AVIRIS Cuprite (224 bands, freely available)
# Metrics: terra C++ efficiency, chunked processing, memory management
################################################################################

suppressPackageStartupMessages({
  library(terra)
  library(R.matlab)
  library(jsonlite)
  library(digest)
})

#' Calculate Spectral Angle Mapper (SAM) for a matrix of pixels
#' 
#' @param pixel_matrix Matrix of shape (n_pixels, n_bands)
#' @param reference_spectrum Vector of length n_bands
#' @return SAM angles in radians (numeric vector)
spectral_angle_mapper <- function(pixel_matrix, reference_spectrum) {
  epsilon <- 1e-8
  
  # Dot product: pixel %*% reference
  dot_products <- pixel_matrix %*% reference_spectrum
  
  # Norms
  pixel_norms <- sqrt(rowSums(pixel_matrix^2))
  ref_norm <- sqrt(sum(reference_spectrum^2))
  
  # Cosine of angle
  cos_angles <- dot_products / (pixel_norms * ref_norm + epsilon)
  
  # Clip to valid range [-1, 1]
  cos_angles <- pmin(pmax(cos_angles, -1), 1)
  
  # SAM angle (radians)
  angles <- acos(cos_angles)
  
  return(as.vector(angles))
}

main <- function() {
  cat(strrep("=", 70), "\n")
  cat("R - Scenario A.2: Hyperspectral SAM\n")
  cat(strrep("=", 70), "\n")
  
  # ===========================================================================
  # 1. Initialize
  # ===========================================================================
  cat("\n[1/5] Initializing...\n")
  
  # Random but reproducible reference spectrum
  set.seed(42)
  n_bands <- 224
  reference_spectrum <- runif(n_bands)
  reference_spectrum <- reference_spectrum / sqrt(sum(reference_spectrum^2))
  
  cat(sprintf("  ✓ Reference spectrum: %d bands\n", n_bands))
  ref_hash <- substr(digest(reference_spectrum, algo = "sha256"), 1, 16)
  cat(sprintf("  ✓ Reference spectrum hash: %s\n", ref_hash))
  
  # ===========================================================================
  # 2. Open Dataset (MAT file format)
  # ===========================================================================
  cat("\n[2/5] Opening hyperspectral dataset...\n")
  
  hsi_path <- "data/Cuprite.mat"
  
  cat(sprintf("  ✓ Loading MAT file: %s\n", hsi_path))
  mat_data <- readMat(hsi_path)
  data_key <- names(mat_data)[1]
  raw_data <- mat_data[[data_key]]
  
  # Cuprite.mat has shape (512, 614, 224) but AVIRIS Cuprite has 224 bands
  # Transpose from (bands_wrong, rows, cols) to (bands_correct, rows, cols)
  if (dim(raw_data)[1] == 512 && dim(raw_data)[3] == 224) {
    data <- aperm(raw_data, c(3, 1, 2))  # (512, 614, 224) -> (224, 614, 512)
    data <- data[1:224, , ]  # Take first 224 bands
    cat("  ✓ Transposed data to (bands, rows, cols)\n")
  } else {
    data <- raw_data
  }
  
  n_bands <- dim(data)[1]
  n_rows <- dim(data)[2]
  n_cols <- dim(data)[3]
  cat(sprintf("  ✓ Dataset shape: %d bands × %d × %d pixels\n", n_bands, n_rows, n_cols))
  
  # File size
  file_size_gb <- file.info(hsi_path)$size / (1024^3)
  cat(sprintf("  ✓ File size: %.2f GB\n", file_size_gb))
  
  # Memory info
  mem_info <- as.numeric(system("awk '/MemAvailable/ {print $2}' /proc/meminfo", intern=TRUE)) / (1024^2)
  cat(sprintf("  ✓ Available RAM: %.2f GB\n", mem_info))
  
  if (file_size_gb > mem_info * 0.8) {
    cat("  ⚠ Dataset size exceeds 80% of available RAM - using chunked processing\n")
  }
  
  # ===========================================================================
  # 3. Process in Chunks
  # ===========================================================================
  cat("\n[3/5] Processing hyperspectral data (chunked I/O)...\n")
  
  chunk_size <- 256
  
  sam_results <- c()
  pixels_processed <- 0
  chunks_processed <- 0
  
  for (row_start in seq(1, n_rows, by = chunk_size)) {
    for (col_start in seq(1, n_cols, by = chunk_size)) {
      row_end <- min(row_start + chunk_size - 1, n_rows)
      col_end <- min(col_start + chunk_size - 1, n_cols)
      
      # Extract chunk: shape (n_bands, chunk_rows, chunk_cols)
      chunk <- data[, row_start:row_end, col_start:col_end, drop = FALSE]
      chunk_rows <- row_end - row_start + 1
      chunk_cols <- col_end - col_start + 1
      
      # Convert to matrix: rows = pixels, cols = bands
      # chunk is (n_bands, chunk_rows, chunk_cols) -> need (pixels, bands)
      dim(chunk) <- c(n_bands, chunk_rows * chunk_cols)
      pixel_matrix <- t(chunk)  # Transpose to (pixels, bands)
      
      # Remove NA values if any
      pixel_matrix <- pixel_matrix[complete.cases(pixel_matrix), , drop = FALSE]
      
      if (nrow(pixel_matrix) > 0) {
        # Calculate SAM
        sam_angles <- spectral_angle_mapper(pixel_matrix, reference_spectrum)
        
        # Accumulate
        sam_results <- c(sam_results, sam_angles)
        pixels_processed <- pixels_processed + length(sam_angles)
      }
      
      chunks_processed <- chunks_processed + 1
      
      # Progress
      if (chunks_processed %% 10 == 0) {
        cat(sprintf("\r    Processed %d chunks (%s pixels)...", 
                    chunks_processed, format(pixels_processed, big.mark = ",")))
      }
    }
  }
  
  cat(sprintf("\r    Processed %d chunks (%s pixels)... Done!\n", 
              chunks_processed, format(pixels_processed, big.mark = ",")))
  
  # ===========================================================================
  # 4. Compute Statistics
  # ===========================================================================
  cat("\n[4/5] Computing statistics...\n")
  
  mean_sam <- mean(sam_results)
  median_sam <- median(sam_results)
  std_sam <- sd(sam_results)
  min_sam <- min(sam_results)
  max_sam <- max(sam_results)
  
  cat(sprintf("  ✓ Mean SAM: %.6f radians (%.2f°)\n", mean_sam, mean_sam * 180 / pi))
  cat(sprintf("  ✓ Median SAM: %.6f radians\n", median_sam))
  cat(sprintf("  ✓ Std Dev: %.6f radians\n", std_sam))
  cat(sprintf("  ✓ Range: [%.6f, %.6f] radians\n", min_sam, max_sam))
  
  # ===========================================================================
  # 5. Validation & Export
  # ===========================================================================
  cat("\n[5/5] Generating validation data...\n")
  
  # Generate validation hash
  result_str <- sprintf("%.8f_%d_%.8f", mean_sam, pixels_processed, median_sam)
  result_hash <- substr(digest(result_str, algo = "sha256"), 1, 16)
  
  cat(sprintf("  ✓ Validation hash: %s\n", result_hash))
  
  # Export results
  results <- list(
    language = "r",
    scenario = "hyperspectral_sam",
    pixels_processed = pixels_processed,
    chunks_processed = chunks_processed,
    n_bands = n_bands,
    mean_sam_rad = mean_sam,
    median_sam_rad = median_sam,
    std_sam_rad = std_sam,
    min_sam_rad = min_sam,
    max_sam_rad = max_sam,
    mean_sam_deg = mean_sam * 180 / pi,
    validation_hash = result_hash,
    reference_hash = ref_hash
  )
  
  # Save results
  dir.create("validation", showWarnings = FALSE)
  write_json(
    results,
    "validation/raster_r_results.json",
    pretty = TRUE,
    auto_unbox = TRUE
  )
  
  cat("\n  ✓ Results saved to validation/raster_r_results.json\n")
  cat(strrep("=", 70), "\n")
  
  return(0)
}

# Run benchmark
quit(status = main())
