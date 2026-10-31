"""
WinOptimize AI - Packaging Build Automation
Builds standalone Windows executable via PyInstaller.
"""

import os
import subprocess
import sys
from pathlib import Path


def build():
    base_dir = Path(__file__).resolve().parent.parent
    spec_file = base_dir / "packaging" / "winop.spec"

    print("=" * 60)
    print("      WinOptimize AI — Standalone Packaging Build          ")
    print("=" * 60)
    print(f"Base Directory: {base_dir}")
    print(f"Spec File:      {spec_file}")

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_file),
    ]

    print("\nRunning PyInstaller...")
    ret = subprocess.run(cmd, cwd=str(base_dir))

    if ret.returncode == 0:
        dist_dir = base_dir / "dist" / "WinOptimizeAI"
        exe_file = dist_dir / "WinOptimizeAI.exe"
        print("\n" + "=" * 60)
        print("          PACKAGING COMPLETED SUCCESSFULLY                  ")
        print("=" * 60)
        print(f"[+] Output Directory: {dist_dir}")
        print(f"[+] Executable Path:  {exe_file}")
        print("=" * 60)
    else:
        print(f"\n[ERROR] PyInstaller failed with exit code {ret.returncode}", file=sys.stderr)
        sys.exit(ret.returncode)


if __name__ == "__main__":
    build()
