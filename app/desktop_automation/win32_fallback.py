"""Minimal Win32 fallback for read-only automation of the Traders Tk client.

UI Automation is deliberately absent from this module.  PID-to-HWND discovery,
desktop/session/integrity checks, foreground activation and GDI desktop capture
remain usable when Tk exposes no useful accessibility tree.
"""

from __future__ import annotations

import ctypes
import os
import struct
import sys
import time
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable, Sequence


class BlockingReason(StrEnum):
    TRADERS_PROCESS_NOT_FOUND = "TRADERS_PROCESS_NOT_FOUND"
    NO_VALID_TOP_LEVEL_HWND = "NO_VALID_TOP_LEVEL_HWND"
    WRONG_WINDOWS_SESSION = "WRONG_WINDOWS_SESSION"
    WRONG_INPUT_DESKTOP = "WRONG_INPUT_DESKTOP"
    INTEGRITY_MISMATCH_PREVENTS_INPUT = "INTEGRITY_MISMATCH_PREVENTS_INPUT"
    WINDOW_NOT_VISIBLE_AFTER_RESTORE = "WINDOW_NOT_VISIBLE_AFTER_RESTORE"
    FULL_DESKTOP_CAPTURE_FAILED = "FULL_DESKTOP_CAPTURE_FAILED"
    FOREGROUND_ACTIVATION_FAILED = "FOREGROUND_ACTIVATION_FAILED"
    WINDOW_HUNG = "WINDOW_HUNG"


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    exe_path: str | None
    session_id: int


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    pid: int
    thread_id: int
    title: str
    rect: tuple[int, int, int, int]
    client_rect: tuple[int, int, int, int]
    visible: bool
    minimized: bool
    owner_hwnd: int
    tool_window: bool
    responsive: bool
    desktop: str
    dpi: int

    @property
    def area(self) -> int:
        left, top, right, bottom = self.client_rect
        return max(0, right - left) * max(0, bottom - top)


@dataclass(frozen=True)
class PreflightResult:
    process: ProcessInfo
    window: WindowInfo
    automation_pid: int
    automation_session_id: int
    same_session: bool
    traders_window_station: str
    automation_window_station: str
    traders_desktop: str
    automation_desktop: str
    input_desktop: str
    same_desktop: bool
    input_desktop_matches: bool
    traders_integrity: str
    automation_integrity: str
    integrity_compatible: bool
    dpi_awareness_mode: str
    desktop_scale: float
    coordinate_mapping: str
    browser_process_count: int
    blockers: tuple[BlockingReason, ...]

    @property
    def passed(self) -> bool:
        return not self.blockers

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["blockers"] = [str(item) for item in self.blockers]
        data["passed"] = self.passed
        data["uia_required"] = False
        data["uia_failure_non_blocking"] = self.passed
        return data


@dataclass(frozen=True)
class CaptureResult:
    full_desktop_path: str
    cropped_window_path: str
    desktop_bounds: tuple[int, int, int, int]
    window_rect: tuple[int, int, int, int]
    crop_rect: tuple[int, int, int, int]
    capture_mode: str = "FULL_DESKTOP_CROPPED_BY_HWND"


def choose_canonical_window(
    windows: Iterable[WindowInfo], *, title_hint: str | None = None
) -> WindowInfo | None:
    """Select the canonical visible, unowned, non-tool HWND deterministically."""

    valid = [
        item
        for item in windows
        if item.visible
        and item.owner_hwnd == 0
        and not item.tool_window
        and item.rect[2] > item.rect[0]
        and item.rect[3] > item.rect[1]
    ]
    if not valid:
        return None
    hint = (title_hint or "").casefold()
    return max(
        valid,
        key=lambda item: (
            bool(hint and item.title.casefold() == hint),
            bool(hint and hint in item.title.casefold()),
            item.area,
            -item.hwnd,
        ),
    )


def evaluate_preflight_blockers(
    *, same_session: bool, same_desktop: bool, input_desktop_matches: bool,
    integrity_compatible: bool, visible: bool, responsive: bool,
) -> tuple[BlockingReason, ...]:
    blockers: list[BlockingReason] = []
    if not same_session:
        blockers.append(BlockingReason.WRONG_WINDOWS_SESSION)
    if not same_desktop or not input_desktop_matches:
        blockers.append(BlockingReason.WRONG_INPUT_DESKTOP)
    if not integrity_compatible:
        blockers.append(BlockingReason.INTEGRITY_MISMATCH_PREVENTS_INPUT)
    if not visible:
        blockers.append(BlockingReason.WINDOW_NOT_VISIBLE_AFTER_RESTORE)
    if not responsive:
        blockers.append(BlockingReason.WINDOW_HUNG)
    return tuple(blockers)


def capture_mode_for(
    *, window_capture_succeeded: bool, full_desktop_succeeded: bool,
    hwnd_crop_succeeded: bool,
) -> str:
    if window_capture_succeeded:
        return "NATIVE_WINDOW"
    if not full_desktop_succeeded:
        raise RuntimeError(BlockingReason.FULL_DESKTOP_CAPTURE_FAILED)
    return "FULL_DESKTOP_CROPPED_BY_HWND" if hwnd_crop_succeeded else "FULL_DESKTOP_FALLBACK"


if sys.platform == "win32":
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260),
        ]

    class SID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Sid", wintypes.LPVOID), ("Attributes", wintypes.DWORD)]

    class TOKEN_MANDATORY_LABEL(ctypes.Structure):
        _fields_ = [("Label", SID_AND_ATTRIBUTES)]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

    # ctypes defaults return C int; explicit signatures are mandatory for
    # pointer-sized Win32 handles and SID pointers on 64-bit Windows.
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetWindow.restype = wintypes.HWND
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetProcessWindowStation.restype = wintypes.HANDLE
    user32.GetThreadDesktop.argtypes = [wintypes.DWORD]
    user32.GetThreadDesktop.restype = wintypes.HANDLE
    user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user32.OpenInputDesktop.restype = wintypes.HANDLE
    user32.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    user32.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.GetAwarenessFromDpiAwarenessContext.restype = ctypes.c_int
    advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi32.OpenProcessToken.restype = wintypes.BOOL
    advapi32.GetSidSubAuthorityCount.argtypes = [wintypes.LPVOID]
    advapi32.GetSidSubAuthorityCount.restype = ctypes.POINTER(ctypes.c_ubyte)
    advapi32.GetSidSubAuthority.argtypes = [wintypes.LPVOID, wintypes.DWORD]
    advapi32.GetSidSubAuthority.restype = ctypes.POINTER(wintypes.DWORD)
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.BitBlt.argtypes = [
        wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD,
    ]
    gdi32.BitBlt.restype = wintypes.BOOL
    gdi32.GetDIBits.argtypes = [
        wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
        wintypes.LPVOID, ctypes.POINTER(BITMAPINFO), wintypes.UINT,
    ]
    gdi32.GetDIBits.restype = ctypes.c_int
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteObject.restype = wintypes.BOOL
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.DeleteDC.restype = wintypes.BOOL
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.ReleaseDC.restype = ctypes.c_int


class Win32DesktopAutomation:
    """Fail-closed diagnostic and capture helper; never mutates trading state."""

    BROWSERS = frozenset({"chrome.exe", "firefox.exe", "msedge.exe", "brave.exe", "opera.exe"})
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    TOKEN_QUERY = 0x0008
    TH32CS_SNAPPROCESS = 0x00000002
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise OSError("Win32 desktop automation is available only on Windows")
        self._make_dpi_aware()

    @staticmethod
    def _make_dpi_aware() -> None:
        try:
            user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (AttributeError, OSError):
            pass

    @staticmethod
    def _name_for_user_object(handle: int) -> str:
        UOI_NAME = 2
        needed = wintypes.DWORD()
        user32.GetUserObjectInformationW(handle, UOI_NAME, None, 0, ctypes.byref(needed))
        if not needed.value:
            return "UNKNOWN"
        buffer = ctypes.create_unicode_buffer(max(1, needed.value // ctypes.sizeof(wintypes.WCHAR)))
        if not user32.GetUserObjectInformationW(handle, UOI_NAME, buffer, needed, ctypes.byref(needed)):
            return "UNKNOWN"
        return buffer.value

    def list_processes(self) -> list[ProcessInfo]:
        snapshot = kernel32.CreateToolhelp32Snapshot(self.TH32CS_SNAPPROCESS, 0)
        if snapshot == self.INVALID_HANDLE_VALUE:
            raise ctypes.WinError(ctypes.get_last_error())
        results: list[ProcessInfo] = []
        try:
            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(entry)
            ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
            while ok:
                pid = int(entry.th32ProcessID)
                session = wintypes.DWORD()
                kernel32.ProcessIdToSessionId(pid, ctypes.byref(session))
                results.append(ProcessInfo(pid, entry.szExeFile, self._exe_path(pid), int(session.value)))
                ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
        finally:
            kernel32.CloseHandle(snapshot)
        return results

    def _exe_path(self, pid: int) -> str | None:
        handle = kernel32.OpenProcess(self.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return None
        try:
            size = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return buffer.value
            return None
        finally:
            kernel32.CloseHandle(handle)

    def find_processes(self, names: Sequence[str]) -> list[ProcessInfo]:
        expected = {name.casefold() for name in names}
        return [item for item in self.list_processes() if item.name.casefold() in expected]

    @staticmethod
    def _window_text(hwnd: int) -> str:
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
        return buffer.value

    def windows_for_pid(self, pid: int) -> list[WindowInfo]:
        results: list[WindowInfo] = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        @callback_type
        def callback(hwnd: int, _lparam: int) -> bool:
            found_pid = wintypes.DWORD()
            thread_id = int(user32.GetWindowThreadProcessId(hwnd, ctypes.byref(found_pid)))
            if int(found_pid.value) != pid:
                return True
            rect = wintypes.RECT()
            client = wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return True
            user32.GetClientRect(hwnd, ctypes.byref(client))
            origin = wintypes.POINT(client.left, client.top)
            extent = wintypes.POINT(client.right, client.bottom)
            user32.ClientToScreen(hwnd, ctypes.byref(origin))
            user32.ClientToScreen(hwnd, ctypes.byref(extent))
            exstyle = int(user32.GetWindowLongW(hwnd, -20))
            owner = int(user32.GetWindow(hwnd, 4) or 0)
            desktop_handle = user32.GetThreadDesktop(thread_id)
            results.append(WindowInfo(
                hwnd=int(hwnd), pid=pid, thread_id=thread_id,
                title=self._window_text(hwnd),
                rect=(rect.left, rect.top, rect.right, rect.bottom),
                client_rect=(origin.x, origin.y, extent.x, extent.y),
                visible=bool(user32.IsWindowVisible(hwnd)),
                minimized=bool(user32.IsIconic(hwnd)), owner_hwnd=owner,
                tool_window=bool(exstyle & 0x00000080),
                responsive=self._responsive(hwnd),
                desktop=self._name_for_user_object(desktop_handle),
                dpi=int(user32.GetDpiForWindow(hwnd) or 96),
            ))
            return True

        if not user32.EnumWindows(callback, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        return results

    @staticmethod
    def _responsive(hwnd: int) -> bool:
        if user32.IsHungAppWindow(hwnd):
            return False
        result = ctypes.c_size_t()
        return bool(user32.SendMessageTimeoutW(hwnd, 0, 0, 0, 0x0002, 1000, ctypes.byref(result)))

    @staticmethod
    def _integrity(pid: int) -> tuple[str, int]:
        process = kernel32.OpenProcess(Win32DesktopAutomation.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not process:
            return "UNKNOWN", -1
        token = wintypes.HANDLE()
        try:
            if not advapi32.OpenProcessToken(process, Win32DesktopAutomation.TOKEN_QUERY, ctypes.byref(token)):
                return "UNKNOWN", -1
            needed = wintypes.DWORD()
            advapi32.GetTokenInformation(token, 25, None, 0, ctypes.byref(needed))
            buffer = ctypes.create_string_buffer(needed.value)
            if not advapi32.GetTokenInformation(token, 25, buffer, needed, ctypes.byref(needed)):
                return "UNKNOWN", -1
            label = ctypes.cast(buffer, ctypes.POINTER(TOKEN_MANDATORY_LABEL)).contents
            sid = label.Label.Sid
            count = int(advapi32.GetSidSubAuthorityCount(sid)[0])
            rid = int(advapi32.GetSidSubAuthority(sid, count - 1)[0])
            name = "LOW" if rid < 0x2000 else "MEDIUM" if rid < 0x3000 else "HIGH" if rid < 0x4000 else "SYSTEM"
            return name, rid
        finally:
            if token:
                kernel32.CloseHandle(token)
            kernel32.CloseHandle(process)

    @staticmethod
    def _current_session() -> int:
        value = wintypes.DWORD()
        if not kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(value)):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(value.value)

    @staticmethod
    def _dpi_awareness() -> str:
        try:
            context = user32.GetThreadDpiAwarenessContext()
            value = int(user32.GetAwarenessFromDpiAwarenessContext(context))
            return {0: "UNAWARE", 1: "SYSTEM_AWARE", 2: "PER_MONITOR_AWARE"}.get(value, f"UNKNOWN_{value}")
        except AttributeError:
            return "UNKNOWN"

    def preflight(self, process: ProcessInfo, window: WindowInfo) -> PreflightResult:
        automation_session = self._current_session()
        station = self._name_for_user_object(user32.GetProcessWindowStation())
        automation_desktop = self._name_for_user_object(user32.GetThreadDesktop(kernel32.GetCurrentThreadId()))
        input_handle = user32.OpenInputDesktop(0, False, 0x0100)
        try:
            input_desktop = self._name_for_user_object(input_handle) if input_handle else "UNKNOWN"
        finally:
            if input_handle:
                user32.CloseDesktop(input_handle)
        target_integrity, target_rid = self._integrity(process.pid)
        automation_integrity, automation_rid = self._integrity(os.getpid())
        compatible = target_rid >= 0 and automation_rid >= target_rid
        same_session = process.session_id == automation_session
        same_desktop = window.desktop.casefold() == automation_desktop.casefold()
        input_matches = window.desktop.casefold() == input_desktop.casefold()
        blockers = evaluate_preflight_blockers(
            same_session=same_session, same_desktop=same_desktop,
            input_desktop_matches=input_matches, integrity_compatible=compatible,
            visible=window.visible, responsive=window.responsive,
        )
        browser_count = sum(item.name.casefold() in self.BROWSERS for item in self.list_processes())
        return PreflightResult(
            process=process, window=window, automation_pid=os.getpid(),
            automation_session_id=automation_session, same_session=same_session,
            traders_window_station=station, automation_window_station=station,
            traders_desktop=window.desktop, automation_desktop=automation_desktop,
            input_desktop=input_desktop, same_desktop=same_desktop,
            input_desktop_matches=input_matches, traders_integrity=target_integrity,
            automation_integrity=automation_integrity, integrity_compatible=compatible,
            dpi_awareness_mode=self._dpi_awareness(), desktop_scale=window.dpi / 96.0,
            coordinate_mapping="PHYSICAL_SCREEN_PIXELS_WIN32_RECT_EQUALS_GDI_CAPTURE",
            browser_process_count=browser_count, blockers=blockers,
        )

    @staticmethod
    def activate(window: WindowInfo, timeout_seconds: float = 2.0) -> bool:
        hwnd = window.hwnd
        if not user32.IsWindow(hwnd):
            return False
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)
        else:
            user32.ShowWindow(hwnd, 5)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if int(user32.GetForegroundWindow() or 0) == hwnd:
                return True
            time.sleep(0.05)
        return False

    @staticmethod
    def _save_bmp(path: Path, width: int, height: int, pixels: bytes) -> None:
        row_size = ((width * 3 + 3) // 4) * 4
        image_size = row_size * height
        header = struct.pack("<2sIHHI", b"BM", 54 + image_size, 0, 0, 54)
        dib = struct.pack("<IiiHHIIiiII", 40, width, -height, 1, 24, 0, image_size, 0, 0, 0, 0)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(header + dib + pixels)

    @staticmethod
    def _crop_bgr(
        pixels: bytes, full_width: int, full_height: int,
        crop: tuple[int, int, int, int], origin: tuple[int, int],
    ) -> tuple[int, int, bytes]:
        left, top, right, bottom = crop
        x0, y0 = left - origin[0], top - origin[1]
        x1, y1 = right - origin[0], bottom - origin[1]
        if not (0 <= x0 < x1 <= full_width and 0 <= y0 < y1 <= full_height):
            raise ValueError("window rectangle is outside the captured desktop")
        source_stride = ((full_width * 3 + 3) // 4) * 4
        width, height = x1 - x0, y1 - y0
        target_stride = ((width * 3 + 3) // 4) * 4
        rows = []
        for y in range(y0, y1):
            start = y * source_stride + x0 * 3
            row = pixels[start : start + width * 3]
            rows.append(row + b"\0" * (target_stride - len(row)))
        return width, height, b"".join(rows)

    def capture_full_desktop(self, window: WindowInfo, output_dir: Path) -> CaptureResult:
        SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN = 76, 77
        SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 78, 79
        x = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
        y = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
        width = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
        height = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
        screen_dc = user32.GetDC(None)
        memory_dc = gdi32.CreateCompatibleDC(screen_dc)
        bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
        old = gdi32.SelectObject(memory_dc, bitmap)
        try:
            if not gdi32.BitBlt(memory_dc, 0, 0, width, height, screen_dc, x, y, 0x00CC0020 | 0x40000000):
                raise ctypes.WinError(ctypes.get_last_error())
            info = BITMAPINFO()
            info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            info.bmiHeader.biWidth = width
            info.bmiHeader.biHeight = -height
            info.bmiHeader.biPlanes = 1
            info.bmiHeader.biBitCount = 24
            stride = ((width * 3 + 3) // 4) * 4
            buffer = ctypes.create_string_buffer(stride * height)
            if not gdi32.GetDIBits(memory_dc, bitmap, 0, height, buffer, ctypes.byref(info), 0):
                raise ctypes.WinError(ctypes.get_last_error())
            pixels = buffer.raw
            stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            full_path = output_dir / f"traders-full-desktop-{stamp}.bmp"
            crop_path = output_dir / f"traders-hwnd-{window.hwnd:x}-{stamp}.bmp"
            self._save_bmp(full_path, width, height, pixels)
            desktop_bounds = (x, y, x + width, y + height)
            crop_rect = (
                max(window.rect[0], desktop_bounds[0]),
                max(window.rect[1], desktop_bounds[1]),
                min(window.rect[2], desktop_bounds[2]),
                min(window.rect[3], desktop_bounds[3]),
            )
            crop_width, crop_height, crop_pixels = self._crop_bgr(
                pixels, width, height, crop_rect, (x, y)
            )
            self._save_bmp(crop_path, crop_width, crop_height, crop_pixels)
            return CaptureResult(
                str(full_path), str(crop_path), desktop_bounds, window.rect, crop_rect
            )
        finally:
            gdi32.SelectObject(memory_dc, old)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(memory_dc)
            user32.ReleaseDC(None, screen_dc)
