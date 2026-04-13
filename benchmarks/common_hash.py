#!/usr/bin/env python3
"""
Unified hashing utilities for cross-language validation.
Uses SHA256 with consistent sampling for fair comparison.
"""

import hashlib
import json
from typing import Union, List, Tuple


def sample_array(arr, n_samples: int = 100) -> List[float]:
    """Sample n_samples uniformly from array."""
    flat = arr.flatten()
    if len(flat) <= n_samples:
        return flat.tolist()
    indices = [int(i * len(flat) / n_samples) for i in range(n_samples)]
    return [float(flat[i]) for i in indices]


def sample_dict(data: dict, keys: List[str] = None) -> dict:
    """Extract and sample values from dict."""
    if keys is None:
        keys = sorted(data.keys())
    result = {}
    for k in keys:
        if k in data:
            result[k] = data[k]
    return result


def compute_hash(
    data: Union[dict, list, float, int], algorithm: str = "sha256", n_samples: int = 100
) -> str:
    """
    Compute hash of data using SHA256 with consistent sampling.

    Args:
        data: Input data (dict, array, or scalar)
        algorithm: Hash algorithm (sha256 default)
        n_samples: Number of samples for arrays

    Returns:
        Hex string of hash (first 16 chars for consistency)
    """
    if algorithm == "sha256":
        hasher = hashlib.sha256
    elif algorithm == "md5":
        hasher = hashlib.md5
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    if isinstance(data, dict):
        sorted_keys = sorted(data.keys())
        items = []
        for k in sorted_keys:
            v = data[k]
            if isinstance(v, (list, tuple)):
                items.extend(
                    [k, sample_array(v, n_samples) if hasattr(v, "flatten") else v]
                )
            else:
                items.extend([k, v])
        content = json.dumps(items, sort_keys=True, default=str)
    elif isinstance(data, (list, tuple)):
        if hasattr(data[0], "flatten") if len(data) > 0 else False:
            content = json.dumps(
                [sample_array(d, n_samples) for d in data], default=str
            )
        else:
            content = json.dumps(data, default=str)
    elif hasattr(data, "flatten"):
        content = json.dumps(sample_array(data, n_samples), default=str)
    else:
        content = str(data)

    h = hasher(content.encode("utf-8")).hexdigest()
    return h[:16]


def array_hash(arr, precision: int = 6) -> str:
    """
    Compute hash of numpy array with consistent sampling and precision.
    """
    if arr is None or (isinstance(arr, (list, tuple)) and len(arr) == 0):
        return "0" * 16

    if isinstance(arr, dict):
        arr = [arr[k] for k in sorted(arr.keys()) if k in arr]

    if not isinstance(arr, list):
        arr = arr.tolist() if hasattr(arr, "tolist") else [arr]

    sampled = []
    for item in arr[:100]:
        if isinstance(item, (int, float)):
            sampled.append(round(item, precision))
        elif isinstance(item, (list, tuple)) and len(item) <= 100:
            sampled.append(
                [
                    round(x, precision) if isinstance(x, (int, float)) else x
                    for x in item
                ]
            )

    content = json.dumps(sampled, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


if __name__ == "__main__":
    import numpy as np

    test_arr = np.random.rand(1000)
    test_dict = {"a": [1, 2, 3], "b": np.random.rand(10)}

    print("Array hash:", array_hash(test_arr))
    print("Dict hash:", compute_hash(test_dict))
