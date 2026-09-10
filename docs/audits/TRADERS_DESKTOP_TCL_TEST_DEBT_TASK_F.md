# TRADERS_DESKTOP_TCL_TEST_DEBT_TASK_F

```text
TASK_STATUS = PASS_TEST_DEBT_ZERO_ACCEPTANCE_PARTIAL
DESKTOP_TCL_FAILURES_BEFORE = 2
DESKTOP_TCL_FAILURES_AFTER = 0
FULL_DESKTOP_SUITE = PASS_1509_PASSED_2_PREEXISTING_SKIPPED_3029_SUBTESTS
UNEXPECTED_FAILURES = 0
UNEXPECTED_ERRORS = 0
COMPILEALL = PASS
CLIENT_CHANGES_BY_THIS_TASK = 0
CLIENT_WORKTREE = PREEXISTING_DIRTY_PRESERVED
```

## Environment and former failure classification

```text
PYTHON = 3.11.9_64BIT
TK = 8.6
TCL = 8.6
WINDOWING_SYSTEM = win32
TCL_LIBRARY = UNSET_DISCOVERED_BY_SUPPORTED_PYTHON_INSTALLATION
TK_LIBRARY = UNSET_DISCOVERED_BY_SUPPORTED_PYTHON_INSTALLATION
TEMP = C:/Users/ZENOL/AppData/Local/Temp
PREFERRED_ENCODING = cp1251
CLASSIFICATION = LOCAL_MACHINE_CONFIGURATION_ONLY
```

The two previously reported Tcl initialization failures did not reproduce.
`tk.Tk()` initialized and destroyed cleanly without developer-specific paths or
environment overrides.  No failure was changed to `skip` or `xfail`, and no
client runtime workaround was added.

## Full suite

```text
python -m pytest -q
1509 passed, 2 skipped, 3029 subtests passed in 39.82s

python -m compileall -q src tests
PASS
```

The two skips predate the reported Tcl debt; the former two Tcl failures are
now zero.

## Supported launch and read-only evidence

The client was launched with the documented `python -m traders_client` entry
point.  Required PID/HWND preflight for PID `18520` passed:

```text
HWND = 591682
TITLE = Клиент Traders
SESSION = 1
WINDOW_STATION = WinSta0
DESKTOP = Default
INTEGRITY = MEDIUM_COMPATIBLE
RESPONSIVE = YES
FOREGROUND = YES
CAPTURE_MODE = FULL_DESKTOP_CROPPED_BY_HWND
CAPTURE_SHA256 = 757A8AAB5B1ACDC51DE92F997AF31778757A82E38F8E37C76BA9A394CA790402
BLOCKERS = 0
LIVE = DISABLED
MUTATION_CONTROLS_USED = 0
REAL_BINANCE_ORDER_CALLS = 0
```

The captured Overview rendered without a Tcl error and visibly showed
`Production Readonly HTTP` and `Только чтение`.  Settings, Trading Funnel and
PAPER rendering are exercised by the green full Tk suite.  Native app control
was not exposed by the available Computer Use runtime (`apps=[]` and no native
`getApp` API), so live-window navigation beyond Overview is recorded as an
acceptance limitation rather than hidden as PASS.
