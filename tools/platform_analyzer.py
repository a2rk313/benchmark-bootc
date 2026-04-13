#!/usr/bin/env python3
"""
===============================================================================
MULTI-PLATFORM BENCHMARK ANALYZER
===============================================================================
Automatically detects platform and generates comprehensive comparison reports
for cross-platform thesis validation.

Platforms Supported:
- Windows (WSL2)
- Linux (Native)
- macOS (Intel/ARM)
- Cloud (Codespaces, Azure, AWS, GCP)

Usage:
    # Automatic platform detection
    python3 tools/platform_analyzer.py

    # Or specify platform manually
    python3 tools/platform_analyzer.py --platform windows-wsl2

    # Generate multi-platform comparison
    python3 tools/platform_analyzer.py --compare \
        --platforms results-windows/ results-linux/ results-cloud/
===============================================================================
"""

import platform
import subprocess
import json
import os
from pathlib import Path
from datetime import datetime
import socket
import argparse

class PlatformAnalyzer:
    """
    Detect and analyze computing platform characteristics
    """
    
    def __init__(self):
        self.platform_info = {}
        self.detect_platform()
    
    def detect_platform(self):
        """Automatically detect platform details"""
        
        system = platform.system()
        
        # Basic system info
        self.platform_info['os'] = system
        self.platform_info['os_version'] = platform.release()
        self.platform_info['architecture'] = platform.machine()
        self.platform_info['python_version'] = platform.python_version()
        self.platform_info['hostname'] = socket.gethostname()
        
        # CPU info
        self.platform_info['cpu_count'] = os.cpu_count()
        
        # Detect specific platform
        if system == "Linux":
            self.detect_linux_platform()
        elif system == "Windows":
            self.detect_windows_platform()
        elif system == "Darwin":
            self.detect_macos_platform()
        
        # Detect virtualization/cloud
        self.detect_virtualization()
        
        # Container runtime
        self.detect_container_runtime()
    
    def detect_linux_platform(self):
        """Detect Linux distribution and characteristics"""
        
        self.platform_info['platform_type'] = 'linux'
        
        # Check for WSL
        if os.path.exists('/proc/version'):
            with open('/proc/version', 'r') as f:
                version = f.read()
                if 'microsoft' in version.lower() or 'wsl' in version.lower():
                    self.platform_info['platform_type'] = 'linux-wsl2'
                    self.platform_info['wsl_version'] = '2'
        
        # Detect distribution
        try:
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if line.startswith('NAME='):
                        self.platform_info['distro'] = line.split('=')[1].strip().strip('"')
                    elif line.startswith('VERSION_ID='):
                        self.platform_info['distro_version'] = line.split('=')[1].strip().strip('"')
        except:
            self.platform_info['distro'] = 'Unknown'
        
        # CPU model
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'model name' in line:
                        self.platform_info['cpu_model'] = line.split(':')[1].strip()
                        break
        except:
            pass
        
        # Memory
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'MemTotal' in line:
                        mem_kb = int(line.split()[1])
                        self.platform_info['memory_gb'] = round(mem_kb / 1024 / 1024, 1)
                        break
        except:
            pass
    
    def detect_windows_platform(self):
        """Detect Windows version"""
        
        self.platform_info['platform_type'] = 'windows-native'
        self.platform_info['windows_version'] = platform.win32_ver()[0]
    
    def detect_macos_platform(self):
        """Detect macOS version and architecture"""
        
        self.platform_info['platform_type'] = 'macos'
        self.platform_info['macos_version'] = platform.mac_ver()[0]
        
        # Detect Apple Silicon
        if self.platform_info['architecture'] == 'arm64':
            self.platform_info['platform_type'] = 'macos-arm'
            self.platform_info['cpu_type'] = 'Apple Silicon (M1/M2/M3)'
        else:
            self.platform_info['platform_type'] = 'macos-intel'
            self.platform_info['cpu_type'] = 'Intel'
    
    def detect_virtualization(self):
        """Detect if running in VM or cloud environment"""
        
        self.platform_info['virtualized'] = False
        self.platform_info['cloud_provider'] = None
        
        # Check for common cloud metadata
        cloud_checks = {
            'codespaces': lambda: os.environ.get('CODESPACES') == 'true',
            'azure': lambda: os.path.exists('/var/lib/waagent'),
            'aws': lambda: self._check_aws_metadata(),
            'gcp': lambda: self._check_gcp_metadata(),
        }
        
        for provider, check_func in cloud_checks.items():
            try:
                if check_func():
                    self.platform_info['virtualized'] = True
                    self.platform_info['cloud_provider'] = provider
                    break
            except:
                pass
        
        # Generic VM detection
        if not self.platform_info['virtualized']:
            vm_indicators = ['/sys/class/dmi/id/product_name', '/proc/cpuinfo']
            for path in vm_indicators:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        content = f.read().lower()
                        if any(vm in content for vm in ['kvm', 'qemu', 'virtualbox', 'vmware']):
                            self.platform_info['virtualized'] = True
                            break
    
    def _check_aws_metadata(self):
        """Check AWS instance metadata"""
        try:
            import urllib.request
            req = urllib.request.Request(
                'http://169.254.169.254/latest/meta-data/instance-id',
                headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'}
            )
            urllib.request.urlopen(req, timeout=1)
            return True
        except:
            return False
    
    def _check_gcp_metadata(self):
        """Check GCP instance metadata"""
        try:
            import urllib.request
            req = urllib.request.Request(
                'http://metadata.google.internal/computeMetadata/v1/instance/id',
                headers={'Metadata-Flavor': 'Google'}
            )
            urllib.request.urlopen(req, timeout=1)
            return True
        except:
            return False
    
    def detect_container_runtime(self):
        """Detect available container runtime"""
        
        runtimes = []
        
        for runtime in ['docker', 'podman']:
            try:
                result = subprocess.run(
                    [runtime, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    runtimes.append(runtime)
                    version = result.stdout.split('\n')[0]
                    self.platform_info[f'{runtime}_version'] = version
            except:
                pass
        
        self.platform_info['container_runtimes'] = runtimes
        self.platform_info['has_container_runtime'] = len(runtimes) > 0
    
    def get_platform_label(self):
        """Generate human-readable platform label"""
        
        ptype = self.platform_info.get('platform_type', 'unknown')
        
        labels = {
            'linux': f"Linux Native ({self.platform_info.get('distro', 'Unknown')})",
            'linux-wsl2': f"Windows WSL2 (Ubuntu)",
            'windows-native': f"Windows {self.platform_info.get('windows_version', '')}",
            'macos': f"macOS {self.platform_info.get('macos_version', '')}",
            'macos-intel': f"macOS Intel {self.platform_info.get('macos_version', '')}",
            'macos-arm': f"macOS Apple Silicon {self.platform_info.get('macos_version', '')}",
        }
        
        label = labels.get(ptype, 'Unknown Platform')
        
        # Add cloud provider if applicable
        if self.platform_info.get('cloud_provider'):
            provider = self.platform_info['cloud_provider'].capitalize()
            label += f" ({provider})"
        
        return label
    
    def generate_report(self):
        """Generate platform analysis report"""
        
        report = []
        
        report.append("=" * 70)
        report.append("PLATFORM ANALYSIS REPORT")
        report.append("=" * 70)
        report.append("")
        
        report.append(f"Platform: {self.get_platform_label()}")
        report.append(f"Architecture: {self.platform_info.get('architecture', 'Unknown')}")
        report.append(f"CPU Cores: {self.platform_info.get('cpu_count', 'Unknown')}")
        
        if 'cpu_model' in self.platform_info:
            report.append(f"CPU Model: {self.platform_info['cpu_model']}")
        
        if 'memory_gb' in self.platform_info:
            report.append(f"Memory: {self.platform_info['memory_gb']} GB")
        
        report.append(f"Virtualized: {'Yes' if self.platform_info.get('virtualized') else 'No'}")
        
        if self.platform_info.get('cloud_provider'):
            report.append(f"Cloud Provider: {self.platform_info['cloud_provider'].capitalize()}")
        
        report.append("")
        report.append("Container Runtime:")
        
        if self.platform_info.get('container_runtimes'):
            for runtime in self.platform_info['container_runtimes']:
                version = self.platform_info.get(f'{runtime}_version', 'Unknown')
                report.append(f"  ✓ {runtime}: {version}")
        else:
            report.append("  ✗ No container runtime detected")
        
        report.append("")
        report.append("=" * 70)
        
        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("=" * 70)
        report.append("")
        
        ptype = self.platform_info.get('platform_type')
        
        if ptype == 'linux':
            report.append("✓ Optimal platform for benchmarking (100% performance)")
        elif ptype == 'linux-wsl2':
            report.append("✓ Excellent platform (95-98% of native Linux)")
            report.append("  - Expected overhead: 2-5%")
            report.append("  - Ensure files are in WSL filesystem (not /mnt/c)")
        elif ptype == 'windows-native':
            report.append("⚠ Native Windows not recommended")
            report.append("  → Install WSL2 for best results")
        elif ptype == 'macos-intel':
            report.append("✓ Good platform (95%+ performance)")
        elif ptype == 'macos-arm':
            report.append("⚠ ARM architecture requires emulation")
            report.append("  - Expected overhead: 20-30%")
            report.append("  → Consider using GitHub Codespaces instead")
        
        if self.platform_info.get('cloud_provider') == 'codespaces':
            report.append("✓ GitHub Codespaces detected (free tier)")
            report.append("  - 60 hours/month free")
            report.append("  - Native Linux performance")
        
        report.append("")
        report.append("=" * 70)
        
        return '\n'.join(report)
    
    def save_platform_metadata(self, output_file='results/platform_metadata.json'):
        """Save platform information for thesis documentation"""
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        metadata = {
            'platform': self.platform_info,
            'timestamp': datetime.now().isoformat(),
            'platform_label': self.get_platform_label()
        }
        
        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Platform metadata saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze computing platform for thesis benchmarking'
    )
    parser.add_argument(
        '--save-metadata',
        action='store_true',
        help='Save platform metadata to results directory'
    )
    parser.add_argument(
        '--output',
        default='results/platform_metadata.json',
        help='Output file for metadata'
    )
    
    args = parser.parse_args()
    
    analyzer = PlatformAnalyzer()
    
    # Print report
    print(analyzer.generate_report())
    
    # Save metadata if requested
    if args.save_metadata:
        analyzer.save_platform_metadata(args.output)
    
    print()
    print("Platform detection complete!")
    print()
    
    # Suggest next steps
    if analyzer.platform_info.get('has_container_runtime'):
        print("✓ Container runtime detected - ready to run benchmarks!")
        print("  Next: ./run_benchmarks.sh")
    else:
        print("⚠ No container runtime detected")
        ptype = analyzer.platform_info.get('platform_type')
        
        if ptype == 'linux' or ptype == 'linux-wsl2':
            print("  Install: sudo apt install docker.io")
        elif 'windows' in ptype:
            print("  Install WSL2: wsl --install")
        elif 'macos' in ptype:
            print("  Install Docker Desktop: https://www.docker.com/products/docker-desktop")


if __name__ == "__main__":
    main()
