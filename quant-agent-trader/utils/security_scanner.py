"""
Dependency Vulnerability Scanner

Scans installed packages for known vulnerabilities.
"""

import subprocess
import json
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime


class VulnerabilityScanner:
    """Scanner for checking dependencies against known vulnerabilities."""

    # Minimum severity to report
    SEVERITY_LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]

    def __init__(self, min_severity: str = "MEDIUM"):
        """
        Initialize scanner.

        Args:
            min_severity: Minimum severity to report (default: MEDIUM)
        """
        self.min_severity = min_severity
        self.severity_index = self.SEVERITY_LEVELS.index(min_severity)

    def get_installed_packages(self) -> Dict[str, str]:
        """
        Get list of installed packages.

        Returns:
            Dictionary of package name to version
        """
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return {}

            packages = json.loads(result.stdout)
            return {p["name"].lower(): p["version"] for p in packages}

        except Exception as e:
            print(f"Error getting package list: {e}")
            return {}

    def check_package(self, package_name: str) -> List[Dict[str, Any]]:
        """
        Check a package for vulnerabilities using pip-audit.

        Args:
            package_name: Name of package to check

        Returns:
            List of vulnerabilities found
        """
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip_audit", "-r", "-f", "json"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=".",
            )

            # Try to parse pip-audit output
            if result.returncode in [0, 1]:  # 0 = no vulns, 1 = vulns found
                try:
                    vulns = json.loads(result.stdout)
                    return vulns.get("dependencies", []).get(package_name.lower(), [])
                except json.JSONDecodeError:
                    pass

        except FileNotFoundError:
            # pip-audit not installed
            pass
        except Exception:
            pass

        return []

    def scan_all(self) -> Dict[str, Any]:
        """
        Scan all installed packages.

        Returns:
            Scan results
        """
        packages = self.get_installed_packages()

        results = {
            "scan_date": datetime.now().isoformat(),
            "total_packages": len(packages),
            "packages_scanned": 0,
            "vulnerabilities": [],
            "recommendations": [],
        }

        # Use pip-audit for batch scan
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip_audit", "-f", "json"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=".",
            )

            if result.returncode in [0, 1]:
                try:
                    vulns_data = json.loads(result.stdout)
                    deps = vulns_data.get("dependencies", {})

                    for pkg_name, pkg_vulns in deps.items():
                        for vuln in pkg_vulns:
                            vuln_severity = vuln.get("severity", "UNKNOWN")

                            # Filter by severity
                            if vuln_severity in self.SEVERITY_LEVELS:
                                idx = self.SEVERITY_LEVELS.index(vuln_severity)
                                if idx >= self.severity_index:
                                    results["vulnerabilities"].append(
                                        {
                                            "package": pkg_name,
                                            "version": packages.get(
                                                pkg_name, "unknown"
                                            ),
                                            "vulnerability_id": vuln.get("id", "N/A"),
                                            "severity": vuln_severity,
                                            "description": vuln.get("description", ""),
                                            "fix_versions": vuln.get(
                                                "fix_versions", []
                                            ),
                                        }
                                    )

                    results["packages_scanned"] = len(deps)

                except json.JSONDecodeError:
                    results["recommendations"].append(
                        "pip-audit output not parseable. Install with: pip install pip-audit"
                    )

        except FileNotFoundError:
            results["recommendations"].append(
                "pip-audit not installed. Install with: pip install pip-audit"
            )
        except subprocess.TimeoutExpired:
            results["recommendations"].append(
                "pip-audit scan timed out. Try running manually."
            )
        except Exception as e:
            results["recommendations"].append(f"Error running pip-audit: {e}")

        return results

    def print_report(self, results: Dict[str, Any]) -> None:
        """
        Print vulnerability report.

        Args:
            results: Scan results from scan_all()
        """
        print("\n" + "=" * 60)
        print("DEPENDENCY VULNERABILITY SCAN REPORT")
        print("=" * 60)

        print(f"\nScan Date: {results['scan_date']}")
        print(f"Total Packages: {results['total_packages']}")
        print(f"Packages Scanned: {results['packages_scanned']}")

        vulns = results["vulnerabilities"]

        if not vulns:
            print("\n✓ No vulnerabilities found!")
        else:
            print(f"\n✗ Found {len(vulns)} vulnerabilities:")

            # Group by severity
            by_severity = {}
            for v in vulns:
                sev = v["severity"]
                if sev not in by_severity:
                    by_severity[sev] = []
                by_severity[sev].append(v)

            for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                if sev in by_severity:
                    print(f"\n{sev} ({len(by_severity[sev])}):")
                    for v in by_severity[sev][:5]:  # Show top 5
                        print(f"  - {v['package']}: {v['vulnerability_id']}")

                    if len(by_severity[sev]) > 5:
                        print(f"  ... and {len(by_severity[sev]) - 5} more")

        if results["recommendations"]:
            print("\nRecommendations:")
            for rec in results["recommendations"]:
                print(f"  • {rec}")

        print("=" * 60)


def run_scan(min_severity: str = "MEDIUM") -> int:
    """
    Run vulnerability scan.

    Args:
        min_severity: Minimum severity to report

    Returns:
        Exit code (0 = no critical vulns, 1 = vulns found)
    """
    scanner = VulnerabilityScanner(min_severity)
    results = scanner.scan_all()
    scanner.print_report(results)

    # Return exit code based on vulnerabilities
    critical_vulns = [
        v for v in results["vulnerabilities"] if v["severity"] in ["CRITICAL", "HIGH"]
    ]

    return 1 if critical_vulns else 0


if __name__ == "__main__":
    severity = sys.argv[1] if len(sys.argv) > 1 else "MEDIUM"
    sys.exit(run_scan(severity))
