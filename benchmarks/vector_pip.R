#!/usr/bin/env Rscript
################################################################################
# SCENARIO B: Complex Vector Operations – R Implementation (terra only)
################################################################################
# Task: Point-in-Polygon spatial join + Haversine distance calculation
# Uses terra for vector operations (no sf dependency)
################################################################################

suppressPackageStartupMessages({
  library(terra)
  library(jsonlite)
  library(digest)
})

#' Vectorized Haversine distance calculation
haversine_vectorized <- function(lat1, lon1, lat2, lon2) {
  R <- 6371000.0
  lat1_rad <- lat1 * pi / 180
  lat2_rad <- lat2 * pi / 180
  dlat <- (lat2 - lat1) * pi / 180
  dlon <- (lon2 - lon1) * pi / 180

  a <- sin(dlat / 2)^2 +
       cos(lat1_rad) * cos(lat2_rad) *
       sin(dlon / 2)^2

  c <- 2 * atan2(sqrt(a), sqrt(1 - a))
  R * c
}

main <- function() {
  cat(strrep("=", 70), "\n")
  cat("R (terra) - Scenario B: Vector Point-in-Polygon + Haversine\n")
  cat(strrep("=", 70), "\n")

  # ===========================================================================
  # 1. Data Loading
  # ===========================================================================
  cat("\n[1/4] Loading data...\n")

  # Load polygon dataset (Natural Earth countries) as SpatVector
  polys <- vect("data/natural_earth_countries.gpkg")
  cat(sprintf("  ✓ Loaded %d polygons\n", nrow(polys)))

  # Load point dataset
  points_df <- read.csv("data/gps_points_1m.csv")
  points <- vect(points_df, geom = c("lon", "lat"), crs = "EPSG:4326")
  cat(sprintf("  ✓ Loaded %d points\n", nrow(points)))

  # ===========================================================================
  # 2. Spatial Join (Point-in-Polygon) using terra::relate with spatial index
  # ===========================================================================
  cat("\n[2/4] Performing spatial join...\n")

  n_points <- nrow(points)
  n_polys <- nrow(polys)
  
  # Use spatial index for faster queries
  matched_points <- integer(0)
  matched_polys <- integer(0)
  
  # Process by bounding box filter first
  poly_bounds <- buffer(polys, 0)
  
  # Use smaller batch for speed
  batch_size <- 100  # Process 100 polygons at a time
  for (poly_start in seq(1, n_polys, by = batch_size)) {
    poly_end <- min(poly_start + batch_size - 1, n_polys)
    poly_batch <- polys[poly_start:poly_end]
    
    # Relate points to this batch of polygons
    rel_mat <- relate(points, poly_batch, "intersects")
    
    # Find matching points
    point_matches <- rowSums(rel_mat) > 0
    poly_indices <- max.col(rel_mat) * point_matches
    poly_indices[poly_indices == 0] <- NA
    poly_indices[!point_matches] <- NA
    
    # Add to results
    matched_points <- c(matched_points, which(point_matches))
    matched_polys <- c(matched_polys, poly_indices[point_matches] + poly_start - 1)
    
    if (poly_start %% 100 == 0) {
      cat(sprintf("    Processed %d/%d polygons (%d matches)...\n", 
                  poly_end, n_polys, length(matched_points)))
    }
  }
  
  # Remove duplicates
  unique_idx <- !duplicated(matched_points)
  matched_points <- matched_points[unique_idx]
  matched_polys <- matched_polys[unique_idx]
  
  n_matched <- length(matched_points)
  cat(sprintf("  ✓ Matched %d points to polygons\n", n_matched))
  cat(sprintf("  ✓ Match rate: %.2f%%\n", 100 * n_matched / n_points))

  # ===========================================================================
  # 3. Distance Calculation
  # ===========================================================================
  cat("\n[3/4] Calculating Haversine distances...\n")

  if (n_matched == 0) {
    cat("  ⚠ No points matched any polygons!\n")
    total_distance <- 0
    mean_distance <- 0
    max_distance <- 0
  } else {
    # Pre-extract all coordinates once to avoid repeated memory allocations
    cat("  Extracting coordinates...\n")
    all_coords <- crds(points)
    cat("  Computing centroids...\n")
    all_centroids <- crds(centroids(polys))
    
    # Process in chunks and compute running statistics
    cat("  Processing in chunks...\n")
    chunk_size <- 50000
    total_distance <- 0.0
    max_distance <- 0.0
    n_chunks <- 0
    
    for (i in seq(1, n_matched, by = chunk_size)) {
      chunk_end <- min(i + chunk_size - 1, n_matched)
      chunk_pt_idx <- matched_points[i:chunk_end]
      chunk_poly_idx <- matched_polys[i:chunk_end]
      
      # Get coordinates from pre-extracted data
      point_lats <- all_coords[chunk_pt_idx, "y"]
      point_lons <- all_coords[chunk_pt_idx, "x"]
      centroid_lats <- all_centroids[chunk_poly_idx, "y"]
      centroid_lons <- all_centroids[chunk_poly_idx, "x"]

      # Vectorized Haversine
      chunk_distances <- haversine_vectorized(
        point_lats, point_lons,
        centroid_lats, centroid_lons
      )
      
      # Update statistics
      total_distance <- total_distance + sum(chunk_distances)
      max_distance <- max(max_distance, max(chunk_distances))
      n_chunks <- n_chunks + length(chunk_distances)
      
      if (chunk_end %% 100000 == 0 || chunk_end == n_matched) {
        cat(sprintf("    Processed %d / %d points...\n", chunk_end, n_matched))
      }
    }
    
    mean_distance <- total_distance / n_matched
  }

  # ===========================================================================
  # 4. Results & Validation
  # ===========================================================================
  cat("\n[4/4] Computing metrics...\n")

  # Use statistics computed during processing
  cat(sprintf("  ✓ Total distance: %s meters\n", format(total_distance, big.mark = ",")))
  cat(sprintf("  ✓ Mean distance: %s meters\n", format(mean_distance, big.mark = ",")))
  cat(sprintf("  ✓ Max distance: %s meters\n", format(max_distance, big.mark = ",")))

  # Generate validation hash
  result_str <- sprintf("%.6f_%d_%.6f", total_distance, n_matched, mean_distance)
  result_hash <- substr(digest(result_str, algo = "sha256"), 1, 16)

  cat(sprintf("  ✓ Validation hash: %s\n", result_hash))

  # Export results
  results <- list(
    language = "r",
    scenario = "vector_pip",
    points_processed = nrow(points),
    matches_found = n_matched,
    total_distance_m = total_distance,
    mean_distance_m = mean_distance,
    max_distance_m = max_distance,
    validation_hash = result_hash
  )

  dir.create("validation", showWarnings = FALSE)
  write_json(
    results,
    "validation/vector_r_results.json",
    pretty = TRUE,
    auto_unbox = TRUE
  )

  cat("\n  ✓ Results saved to validation/vector_r_results.json\n")
  cat(strrep("=", 70), "\n")

  return(0)
}

quit(status = main())
