"""Bounded Tk client smoke. This module is only launched as a child process."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


class MemorySettingsStore:
    def __init__(self, settings):
        self.settings = settings

    def load(self):
        return self.settings

    def save(self, settings):
        self.settings = settings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-root", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    client_root = Path(args.client_root).resolve()
    sys.path.insert(0, str(client_root / "src"))

    import tkinter as tk

    from traders_client.async_loading import LoadState
    from traders_client.config import ClientSettings, ProviderMode
    from traders_client.i18n import Locale
    from traders_client.main import create_application
    from traders_client.providers import ServerProvider

    settings = ClientSettings(
        server_url=args.base_url,
        provider_mode=ProviderMode.PRODUCTION_READONLY_HTTP,
        locale=Locale.RU,
    )
    store = MemorySettingsStore(settings)
    root = tk.Tk()
    root.withdraw()
    root, window = create_application(root, store)
    if not isinstance(window.controller.provider, ServerProvider):
        raise AssertionError("silent provider fallback")

    def wait_for(page: str, timeout: float = 12.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            root.update()
            state = window.controller.state.page_loads[page].state
            if state in {LoadState.SUCCESS, LoadState.EMPTY}:
                return
            if state is LoadState.ERROR:
                raise AssertionError(f"{page} load failed")
            time.sleep(0.01)
        raise AssertionError(f"{page} load timed out")

    try:
        for page in ("Dashboard", "Market", "Analysis", "Setups", "Incidents"):
            window.show_page(page)
            window.controller.refresh_page(page)
            wait_for(page)
        window.show_page("Settings")
        window.set_locale(Locale.EN)
        if store.load().locale is not Locale.EN:
            raise AssertionError("language persistence failed")
        window.open_help()
        root.update_idletasks()
        if window.help_window is None or not window.help_window.exists():
            raise AssertionError("Help did not open")
        window.set_locale(Locale.RU)
        if store.load().locale is not Locale.RU:
            raise AssertionError("language persistence failed")
        if not isinstance(window.controller.provider, ServerProvider):
            raise AssertionError("provider changed during smoke")
    finally:
        window.close()
        deadline = time.monotonic() + 5.0
        while not window.controller.loader.is_terminated() and time.monotonic() < deadline:
            try:
                root.update()
            except tk.TclError:
                break
            time.sleep(0.01)
    if not window.controller.loader.is_terminated():
        return 3
    print(
        json.dumps(
            {
                "schema": "TRADERS_CLIENT_SMOKE/1",
                "result": "PASS",
                "pages": 7,
                "analysis_errors": 0,
                "provider": "PRODUCTION_READONLY_HTTP",
                "language_persistence": "PASS",
                "async": "PASS",
                "orphan_workers": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
