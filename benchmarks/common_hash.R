# =============================================================================
# Unified Hashing Utilities for R
# Uses SHA256 with consistent sampling for cross-language validation.
# =============================================================================

sample_array <- function(arr, n_samples = 100) {
  if (is.null(arr) || length(arr) == 0) {
    return(numeric(0))
  }
  flat <- as.numeric(arr)
  len <- length(flat)
  if (len <= n_samples) {
    return(flat)
  }
  indices <- floor(seq(1, len, length.out = n_samples))
  return(flat[indices])
}

round_val <- function(v, precision = 6) {
  if (is.numeric(v)) {
    return(round(v, precision))
  }
  return(v)
}

generate_hash <- function(data, n_samples = 100) {
  if (is.null(data)) {
    return(paste0(rep("0", 16), collapse = ""))
  }
  
  if (is.list(data) && !is.data.frame(data)) {
    keys <- sort(names(data))
    items <- lapply(keys, function(k) {
      v <- data[[k]]
      if (is.numeric(v) && length(v) > 1) {
        sampled <- sample_array(v, n_samples)
        list(key = k, values = sapply(sampled, round_val))
      } else {
        list(key = k, values = round_val(v))
      }
    })
    content <- jsonlite::toJSON(items, auto_unbox = FALSE, pretty = FALSE)
  } else if (is.numeric(data)) {
    if (length(data) > 1) {
      sampled <- sample_array(data, n_samples)
      content <- jsonlite::toJSON(sapply(sampled, round_val), auto_unbox = FALSE)
    } else {
      content <- jsonlite::toJSON(round_val(data), auto_unbox = TRUE)
    }
  } else {
    content <- as.character(data)
  }
  
  h <- digest::digest(content, algo = "sha256", serialize = FALSE)
  return(substr(h, 1, 16))
}
