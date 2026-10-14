#!/usr/bin/env python3
"""Start/check the correct local GeoJoy server and open its site/admin URL."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError, HTTPError
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "8052"))
VERSION = "8.9.0"
BASE = f"http://127.0.0.1:{PORT}"
HEALTH_URL = f"{BASE}/api/health"
LOG_PATH = ROOT / "geojoy_server.log"


def get_health(timeout: float = 0.7):
    try:
        with urlopen(HEALTH_URL, timeout=timeout) as response:
            if response.status != 200:
                return None
            data = json.loads(response.read().decode("utf-8"))
            return data if isinstance(data, dict) else None
    except (URLError, HTTPError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return None


def start_server() -> None:
    env = os.environ.copy()
    env["PORT"] = str(PORT)
    env.setdefault("GEOJOY_ADMIN_PASSWORD", "GeoJoy2026!")
    env.setdefault("PYTHONUNBUFFERED", "1")
    log = LOG_PATH.open("a", encoding="utf-8")
    log.write(f"\n--- GeoJoy {VERSION} launch {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    log.flush()
    kwargs = dict(cwd=str(ROOT), env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([sys.executable, str(ROOT / "server.py")], **kwargs)
    # Wait for a ready API from this exact version. Never open a stale server by mistake.
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        health = get_health(timeout=0.5)
        if health:
            if health.get("version") == VERSION:
                return
            raise RuntimeError(
                f"პორტი {PORT} დაკავებულია GeoJoy-ის სხვა ვერსიით ({health.get('version')}). "
                f"დახურე ძველი სერვერი ან გამოიყენე მხოლოდ ამ პაკეტის run_windows.bat."
            )
        time.sleep(0.25)
    try:
        tail = LOG_PATH.read_text(encoding="utf-8", errors="replace")[-3000:]
    except OSError:
        tail = ""
    raise RuntimeError(f"GeoJoy სერვერი 20 წამში არ გაეშვა. ლოგი: {LOG_PATH}\n{tail}")


def open_browser_url(url: str) -> bool:
    try:
        if webbrowser.open_new_tab(url):
            return True
    except Exception:
        pass
    # Windows fallback when the Python browser controller cannot identify the default browser.
    if os.name == "nt":
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        except Exception:
            pass
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="GeoJoy local site/admin launcher")
    parser.add_argument("--admin", action="store_true", help="open the admin login screen only")
    parser.add_argument("--site", action="store_true", help="open the public site only")
    args = parser.parse_args()
    if args.admin and args.site:
        parser.error("Use only one of --admin or --site")
    try:
        health = get_health()
        if health is None:
            start_server()
            health = get_health()
        if not health or health.get("version") != VERSION or health.get("port") != PORT:
            actual = (health or {}).get("version", "უცნობია")
            actual_port = (health or {}).get("port", "უცნობია")
            raise RuntimeError(f"არასწორი GeoJoy სერვერია ხელმისაწვდომი (ვერსია {actual}, პორტი {actual_port}). გადაამოწმე პორტი {PORT}.")
        urls = {
            "site": f"{BASE}/?build={VERSION}",
            "admin": f"{BASE}/admin/?build={VERSION}",
        }
        targets = [urls["admin"]] if args.admin else ([urls["site"]] if args.site else [urls["site"], urls["admin"]])
        failed = []
        for url in targets:
            print(f"Opening: {url}")
            if not open_browser_url(url):
                failed.append(url)
        print(f"GeoJoy {VERSION} is running on port {PORT}.")
        print(f"Admin URL: {urls['admin']}")
        print(f"Server log: {LOG_PATH}")
        if failed:
            print("ბრაუზერის ავტომატური გახსნა ვერ მოხერხდა. დააკოპირე მისამართი ზემოთ და გახსენი ხელით:")
            for url in failed:
                print(url)
            return 1
        return 0
    except Exception as exc:
        print(f"შეცდომა: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
