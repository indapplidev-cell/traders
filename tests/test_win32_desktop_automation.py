from __future__ import annotations

import pytest

from app.desktop_automation.win32_fallback import (
    BlockingReason,
    WindowInfo,
    capture_mode_for,
    choose_canonical_window,
    evaluate_preflight_blockers,
)


def window(
    hwnd: int, *, title: str = "Traders Desktop", visible: bool = True,
    minimized: bool = False, owner: int = 0, tool: bool = False,
    rect: tuple[int, int, int, int] = (10, 20, 1010, 720),
) -> WindowInfo:
    return WindowInfo(
        hwnd=hwnd, pid=42, thread_id=7, title=title, rect=rect,
        client_rect=rect, visible=visible, minimized=minimized,
        owner_hwnd=owner, tool_window=tool, responsive=True,
        desktop="Default", dpi=120,
    )


def test_one_traders_hwnd_is_selected():
    assert choose_canonical_window([window(100)]).hwnd == 100


def test_multiple_hwnds_prefers_exact_title_then_largest_area():
    items = [
        window(100, title="Traders helper", rect=(0, 0, 1600, 900)),
        window(101, title="Traders Desktop", rect=(0, 0, 900, 700)),
    ]
    assert choose_canonical_window(items, title_hint="Traders Desktop").hwnd == 101


def test_minimized_window_remains_discoverable_for_restore():
    assert choose_canonical_window([window(100, minimized=True)]).minimized


def test_hidden_child_and_tool_windows_are_excluded():
    items = [window(1, visible=False), window(2, owner=1), window(3, tool=True), window(4)]
    assert choose_canonical_window(items).hwnd == 4


def test_stale_hwnd_is_not_reused_after_restart_inventory_refresh():
    before = choose_canonical_window([window(100)])
    after = choose_canonical_window([window(200)])
    assert before.hwnd != after.hwnd


def test_uia_unavailable_does_not_participate_in_hwnd_selection():
    # There is intentionally no UIA argument or gate in this policy surface.
    assert choose_canonical_window([window(100)]).hwnd == 100


def test_window_capture_unavailable_keeps_full_desktop_policy_available():
    assert capture_mode_for(
        window_capture_succeeded=False,
        full_desktop_succeeded=True,
        hwnd_crop_succeeded=True,
    ) == "FULL_DESKTOP_CROPPED_BY_HWND"


def test_failed_full_desktop_capture_is_terminal():
    with pytest.raises(RuntimeError, match="FULL_DESKTOP_CAPTURE_FAILED"):
        capture_mode_for(
            window_capture_succeeded=False,
            full_desktop_succeeded=False,
            hwnd_crop_succeeded=False,
        )


def test_wrong_desktop_and_session_are_preflight_blockers_not_click_fallbacks():
    blockers = evaluate_preflight_blockers(
        same_session=False, same_desktop=False, input_desktop_matches=False,
        integrity_compatible=True, visible=True, responsive=True,
    )
    assert blockers == (
        BlockingReason.WRONG_WINDOWS_SESSION,
        BlockingReason.WRONG_INPUT_DESKTOP,
    )


def test_healthy_win32_path_has_no_uia_gate_or_blocker():
    assert evaluate_preflight_blockers(
        same_session=True, same_desktop=True, input_desktop_matches=True,
        integrity_compatible=True, visible=True, responsive=True,
    ) == ()


def test_dpi_mapping_retains_physical_window_rectangle():
    selected = choose_canonical_window([window(100)])
    assert selected.dpi == 120
    assert selected.rect[0] <= 500 < selected.rect[2]
    assert selected.rect[1] <= 400 < selected.rect[3]
