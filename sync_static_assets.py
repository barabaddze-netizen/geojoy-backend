#!/usr/bin/env python3
"""Sync the canonical root CSS/JS files into the conventional static asset directory."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / 'static'
ASSET_NAMES = ('styles.css', 'app.js', 'admin.css', 'admin.js', 'geojoy-favicon.svg')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    for name in ASSET_NAMES:
        source = ROOT / name
        target = STATIC_DIR / name
        if not source.is_file():
            raise FileNotFoundError(f'Required GeoJoy asset is missing: {source}')
        shutil.copy2(source, target)
        if digest(source) != digest(target):
            raise OSError(f'Static asset copy verification failed: {name}')
    print(f'Synchronized and verified {len(ASSET_NAMES)} CSS/JavaScript assets in {STATIC_DIR}')


if __name__ == '__main__':
    main()
