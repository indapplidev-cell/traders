# Traders Tk Desktop automation policy

```text
AUTOMATION_POLICY_VERSION = TRADERS_TK_WIN32_FALLBACK_V1
UIA_REQUIRED = NO
PID_HWND_DISCOVERY = AUTHORITATIVE
FULL_DESKTOP_FALLBACK_SCREENSHOT = VALID_ACCEPTANCE_EVIDENCE
BROWSER_URL_REQUIRED = NO
PAINT_REQUIRED = NO
```

This policy applies to read-only Desktop acceptance of the Traders Tk/Tkinter
client. It does not authorize a trading mutation, LIVE enablement, an Emergency
Stop, configuration changes, service control, or secret access.

## Required preflight

1. Find the intended Traders process. Prefer the PID obtained when the client
   was launched; otherwise enumerate expected process names and use title only
   as a secondary discriminator.
2. Enumerate top-level HWNDs and bind them to PID with
   `GetWindowThreadProcessId`. Select a visible, unowned, non-tool window with a
   valid rectangle; prefer the stable title and largest valid client area when
   the PID owns several windows.
3. Verify `IsWindow`, visibility, non-zero `GetWindowRect`, responsiveness,
   same session, `WinSta0`, target/automation/input desktop `Default`, and
   compatible integrity levels. A higher-integrity target is fail-closed.
4. Record DPI awareness, `GetDpiForWindow`, desktop scale, window/client
   rectangles, and physical-pixel coordinate mapping.
5. Restore a minimized window, bring it to the top, activate it, and verify the
   foreground HWND before input. After restart, discard the old PID/HWND and
   run the complete preflight again.

The reusable helper is `python scripts/traders_desktop_automation_preflight.py
--pid <PID> --activate --capture`. It emits JSON and writes temporary BMP
evidence beneath the operating-system temporary directory by default. Evidence
images must not be committed.

## UIA and input fallback

UIA/native discovery may be attempted, but an empty, partial, or absent Tk
accessibility tree is `UIA_TREE_UNAVAILABLE_NON_BLOCKING`. When Win32 preflight
passes, continue automatically with the PID-bound HWND, fresh visual state, and
keyboard/mouse input. Coordinates are relative to the latest captured target
window or derived from its current rectangle; stale screenshot IDs, stale
coordinates, absolute hard-coded screen points, and old HWNDs are prohibited.

Use canonical virtual-key events for shortcuts so RU/EN layout does not change
their meaning. Validate input harmlessly through navigation, a neutral click,
and scroll. Never click mutation controls, Disable, or Emergency Stop.

## Capture fallback

Try native/window-only capture when available. If it is unsupported or fails,
activate the HWND and capture the full virtual desktop. Verify that the HWND
rectangle is inside the desktop bounds, preserve full-desktop evidence, and
crop by the current HWND rectangle when window-only evidence is useful.

The accepted modes are `NATIVE_WINDOW`, `FULL_DESKTOP_FALLBACK`, and
`FULL_DESKTOP_CROPPED_BY_HWND`. Window capture failure is recorded as
`WINDOW_CAPTURE_UNSUPPORTED_FALLBACK_USED`, not as a blocker.

## Canonical acceptance flow

Run preflight, activate, capture, navigate to Funnel, use a bounded render wait,
capture, navigate to PAPER, use a bounded render wait, capture, scroll the PAPER
page, and capture the lower section. Re-observe after every state-changing
action. Poll responsiveness/page indicators at a bounded cadence; do not use
busy loops, continuous screenshots, or long arbitrary sleeps.

Browsers, browser URLs, Paint, browser-mediated UI, and Chrome are irrelevant.
Count browser processes for diagnostics. Leave them alone unless a specific
browser window is proven to obstruct activation/capture; if mitigation is
necessary, close only that interfering browser safely, create a fresh Computer
Use context, and rerun preflight.

## Failure taxonomy

Non-blocking success evidence:

- `UIA_TREE_UNAVAILABLE_NON_BLOCKING`
- `WINDOW_CAPTURE_UNSUPPORTED_FALLBACK_USED`
- `FULL_DESKTOP_CAPTURE_PASS`
- `HWND_DISCOVERY_PASS`
- `FOREGROUND_ACTIVATION_PASS`
- `COORDINATE_INPUT_PASS`

Blocking reasons only:

- `TRADERS_PROCESS_NOT_FOUND`
- `NO_VALID_TOP_LEVEL_HWND`
- `WRONG_WINDOWS_SESSION`
- `WRONG_INPUT_DESKTOP`
- `INTEGRITY_MISMATCH_PREVENTS_INPUT`
- `WINDOW_NOT_VISIBLE_AFTER_RESTORE`
- `FULL_DESKTOP_CAPTURE_FAILED`
- `FOREGROUND_ACTIVATION_FAILED`
- `WINDOW_HUNG`

Invariant: if PID/HWND, session/desktop/integrity, activation, responsiveness,
and full-desktop capture pass, UIA failure alone cannot produce a terminal or
blocked result.

## Evidence fields

Every acceptance record includes UTC timestamp, process name/path/PID, HWND,
title, session IDs, window station, target/automation/input desktops, integrity,
window rectangle, minimized/visible/foreground state, DPI mapping, browser
count/action, capture mode and hash, page, input results, blockers, and safety
outcomes (`LIVE=DISABLED`, real Binance order calls `0`, secret output `0`).
