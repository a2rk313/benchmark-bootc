#!/usr/bin/env python3
"""
Hardware Detection Module
Captures system specifications for benchmark reproducibility.
"""

import platform
import json
import os
from pathlib import Path
from datetime import datetime


def get_hardware_info() -> dict:
    """
    Collect comprehensive hardware and software information.
    """
    info = {
        "timestamp": datetime.now().isoformat(),
        "platform": {},
        "cpu": {},
        "memory": {},
        "python": {},
        "packages": {},
    }

    # Platform info
    info["platform"] = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }

    # CPU info
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read()

        # Count cores
        num_cores = cpuinfo.count("processor\t:")
        model = None
        for line in cpuinfo.split("\n"):
            if "model name" in line:
                model = line.split(":")[-1].strip()
                break

        info["cpu"] = {
            "model": model or "Unknown",
            "physical_cores": os.cpu_count() or num_cores,
            "logical_cores": os.cpu_count() or num_cores,
        }
    except:
        info["cpu"] = {
            "model": platform.processor(),
            "logical_cores": os.cpu_count(),
        }

    # Memory info
    try:
        with open("/proc/meminfo", "r") as f:
            meminfo = f.read()

        mem_total = None
        mem_available = None
        for line in meminfo.split("\n"):
            if line.startswith("MemTotal:"):
                mem_total = int(line.split()[1]) // 1024  # KB to MB
            elif line.startswith("MemAvailable:"):
                mem_available = int(line.split()[1]) // 1024

        info["memory"] = {
            "total_mb": mem_total,
            "available_mb": mem_available,
        }
    except:
        info["memory"] = {"total_mb": None, "available_mb": None}

    # Python info
    info["python"] = {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "compiler": platform.python_compiler(),
    }

    return info


def get_package_versions() -> dict:
    """Get versions of key scientific packages."""
    packages = {}

    try:
        import numpy

        packages["numpy"] = numpy.__version__
    except:
        packages["numpy"] = None

    try:
        import scipy

        packages["scipy"] = scipy.__version__
    except:
        packages["scipy"] = None

    try:
        import pandas

        packages["pandas"] = pandas.__version__
    except:
        packages["pandas"] = None

    try:
        import rasterio

        packages["rasterio"] = rasterio.__version__
    except:
        packages["rasterio"] = None

    try:
        import geopandas

        packages["geopandas"] = geopandas.__version__
    except:
        packages["geopandas"] = None

    return packages


def save_hardware_info(output_path: str = "results/hardware_info.json"):
    """Save hardware info to JSON file."""
    info = get_hardware_info()
    info["packages"] = get_package_versions()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(info, f, indent=2)

    return info


def print_hardware_summary():
    """Print a summary of hardware info."""
    info = get_hardware_info()
    pkgs = get_package_versions()

    print("=" * 60)
    print("HARDWARE & ENVIRONMENT SUMMARY")
    print("=" * 60)

    print(f"\nPlatform:")
    print(f"  System: {info['platform']['system']} {info['platform']['release']}")
    print(f"  Machine: {info['platform']['machine']}")

    print(f"\nCPU:")
    print(f"  Model: {info['cpu'].get('model', 'Unknown')}")
    print(f"  Cores: {info['cpu'].get('logical_cores', 'Unknown')}")

    print(f"\nMemory:")
    total = info["memory"].get("total_mb", "Unknown")
    if isinstance(total, int):
        total = f"{total} MB"
    print(f"  Total: {total}")

    print(f"\nPython:")
    print(f"  Version: {info['python']['version']}")
    print(f"  Implementation: {info['python']['implementation']}")

    print(f"\nPackages:")
    for name, version in pkgs.items():
        if version:
            print(f"  {name}: {version}")

    print(f"\nTimestamp: {info['timestamp']}")
    print("=" * 60)

    return info


if __name__ == "__main__":
    info = print_hardware_summary()
    save_hardware_info()
    print(f"\nSaved to: results/hardware_info.json")
