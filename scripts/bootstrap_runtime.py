#!/usr/bin/env python3
"""Create an isolated runtime and download the official MediaPipe pose model."""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
MODEL_DIR = ROOT / "models"
MODEL = MODEL_DIR / "pose_landmarker_full.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
)


def python_in_venv() -> pathlib.Path:
    return VENV / "bin" / "python"


def readiness() -> tuple[bool, list[str]]:
    notes: list[str] = []
    py = python_in_venv()
    if not py.exists():
        notes.append(f"missing runtime: {VENV}")
        return False, notes
    check = subprocess.run(
        [str(py), "-c", "import cv2, mediapipe, numpy; print('imports ok')"],
        text=True,
        capture_output=True,
    )
    if check.returncode:
        notes.append("runtime imports failed: " + (check.stderr.strip() or "unknown error"))
    if not MODEL.exists() or MODEL.stat().st_size < 1_000_000:
        notes.append(f"missing pose model: {MODEL}")
    return not notes, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check readiness without installing")
    args = parser.parse_args()
    ok, notes = readiness()
    if args.check:
        print("READY" if ok else "NOT READY")
        for note in notes:
            print(f"- {note}")
        return 0 if ok else 1
    if not VENV.exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    py = python_in_venv()
    subprocess.run([str(py), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run(
        [str(py), "-m", "pip", "install", "mediapipe>=0.10", "opencv-python>=4.8", "numpy>=1.24,<3"],
        check=True,
    )
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if not MODEL.exists() or MODEL.stat().st_size < 1_000_000:
        print(f"Downloading pose model to {MODEL}")
        urllib.request.urlretrieve(MODEL_URL, MODEL)
    ok, notes = readiness()
    print("READY" if ok else "NOT READY")
    for note in notes:
        print(f"- {note}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

