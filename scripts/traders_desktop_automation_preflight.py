"""Emit fail-closed Win32 preflight and optional screenshot evidence for Traders."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from app.desktop_automation import Win32DesktopAutomation, choose_canonical_window


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, help="Known Traders PID; preferred after launch")
    parser.add_argument("--process-name", action="append", default=["traders.exe", "pythonw.exe"])
    parser.add_argument("--title-hint", default="Traders")
    parser.add_argument("--activate", action="store_true")
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path(tempfile.gettempdir()) / "traders-desktop-acceptance")
    args = parser.parse_args()

    helper = Win32DesktopAutomation()
    processes = helper.list_processes()
    candidates = [item for item in processes if item.pid == args.pid] if args.pid else [
        item for item in processes if item.name.casefold() in {name.casefold() for name in args.process_name}
    ]
    selected: tuple[object, object] | None = None
    for process in candidates:
        window = choose_canonical_window(helper.windows_for_pid(process.pid), title_hint=args.title_hint)
        if window and (args.title_hint.casefold() in window.title.casefold() or args.pid):
            selected = (process, window)
            break
    if selected is None:
        print(json.dumps({"passed": False, "blockers": ["TRADERS_PROCESS_NOT_FOUND_OR_NO_VALID_TOP_LEVEL_HWND"]}))
        return 2
    process, window = selected
    activated = helper.activate(window) if args.activate else None
    window = choose_canonical_window(helper.windows_for_pid(process.pid), title_hint=args.title_hint)
    if window is None:
        print(json.dumps({"passed": False, "blockers": ["NO_VALID_TOP_LEVEL_HWND"]}))
        return 2
    result = helper.preflight(process, window)
    payload = result.as_dict()
    payload["foreground_activation"] = activated
    payload["hwnd_discovery"] = "PASS"
    payload["full_desktop_capture"] = "NOT_REQUESTED"
    if activated is False:
        payload["passed"] = False
        payload["blockers"].append("FOREGROUND_ACTIVATION_FAILED")
    if args.capture and payload["passed"]:
        capture = helper.capture_full_desktop(window, args.output_dir)
        payload["capture"] = asdict(capture)
        payload["capture"]["full_desktop_sha256"] = sha256(capture.full_desktop_path)
        payload["capture"]["cropped_window_sha256"] = sha256(capture.cropped_window_path)
        payload["full_desktop_capture"] = "PASS"
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
