"""
WinOptimize AI - Phase 1 Diagnostic Prototype CLI Runner
Runs read-only system inspection and exports structured reports.
"""

from __future__ import annotations
import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from .system_scanner import SystemScanner
from .models import DiagnosticReport


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
        datefmt="%H:%M:%S",
    )


def run_diagnostics(
    output_dir: str = "reports",
    use_powershell: bool = True,
    verbose: bool = False,
) -> DiagnosticReport:
    setup_logging(verbose)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = out_path / f"diagnostic_report_{timestamp_str}.json"
    md_path = out_path / f"diagnostic_summary_{timestamp_str}.md"

    print("=" * 64)
    print("      WinOptimize AI — Phase 1 Diagnostic Inspection        ")
    print("      Strict Read-Only Execution: Zero System Changes       ")
    print("=" * 64)

    scanner = SystemScanner()
    report = scanner.scan(output_json_path=str(json_path), use_powershell=use_powershell)

    # Save markdown summary
    md_content = report.generate_markdown_summary()
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print("\n" + "=" * 64)
    print("                   DIAGNOSTIC SUMMARY                        ")
    print("=" * 64)
    print(f"OS:                 {report.system.caption} (Build {report.system.build_number})")
    print(f"Memory:             {report.system.used_physical_memory_mb:,.1f} MB used / {report.system.total_physical_memory_mb:,.1f} MB ({report.system.memory_usage_percent:.1f}%)")
    print(f"Processes:          {report.processes_count} running")
    print(f"Startup Entries:    {report.startup_entries_count} discovered ({report.active_startup_count} active)")
    print(f"Scheduled Tasks:    {report.scheduled_tasks_count} non-core tasks")
    print(f"Services:           {report.services_count} evaluated")
    print(f"Candidates Flagged: {len(report.candidates)} potential optimization candidates")
    print(f"Scan Duration:      {report.scan_duration_sec}s")
    print("-" * 64)
    print(f"[+] Structured JSON Report: {json_path.resolve()}")
    print(f"[+] Markdown Summary:      {md_path.resolve()}")
    print("=" * 64 + "\n")

    return report


def main():
    parser = argparse.ArgumentParser(description="WinOptimize AI Read-Only Diagnostic Runner")
    parser.add_argument("--output-dir", default="reports", help="Directory to save diagnostic reports")
    parser.add_argument(
        "--engine",
        choices=["powershell", "python"],
        default="powershell",
        help="Inspection engine (default: powershell)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()
    use_ps = args.engine == "powershell"

    try:
        run_diagnostics(
            output_dir=args.output_dir,
            use_powershell=use_ps,
            verbose=args.verbose,
        )
    except Exception as exc:
        print(f"\n[ERROR] Diagnostic scan failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
