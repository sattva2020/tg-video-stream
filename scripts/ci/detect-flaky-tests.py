#!/usr/bin/env python3
"""
Flaky Test Detection Script

Tracks test results across multiple runs and identifies unstable/flaky tests.
Maintains a history of test results to detect tests that fail inconsistently.

Usage:
    python scripts/ci/detect-flaky-tests.py --help
    python scripts/ci/detect-flaky-tests.py analyze --test-results backend/test-results.json
    python scripts/ci/detect-flaky-tests.py report --history .test-history.json
    python scripts/ci/detect-flaky-tests.py record --test-results backend/test-results.json
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class FlakyTestDetector:
    """Detects flaky tests by analyzing historical test results."""

    def __init__(self, history_file: Path):
        """
        Initialize the detector with a history file.

        Args:
            history_file: Path to JSON file storing test history
        """
        self.history_file = history_file
        self.history = self._load_history()

    def _load_history(self) -> Dict[str, Any]:
        """Load test history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load history file: {e}", file=sys.stderr)
                return {"runs": [], "tests": {}}
        return {"runs": [], "tests": {}}

    def _save_history(self) -> None:
        """Save test history to file."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error: Could not save history file: {e}", file=sys.stderr)
            sys.exit(1)

    def record_results(
        self,
        results: Dict[str, Any],
        run_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record test results from a test run.

        Args:
            results: Test results dictionary with test outcomes
            run_metadata: Optional metadata about the run (branch, commit, etc.)
        """
        timestamp = datetime.now().isoformat()
        run_id = f"run-{len(self.history['runs']) + 1}"

        run_info = {
            "id": run_id,
            "timestamp": timestamp,
            **(run_metadata or {})
        }

        # Record test results
        if "tests" in results:
            for test_name, test_result in results["tests"].items():
                outcome = test_result.get("outcome", "unknown")

                if test_name not in self.history["tests"]:
                    self.history["tests"][test_name] = {
                        "total_runs": 0,
                        "passed": 0,
                        "failed": 0,
                        "skipped": 0,
                        "error": 0,
                        "flaky_score": 0.0,
                        "history": []
                    }

                test_history = self.history["tests"][test_name]
                test_history["total_runs"] += 1
                test_history["history"].append({
                    "run_id": run_id,
                    "outcome": outcome,
                    "timestamp": timestamp
                })

                if outcome == "passed":
                    test_history["passed"] += 1
                elif outcome == "failed":
                    test_history["failed"] += 1
                elif outcome == "skipped":
                    test_history["skipped"] += 1
                else:
                    test_history["error"] += 1

                # Calculate flaky score (0 = stable, 1 = highly flaky)
                if test_history["total_runs"] > 1:
                    failure_rate = test_history["failed"] / test_history["total_runs"]
                    # Tests with intermediate failure rates are flakier
                    # (consistently passing or consistently failing is not "flaky")
                    test_history["flaky_score"] = 1.0 - abs(0.5 - failure_rate) * 2
                else:
                    test_history["flaky_score"] = 0.0

        # Record run info
        self.history["runs"].append(run_info)
        self._save_history()

        print(f"Recorded {len(results.get('tests', {}))} test results")
        print(f"Total test runs in history: {len(self.history['runs'])}")

    def analyze_flaky_tests(
        self,
        min_runs: int = 3,
        flaky_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Analyze test history to identify flaky tests.

        Args:
            min_runs: Minimum number of runs before considering a test for flakiness
            flaky_threshold: Minimum flaky score to consider a test flaky (0.0 - 1.0)

        Returns:
            List of flaky tests with details
        """
        flaky_tests = []

        for test_name, test_data in self.history["tests"].items():
            if test_data["total_runs"] < min_runs:
                continue

            if test_data["flaky_score"] >= flaky_threshold:
                flaky_tests.append({
                    "name": test_name,
                    "total_runs": test_data["total_runs"],
                    "passed": test_data["passed"],
                    "failed": test_data["failed"],
                    "skipped": test_data["skipped"],
                    "error": test_data["error"],
                    "flaky_score": test_data["flaky_score"],
                    "failure_rate": test_data["failed"] / test_data["total_runs"] if test_data["total_runs"] > 0 else 0,
                    "recent_failures": self._get_recent_failures(test_name)
                })

        # Sort by flaky score (most flaky first)
        flaky_tests.sort(key=lambda x: x["flaky_score"], reverse=True)
        return flaky_tests

    def _get_recent_failures(self, test_name: str, last_n: int = 5) -> List[str]:
        """Get recent failure outcomes for a test."""
        test_history = self.history["tests"].get(test_name, {})
        recent_runs = test_history.get("history", [])[-last_n:]
        return [
            f"{h['outcome']} ({h['timestamp']})"
            for h in recent_runs
            if h["outcome"] in ["failed", "error"]
        ]

    def generate_report(
        self,
        min_runs: int = 3,
        flaky_threshold: float = 0.3,
        output_format: str = "text"
    ) -> str:
        """
        Generate a report of flaky tests.

        Args:
            min_runs: Minimum runs before considering for flakiness
            flaky_threshold: Minimum flaky score to consider flaky
            output_format: Format for report ('text', 'json', 'markdown')

        Returns:
            Formatted report string
        """
        flaky_tests = self.analyze_flaky_tests(min_runs, flaky_threshold)

        if output_format == "json":
            return json.dumps({
                "summary": {
                    "total_tests": len(self.history["tests"]),
                    "flaky_tests": len(flaky_tests),
                    "total_runs": len(self.history["runs"])
                },
                "flaky_tests": flaky_tests
            }, indent=2)

        elif output_format == "markdown":
            report = []
            report.append("# Flaky Test Report\n")
            report.append(f"Generated: {datetime.now().isoformat()}\n")
            report.append(f"Total tests tracked: {len(self.history['tests'])}")
            report.append(f"Total test runs: {len(self.history['runs'])}")
            report.append(f"Flaky tests found: {len(flaky_tests)}\n")

            if flaky_tests:
                report.append("## Flaky Tests\n")
                for test in flaky_tests:
                    report.append(f"### {test['name']}")
                    report.append(f"- **Flaky Score**: {test['flaky_score']:.2f}")
                    report.append(f"- **Total Runs**: {test['total_runs']}")
                    report.append(f"- **Passed**: {test['passed']}")
                    report.append(f"- **Failed**: {test['failed']}")
                    report.append(f"- **Failure Rate**: {test['failure_rate']:.1%}")
                    if test['recent_failures']:
                        report.append(f"- **Recent Failures**: {', '.join(test['recent_failures'])}")
                    report.append("")
            else:
                report.append("✅ No flaky tests detected!\n")

            return "\n".join(report)

        else:  # text format
            lines = []
            lines.append("=" * 80)
            lines.append("FLAKY TEST DETECTION REPORT")
            lines.append("=" * 80)
            lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"Total tests tracked: {len(self.history['tests'])}")
            lines.append(f"Total test runs: {len(self.history['runs'])}")
            lines.append(f"Flaky tests found: {len(flaky_tests)}")
            lines.append("")

            if flaky_tests:
                lines.append("-" * 80)
                lines.append("FLAKY TESTS (sorted by flaky score)")
                lines.append("-" * 80)
                lines.append("")

                for i, test in enumerate(flaky_tests, 1):
                    lines.append(f"{i}. {test['name']}")
                    lines.append(f"   Flaky Score: {test['flaky_score']:.2f} (threshold: {flaky_threshold})")
                    lines.append(f"   Total Runs: {test['total_runs']} | "
                               f"Passed: {test['passed']} | "
                               f"Failed: {test['failed']} | "
                               f"Skipped: {test['skipped']}")
                    lines.append(f"   Failure Rate: {test['failure_rate']:.1%}")

                    if test['recent_failures']:
                        lines.append(f"   Recent Failures: {len(test['recent_failures'])}")

                    lines.append("")

                lines.append("-" * 80)
                lines.append("RECOMMENDATIONS")
                lines.append("-" * 80)
                lines.append("")
                lines.append("Tests with high flaky scores should be investigated and fixed:")
                lines.append("- Check for race conditions or timing issues")
                lines.append("- Ensure proper test isolation and cleanup")
                lines.append("- Use proper mocking/stubbing for external dependencies")
                lines.append("- Add explicit waits for async operations")
                lines.append("- Review test data setup and teardown")
                lines.append("")

            else:
                lines.append("✅ No flaky tests detected!")
                lines.append("All tracked tests show consistent results across runs.")
                lines.append("")

            return "\n".join(lines)

    def get_test_trend(self, test_name: str) -> Dict[str, Any]:
        """
        Get trend information for a specific test.

        Args:
            test_name: Name of the test to analyze

        Returns:
            Dictionary with trend information
        """
        if test_name not in self.history["tests"]:
            return {"error": f"Test {test_name} not found in history"}

        test_data = self.history["tests"][test_name]

        # Calculate recent trends (last 10 runs)
        recent_history = test_data["history"][-10:]
        recent_passed = sum(1 for h in recent_history if h["outcome"] == "passed")
        recent_failed = sum(1 for h in recent_history if h["outcome"] == "failed")

        return {
            "test_name": test_name,
            "total_runs": test_data["total_runs"],
            "flaky_score": test_data["flaky_score"],
            "recent_performance": {
                "total": len(recent_history),
                "passed": recent_passed,
                "failed": recent_failed,
                "pass_rate": recent_passed / len(recent_history) if recent_history else 0
            },
            "all_time_performance": {
                "passed": test_data["passed"],
                "failed": test_data["failed"],
                "skipped": test_data["skipped"],
                "error": test_data["error"]
            }
        }


def parse_pytest_json_report(json_file: Path) -> Dict[str, Any]:
    """
    Parse pytest JSON report file.

    Args:
        json_file: Path to pytest JSON report

    Returns:
        Parsed test results dictionary
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Convert pytest report to our format
        tests = {}
        summary = data.get("summary", {})
        test_results = data.get("tests", [])

        for test in test_results:
            test_name = test.get("nodeid", test.get("name", "unknown"))
            tests[test_name] = {
                "outcome": test.get("outcome", "unknown"),
                "duration": test.get("duration", 0),
                "keywords": test.get("keywords", [])
            }

        return {
            "tests": tests,
            "summary": {
                "total": summary.get("total", 0),
                "passed": summary.get("passed", 0),
                "failed": summary.get("failed", 0),
                "skipped": summary.get("skipped", 0),
                "duration": summary.get("duration", 0)
            }
        }
    except (json.JSONDecodeError, IOError, KeyError) as e:
        print(f"Error: Could not parse pytest JSON report: {e}", file=sys.stderr)
        sys.exit(1)


def parse_pytest_log_file(log_file: Path) -> Dict[str, Any]:
    """
    Parse pytest result log file (text format).

    Args:
        log_file: Path to pytest log file

    Returns:
        Parsed test results dictionary
    """
    tests = {}
    passed = 0
    failed = 0
    skipped = 0
    error = 0

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse test results from pytest output
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if '::' in line and ('PASSED' in line or 'FAILED' in line or 'ERROR' in line or 'SKIPPED' in line):
                parts = line.split()
                if len(parts) >= 2:
                    test_name = parts[0]
                    outcome = parts[1].lower()

                    if outcome == "passed":
                        tests[test_name] = {"outcome": "passed"}
                        passed += 1
                    elif outcome == "failed":
                        tests[test_name] = {"outcome": "failed"}
                        failed += 1
                    elif outcome == "error":
                        tests[test_name] = {"outcome": "error"}
                        error += 1
                    elif outcome == "skipped":
                        tests[test_name] = {"outcome": "skipped"}
                        skipped += 1

        return {
            "tests": tests,
            "summary": {
                "total": len(tests),
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "error": error
            }
        }
    except IOError as e:
        print(f"Error: Could not parse pytest log file: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Detect flaky tests by analyzing historical test results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Record test results from pytest JSON report
  python scripts/ci/detect-flaky-tests.py record \\
      --test-results backend/test-results.json

  # Generate flaky test report
  python scripts/ci/detect-flaky-tests.py report \\
      --history .test-history.json

  # Analyze and show flaky tests
  python scripts/ci/detect-flaky-tests.py analyze \\
      --history .test-history.json \\
      --min-runs 3 \\
      --flaky-threshold 0.3

  # Get trend for specific test
  python scripts/ci/detect-flaky-tests.py trend \\
      --history .test-history.json \\
      --test-name tests/test_auth.py::test_login
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Record command
    record_parser = subparsers.add_parser("record", help="Record test results")
    record_parser.add_argument(
        "--test-results",
        type=Path,
        required=True,
        help="Path to test results JSON file"
    )
    record_parser.add_argument(
        "--history",
        type=Path,
        default=Path(".test-history.json"),
        help="Path to history file (default: .test-history.json)"
    )
    record_parser.add_argument(
        "--branch",
        type=str,
        help="Git branch name"
    )
    record_parser.add_argument(
        "--commit",
        type=str,
        help="Git commit hash"
    )

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate flaky test report")
    report_parser.add_argument(
        "--history",
        type=Path,
        default=Path(".test-history.json"),
        help="Path to history file (default: .test-history.json)"
    )
    report_parser.add_argument(
        "--min-runs",
        type=int,
        default=3,
        help="Minimum runs before considering for flakiness (default: 3)"
    )
    report_parser.add_argument(
        "--flaky-threshold",
        type=float,
        default=0.3,
        help="Minimum flaky score to consider flaky (default: 0.3)"
    )
    report_parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json", "markdown"],
        default="text",
        help="Report format (default: text)"
    )
    report_parser.add_argument(
        "--output",
        type=Path,
        help="Output file (default: stdout)"
    )

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze flaky tests")
    analyze_parser.add_argument(
        "--test-results",
        type=Path,
        required=True,
        help="Path to test results JSON file"
    )
    analyze_parser.add_argument(
        "--history",
        type=Path,
        default=Path(".test-history.json"),
        help="Path to history file (default: .test-history.json)"
    )
    analyze_parser.add_argument(
        "--min-runs",
        type=int,
        default=3,
        help="Minimum runs before considering for flakiness (default: 3)"
    )
    analyze_parser.add_argument(
        "--flaky-threshold",
        type=float,
        default=0.3,
        help="Minimum flaky score to consider flaky (default: 0.3)"
    )

    # Trend command
    trend_parser = subparsers.add_parser("trend", help="Get trend for specific test")
    trend_parser.add_argument(
        "--history",
        type=Path,
        default=Path(".test-history.json"),
        help="Path to history file (default: .test-history.json)"
    )
    trend_parser.add_argument(
        "--test-name",
        type=str,
        required=True,
        help="Full test name to analyze"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    detector = FlakyTestDetector(args.history)

    if args.command == "record":
        # Parse and record test results
        if args.test_results.suffix == ".json":
            results = parse_pytest_json_report(args.test_results)
        else:
            results = parse_pytest_log_file(args.test_results)

        metadata = {}
        if args.branch:
            metadata["branch"] = args.branch
        if args.commit:
            metadata["commit"] = args.commit

        detector.record_results(results, metadata)

    elif args.command == "report":
        # Generate report
        report = detector.generate_report(
            min_runs=args.min_runs,
            flaky_threshold=args.flaky_threshold,
            output_format=args.format
        )

        if args.output:
            try:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"Report saved to {args.output}")
            except IOError as e:
                print(f"Error: Could not write report: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(report)

        # Exit with error if flaky tests found
        flaky_tests = detector.analyze_flaky_tests(args.min_runs, args.flaky_threshold)
        if flaky_tests:
            sys.exit(1)

    elif args.command == "analyze":
        # Record then report
        if args.test_results.suffix == ".json":
            results = parse_pytest_json_report(args.test_results)
        else:
            results = parse_pytest_log_file(args.test_results)

        detector.record_results(results)

        report = detector.generate_report(
            min_runs=args.min_runs,
            flaky_threshold=args.flaky_threshold,
            output_format="text"
        )
        print(report)

        flaky_tests = detector.analyze_flaky_tests(args.min_runs, args.flaky_threshold)
        if flaky_tests:
            sys.exit(1)

    elif args.command == "trend":
        # Get trend for specific test
        trend = detector.get_test_trend(args.test_name)
        print(json.dumps(trend, indent=2))

        if "error" in trend:
            sys.exit(1)


if __name__ == "__main__":
    main()
